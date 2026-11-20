import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join,resolve} from 'node:path';

const evidence=resolve(process.argv[2]);
const expectedRunner=process.argv[3];
const expectedManifest=process.argv[4];
const expectedProbe=process.argv[5];
const sha=value=>createHash('sha256').update(value).digest('hex');
const lines=name=>readFileSync(join(evidence,name),'utf8').trim().split(/\r?\n/).map(JSON.parse);
const summary=JSON.parse(readFileSync(join(evidence,'summary.json'),'utf8'));
const integrity=JSON.parse(readFileSync(join(evidence,'integrity.json'),'utf8'));
const trials=lines('trials.jsonl');
const commands=lines('commands.jsonl');

for(const [name,expected] of Object.entries(integrity.files))assert.equal(sha(readFileSync(join(evidence,name))),expected,`integrity:${name}`);

let previous='0'.repeat(64);
for(const trial of trials){
 const copy={...trial};delete copy.evidence_hash;
 assert.equal(copy.evidence_prev_hash,previous,`previous:${trial.trial_id}`);
 assert.equal(sha(JSON.stringify(copy)),trial.evidence_hash,`chain:${trial.trial_id}`);
 previous=trial.evidence_hash;
}
assert.equal(previous,summary.evidence_chain_head,'summary chain head');
assert.equal(previous,integrity.evidence_chain_head,'integrity chain head');

function startRegistry(){return {lineage_id:'L-vm-snapshot',status:'ACTIVE',counter:0,canonical_head:'H0',credential_id:'K1',policy_revision:3,used_challenges:new Set()};}
function decide(state,candidate){
 const snapshot=()=>({lineage_id:state.lineage_id,status:state.status,counter:state.counter,canonical_head:state.canonical_head,credential_id:state.credential_id,policy_revision:state.policy_revision});
 let reason='CONTINUITY_ACCEPTED',accepted=false;
 if(!candidate||candidate.lineage_id!==state.lineage_id)reason='LINEAGE_MISMATCH';
 else if(state.used_challenges.has(candidate.challenge))reason='CHALLENGE_REPLAY';
 else if((()=>{const copy={...candidate};delete copy.transition_digest;return sha(JSON.stringify(copy))!==candidate.transition_digest;})())reason='TRANSITION_DIGEST_MISMATCH';
 else if(candidate.policy_revision!==state.policy_revision)reason='POLICY_REVISION_MISMATCH';
 else if(candidate.predecessor!==state.canonical_head)reason='PREDECESSOR_MISMATCH';
 else if(candidate.counter!==state.counter+1)reason='COUNTER_MISMATCH';
 else if(candidate.credential_id!==state.credential_id)reason='CREDENTIAL_MISMATCH';
 else {accepted=true;state.counter=candidate.counter;state.canonical_head=candidate.successor;}
 state.used_challenges.add(candidate?.challenge);
 return {accepted,reason,state:snapshot()};
}

const expectedCounts={baseline_continue:4,rollback_after_accept:4,exact_replay:4,same_snapshot_fork:6,shared_current_credential_clone_first:4};
const seenCounts={},challenges=[],transitionDigests=[];
let decisions=0;
for(const trial of trials){
 seenCounts[trial.scenario]=(seenCounts[trial.scenario]||0)+1;
 assert.equal(trial.vm_restore_observed,true,`vm restore flag:${trial.trial_id}`);
 const registry=startRegistry();
 for(const step of trial.steps){
  const candidate=step.candidate,body={...candidate};delete body.transition_digest;
  assert.equal(sha(JSON.stringify(body)),candidate.transition_digest,`transition:${trial.trial_id}:${step.label}`);
  assert.deepEqual(decide(registry,candidate),step.decision,`decision:${trial.trial_id}:${step.label}`);
  challenges.push(candidate.challenge);transitionDigests.push(candidate.transition_digest);decisions++;
 }
 let pass=false;
 const [first,second]=trial.steps.map(x=>x.decision);
 if(trial.scenario==='baseline_continue')pass=first.accepted&&first.reason==='CONTINUITY_ACCEPTED';
 if(trial.scenario==='exact_replay')pass=first.accepted&&!second.accepted&&second.reason==='CHALLENGE_REPLAY';
 if(['rollback_after_accept','same_snapshot_fork','shared_current_credential_clone_first'].includes(trial.scenario))pass=first.accepted&&!second.accepted&&second.reason==='PREDECESSOR_MISMATCH';
 assert.equal(trial.pass,pass,`pass:${trial.trial_id}`);
 assert.equal(trial.final_registry.counter,1,`counter:${trial.trial_id}`);
 assert.equal(trial.final_registry.canonical_head,trial.steps[0].candidate.successor,`head:${trial.trial_id}`);
}
assert.deepEqual(seenCounts,expectedCounts,'scenario counts');

const challengeCounts=new Map();
for(const value of challenges)challengeCounts.set(value,(challengeCounts.get(value)||0)+1);
const duplicates=[...challengeCounts.values()].filter(x=>x>1);
assert.equal(challengeCounts.size,36,'unique challenges');
assert.deepEqual(duplicates.sort((a,b)=>a-b),[2,2,2,2],'exact replay challenge duplication');
assert.equal(new Set(transitionDigests).size,36,'unique transition digests');

const isArgs=(row,...parts)=>parts.every((value,index)=>row.args[index]===value);
const restores=commands.filter(row=>isArgs(row,'snapshot','[REDACTED]','restore'));
const starts=commands.filter(row=>isArgs(row,'startvm','[REDACTED]','--type','headless'));
const snapshotTakes=commands.filter(row=>isArgs(row,'snapshot','[REDACTED]','take'));
const readiness=commands.filter(row=>row.phase==='guest_readiness_probe');
const readinessSuccess=readiness.filter(row=>row.status===0);
const nonzero=commands.filter(row=>row.status!==0);
assert.equal(restores.length,36,'snapshot restores');
assert.equal(starts.length,37,'VM starts');
assert.equal(snapshotTakes.length,1,'versioned genesis snapshot take');
assert.equal(readinessSuccess.length,37,'readiness sessions');
assert.equal(nonzero.length,summary.execution.hypervisor.readiness.failed_probe_attempts,'failed probe count');
assert.equal(nonzero.every(row=>row.phase==='guest_readiness_probe'&&row.retry_allowed===true),true,'only readiness probes may fail');
assert.equal(commands.some(row=>row.args.includes('iepp-l2-genesis-b20dbd3ea6-v023')),true,'v0.2.3 snapshot observed');
assert.equal(commands.some(row=>JSON.stringify(row).includes('IEPP-Node1')),false,'VM name redaction');
assert.equal(commands.some(row=>JSON.stringify(row).includes('.txt')),false,'password-file path redaction');

assert.equal(summary.runner_version,'0.2.3');
assert.equal(summary.execution.actual_vm_executed,true);
assert.equal(summary.scope.observation_level,'VM_OBSERVED');
assert.equal(summary.scope.claim_level,'L1_REGISTRY_RELATIVE_CONTINUATION');
assert.equal(summary.passed_trials,22);
assert.equal(summary.total_trials,22);
assert.equal(summary.source_hashes.runner_sha256,expectedRunner,'runner source hash');
assert.equal(summary.source_hashes.manifest_sha256,expectedManifest,'manifest source hash');
assert.equal(summary.source_hashes.guest_probe_sha256,expectedProbe,'probe source hash');
assert.equal(summary.execution.hypervisor.reused_snapshot,false,'fresh v0.2.3 genesis');
assert.equal(summary.execution.hypervisor.snapshot,'iepp-l2-genesis-b20dbd3ea6-v023');
assert.equal(summary.execution.hypervisor.guest_additions_version,'7.2.16');
assert.equal(summary.execution.hypervisor.guest_node,'/snap/node/current/bin/node');
assert.equal(summary.execution.hypervisor.readiness.sessions,37);
assert.equal(summary.execution.hypervisor.readiness.successful_sessions,37);

process.stdout.write(JSON.stringify({
 ok:true,
 run_id:summary.run_id,
 trials:trials.length,
 decisions,
 transition_digests_verified:transitionDigests.length,
 unique_challenges:challengeCounts.size,
 exact_replay_duplicates:duplicates.length,
 snapshot_restores:restores.length,
 vm_starts:starts.length,
 readiness_successes:readinessSuccess.length,
 retryable_readiness_failures:nonzero.length,
 evidence_chain_head:previous,
 source_hashes:summary.source_hashes,
 environment:summary.execution.hypervisor,
},null,2)+'\n');
