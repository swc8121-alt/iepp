#!/usr/bin/env node
import {createHash,randomUUID} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {copyFileSync,existsSync,mkdirSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {basename,dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import os from 'node:os';
import {resolveGuestPlatform} from './guest-platform.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const argv=process.argv.slice(2);
const value=name=>{const i=argv.indexOf('--'+name);return i>=0?argv[i+1]:undefined;};
const flag=name=>argv.includes('--'+name);
const help=flag('help')||flag('h');
if(help){process.stdout.write(`IEPP L2 VirtualBox runner v0.2.3\n\nEasy Windows-host launch:\n  CHECK_IEPP_L2.cmd\n  START_IEPP_L2.cmd\n\nDry-run:\n  node run.mjs --dry-run --output ./evidence-run\n\nVirtualBox:\n  node run.mjs --vm "IEPP-L2" --guest-user iepp --password-file "C:\\secure\\guest-password.txt" --guest-os auto --output ./evidence-run\n\nOptions:\n  --guest-os <auto|linux|windows>  Guest OS mode (default auto)\n  --guest-node <path>             Override guest Node executable\n  --guest-workdir <path>          Override guest work directory\n  --vboxmanage <path>             VBoxManage executable (default VBoxManage)\n\nDefaults:\n  Linux:   /usr/bin/node and /home/<guest-user>/IEPP-L2\n  Windows: C:\\Program Files\\nodejs\\node.exe and C:\\IEPP-L2\n`);process.exit(0);}

const dryRun=flag('dry-run');
const vm=value('vm');
const guestUser=value('guest-user');
const passwordFile=value('password-file');
const outputDir=resolve(value('output')||join(process.cwd(),'iepp-l2-evidence-'+new Date().toISOString().replace(/[:.]/g,'-')));
const guestOsRequest=(value('guest-os')||'auto').toLowerCase();
const guestNodeOverride=value('guest-node');
const guestWorkdirOverride=value('guest-workdir');
const vbox=value('vboxmanage')||'VBoxManage';
if(!['auto','linux','windows'].includes(guestOsRequest))throw Error('--guest-os must be auto, linux, or windows.');
if(!dryRun&&(!vm||!guestUser||!passwordFile))throw Error('VirtualBox mode requires --vm, --guest-user and --password-file.');
if(!dryRun&&!existsSync(resolve(passwordFile)))throw Error('Password file not found.');

mkdirSync(outputDir,{recursive:true});
const manifest=JSON.parse(readFileSync(join(here,'manifest.json'),'utf8'));
const probePath=join(here,'guest-probe.mjs');
const sha=value=>createHash('sha256').update(value).digest('hex');
const fileSha=path=>sha(readFileSync(path));
const now=()=>new Date().toISOString();
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const runId='l2-'+new Date().toISOString().replace(/[-:.TZ]/g,'').slice(0,14)+'-'+randomUUID().slice(0,8);
const commandLog=[];
function logCommand(args,result,meta={}){commandLog.push({at:now(),program:dryRun?'local-simulator':basename(vbox),args:args.map((v,i)=>args[i-1]==='--passwordfile'||(!dryRun&&v===vm)?'[REDACTED]':v),status:result?.status??0,stderr:String(result?.stderr||'').split(vm||'__NO_VM__').join('[REDACTED]').slice(0,1000),...meta});}
function vboxRun(args,{allowFailure=false,timeout=180000,logMeta={}}={}){
 const result=spawnSync(vbox,args,{encoding:'utf8',timeout,windowsHide:true});logCommand(args,result,logMeta);
 if(result.error&&!allowFailure)throw result.error;
 if(result.status!==0&&!allowFailure)throw Error(`VBoxManage failed (${args.slice(0,3).join(' ')}): ${String(result.stderr||result.stdout).trim()}`);
 return result;
}
function parseJsonOutput(text){for(const line of String(text).trim().split(/\r?\n/).reverse()){try{const value=JSON.parse(line);if(value&&typeof value==='object')return value;}catch{}}throw Error('Guest probe did not return JSON.');}
function parseSnapshotUuid(text,name){
 const pairs=new Map();
 for(const line of String(text).split(/\r?\n/)){
  const match=/^Snapshot(Name|UUID)([^=]*)="([^"]*)"$/.exec(line.trim());
  if(match)pairs.set(`${match[1]}:${match[2]}`,match[3]);
 }
 for(const [key,value] of pairs){if(key.startsWith('Name:')&&value===name)return pairs.get(`UUID:${key.slice(5)}`)||null;}
 return null;
}
function cleanOutput(value){const text=String(value||'').trim();return text||null;}
function registryStart(){return {lineage_id:'L-vm-snapshot',status:'ACTIVE',counter:0,canonical_head:'H0',credential_id:'K1',policy_revision:3,used_challenges:new Set()};}
function apply(state,candidate){
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

class LocalAdapter{
 constructor(){this.kind='filesystem-simulation';this.actualVm=false;this.root=join(outputDir,'.sim-guest');this.state=join(this.root,'state.json');this.base=join(this.root,'snapshot-state.json');}
 async prepare(){mkdirSync(this.root,{recursive:true});this.call(['init','--state',this.state]);copyFileSync(this.state,this.base);return {product:'local-filesystem-simulator',version:process.version,snapshot:'simulated-genesis'};}
 async restore(){copyFileSync(this.base,this.state);}
 async advance({challenge,successor,branch}){return this.call(['advance','--state',this.state,'--challenge',challenge,'--successor',successor,'--branch',branch]);}
 call(args){const r=spawnSync(process.execPath,[probePath,...args],{encoding:'utf8'});logCommand(['guest-probe',...args],r);if(r.status!==0)throw Error(r.stderr||r.stdout);return parseJsonOutput(r.stdout);}
 async finish(){rmSync(this.root,{recursive:true,force:true});}
}

class VirtualBoxAdapter{
 constructor(){this.kind='virtualbox';this.actualVm=true;this.guestOs=null;this.guestOsDeclared=null;this.guestNode=null;this.guestWorkdir=null;this.guestState=null;this.guestProbe=null;this.guestNodeVersion=null;this.guestAdditionsVersion=null;this.guestRuntime=null;this.metadataCollected=false;this.readinessSamples=[];this.snapshot='iepp-l2-genesis-'+fileSha(probePath).slice(0,10)+'-v'+manifest.runner_version.replace(/\D/g,'');this.snapshotUuid=null;}
 configure(info){
  const config=resolveGuestPlatform({machineInfo:info,requested:guestOsRequest,guestUser,nodeOverride:guestNodeOverride,workdirOverride:guestWorkdirOverride});
  this.guestOs=config.guestOs;this.guestOsDeclared=config.declaredType;this.guestNode=config.guestNode;this.guestWorkdir=config.guestWorkdir;this.guestState=config.guestState;this.guestProbe=config.guestProbe;
 }
 auth(){return ['--username',guestUser,'--passwordfile',resolve(passwordFile)];}
 state(){const r=vboxRun(['showvminfo',vm,'--machinereadable']);return (/^VMState="([^"]+)"/m.exec(r.stdout)||[])[1]||'unknown';}
 async ensureOff(){if(this.state()==='poweroff'||this.state()==='saved')return;vboxRun(['controlvm',vm,'acpipowerbutton'],{allowFailure:true});for(let i=0;i<60;i++){await sleep(1000);if(this.state()==='poweroff')return;}vboxRun(['controlvm',vm,'poweroff']);}
 async start(){
  const startedAt=Date.now();let failedProbes=0;
  const nodeCandidates=this.guestOs==='linux'&&!guestNodeOverride?[...new Set([this.guestNode,'/snap/node/current/bin/node'])]:[this.guestNode];
  if(this.state()!=='running')vboxRun(['startvm',vm,'--type','headless']);
  for(let i=0;i<90;i++){
   await sleep(2000);
   let unsupportedVersion=null;
   for(const nodeCandidate of nodeCandidates){
    const r=this.guest(['run',...this.auth(),'--quiet','--exe',nodeCandidate,'--wait-stdout','--wait-stderr','--','--version'],true,{phase:'guest_readiness_probe',retry_allowed:true,probe_number:i+1,node_candidate:nodeCandidate});
    if(r.status===0){
     const version=(/v(\d+)\.[\d.]+/.exec(r.stdout)||[])[0];
     const major=Number((/v(\d+)/.exec(r.stdout)||[])[1]);
     if(major>=22){this.guestNode=nodeCandidate;this.guestNodeVersion=version;this.readinessSamples.push({ready:true,elapsed_ms:Date.now()-startedAt,failed_probes:failedProbes});await this.collectGuestMetadata();return;}
     if(major)unsupportedVersion=version;
    }else failedProbes++;
   }
   if(unsupportedVersion)throw Error(`Guest Node.js 22 or newer is required; found ${unsupportedVersion}.`);
  }
  this.readinessSamples.push({ready:false,elapsed_ms:Date.now()-startedAt,failed_probes:failedProbes});
  throw Error(`Guest Additions, credentials, or guest Node (${nodeCandidates.join(' or ')}) did not become ready within 180 seconds.`);
 }
 guest(args,allowFailure=false,logMeta={}){return vboxRun(['guestcontrol',vm,...args],{allowFailure,timeout:180000,logMeta});}
 async collectGuestMetadata(){
  if(this.metadataCollected)return;
  this.metadataCollected=true;
  const additions=vboxRun(['guestproperty','get',vm,'/VirtualBox/GuestAdd/Version'],{allowFailure:true,logMeta:{phase:'guest_metadata'}});
  const additionsValue=/^Value:\s*(.+)$/m.exec(String(additions.stdout||''));
  if(additionsValue&&additionsValue[1]!=='No value set!')this.guestAdditionsVersion=additionsValue[1].trim();
  const runtime=this.guestOs==='linux'
   ?this.guest(['run',...this.auth(),'--quiet','--exe','/usr/bin/uname','--wait-stdout','--wait-stderr','--','-srmo'],true,{phase:'guest_metadata'})
   :this.guest(['run',...this.auth(),'--quiet','--exe','C:\\Windows\\System32\\cmd.exe','--wait-stdout','--wait-stderr','--','/d','/s','/c','ver'],true,{phase:'guest_metadata'});
  if(runtime.status===0)this.guestRuntime=cleanOutput(runtime.stdout);
 }
 runtimeMetadata(){
  const durations=this.readinessSamples.filter(x=>x.ready).map(x=>x.elapsed_ms).sort((a,b)=>a-b);
  const sum=durations.reduce((a,b)=>a+b,0),middle=Math.floor(durations.length/2);
  const median=durations.length?(durations.length%2?durations[middle]:(durations[middle-1]+durations[middle])/2):null;
  return {guest_os_declared:this.guestOsDeclared,guest_node:this.guestNode,guest_node_version:this.guestNodeVersion,guest_additions_version:this.guestAdditionsVersion,guest_runtime:this.guestRuntime,snapshot_uuid:this.snapshotUuid,readiness:{timeout_seconds:180,sessions:this.readinessSamples.length,successful_sessions:durations.length,failed_probe_attempts:this.readinessSamples.reduce((n,x)=>n+x.failed_probes,0),elapsed_ms:{min:durations.length?durations[0]:null,median,max:durations.length?durations.at(-1):null,mean:durations.length?Math.round(sum/durations.length):null}}};
 }
 async prepare(){
  const vmInfo=vboxRun(['showvminfo',vm,'--machinereadable']);this.configure(vmInfo.stdout);
  const snapshots=vboxRun(['snapshot',vm,'list','--machinereadable'],{allowFailure:true}).stdout;
  this.snapshotUuid=parseSnapshotUuid(snapshots,this.snapshot);
  if(this.snapshotUuid)return {product:'Oracle VM VirtualBox',version:vboxRun(['--version']).stdout.trim(),guest_os:this.guestOs,guest_node:this.guestNode,snapshot:this.snapshot,reused_snapshot:true};
  await this.start();
  this.guest(['mkdir',...this.auth(),'--parents',this.guestWorkdir],true);
  this.guest(['copyto',...this.auth(),probePath,this.guestProbe]);
  const init=this.guest(['run',...this.auth(),'--quiet','--exe',this.guestNode,'--wait-stdout','--wait-stderr','--',this.guestProbe,'init','--state',this.guestState]);
  parseJsonOutput(init.stdout);await this.ensureOff();
  const taken=vboxRun(['snapshot',vm,'take',this.snapshot,'--description','IEPP L2 clean genesis; probe '+fileSha(probePath).slice(0,16)]);
  this.snapshotUuid=(/UUID:\s*([0-9a-f-]+)/i.exec(String(taken.stdout||''))||[])[1]||null;
  if(!this.snapshotUuid){const current=vboxRun(['snapshot',vm,'list','--machinereadable']).stdout;this.snapshotUuid=parseSnapshotUuid(current,this.snapshot);}
  return {product:'Oracle VM VirtualBox',version:vboxRun(['--version']).stdout.trim(),guest_os:this.guestOs,guest_node:this.guestNode,snapshot:this.snapshot,reused_snapshot:false};
 }
 async restore(){await this.ensureOff();vboxRun(['snapshot',vm,'restore',this.snapshot]);await this.start();}
 async advance({challenge,successor,branch}){const r=this.guest(['run',...this.auth(),'--quiet','--exe',this.guestNode,'--wait-stdout','--wait-stderr','--',this.guestProbe,'advance','--state',this.guestState,'--challenge',challenge,'--successor',successor,'--branch',branch]);return parseJsonOutput(r.stdout);}
 async finish(){await this.ensureOff();}
}

const adapter=dryRun?new LocalAdapter():new VirtualBoxAdapter();
let environment,trials=[];
function challenge(id,label){return sha(runId+'|'+id+'|'+label+'|'+randomUUID());}
async function candidate(id,label,successor){const response=await adapter.advance({challenge:challenge(id,label),successor,branch:label});if(!response.ok)throw Error(response.error||'GUEST_PROBE_FAILED');return response.candidate;}
async function executeTrial(id,scenario){
 const registry=registryStart(),steps=[];
 const submit=(label,c)=>{const d=apply(registry,c);steps.push({label,candidate:c,decision:d});return d;};
 await adapter.restore();
 const a=await candidate(id,'A',`H-${id}-A`);const first=submit('A',a);let pass=false;
 if(scenario==='baseline_continue')pass=first.accepted&&first.reason==='CONTINUITY_ACCEPTED';
 if(scenario==='exact_replay'){const replay=submit('A-replay',a);pass=first.accepted&&!replay.accepted&&replay.reason==='CHALLENGE_REPLAY';}
 if(['rollback_after_accept','same_snapshot_fork','shared_current_credential_clone_first'].includes(scenario)){
  await adapter.restore();const label=scenario==='shared_current_credential_clone_first'?'honest-after-clone':'B';const b=await candidate(id,label,`H-${id}-${label}`);const second=submit(label,b);
  pass=first.accepted&&!second.accepted&&second.reason==='PREDECESSOR_MISMATCH';
 }
 return {trial_id:id,scenario,pass,vm_restore_observed:adapter.actualVm,steps,final_registry:{lineage_id:registry.lineage_id,counter:registry.counter,canonical_head:registry.canonical_head,credential_id:registry.credential_id,policy_revision:registry.policy_revision}};
}

try{
 environment=await adapter.prepare();let n=0;
 for(const group of manifest.groups){for(let i=1;i<=group.count;i++){n++;trials.push(await executeTrial(String(n).padStart(2,'0'),group.scenario));process.stdout.write(`[${n}/${manifest.total_trials}] ${group.scenario} ${trials.at(-1).pass?'PASS':'FAIL'}\n`);}}
}finally{await adapter.finish();}

let previous='0'.repeat(64);
const chained=trials.map(row=>{const body={...row,evidence_prev_hash:previous};const evidence_hash=sha(JSON.stringify(body));previous=evidence_hash;return {...body,evidence_hash};});
const counts=Object.fromEntries(manifest.groups.map(g=>[g.scenario,{passed:chained.filter(t=>t.scenario===g.scenario&&t.pass).length,total:g.count}]));
const allPassed=chained.length===manifest.total_trials&&chained.every(t=>t.pass);
const runtimeMetadata=typeof adapter.runtimeMetadata==='function'?adapter.runtimeMetadata():{};
const summary={format:'iepp-l2-virtualbox-summary-v1',runner_version:manifest.runner_version,run_id:runId,generated_at:now(),execution:{actual_vm_executed:adapter.actualVm,adapter:adapter.kind,hypervisor:{...environment,...runtimeMetadata},host:{platform:os.platform(),release:os.release(),arch:os.arch()},vm_name_hash:vm?sha(vm):null},scope:{observation_level:adapter.actualVm?'VM_OBSERVED':'SIMULATION_ONLY',claim_level:'L1_REGISTRY_RELATIVE_CONTINUATION',claims:{orchestration_completed:allPassed,guest_state_restore_exercised:adapter.actualVm&&allPassed,stale_restored_predecessor_rejected:adapter.actualVm&&counts.rollback_after_accept.passed===counts.rollback_after_accept.total,single_canonical_successor_observed:adapter.actualVm&&counts.same_snapshot_fork.passed===counts.same_snapshot_fork.total,current_shared_credential_clone_can_win:adapter.actualVm&&counts.shared_current_credential_clone_first.passed===counts.shared_current_credential_clone_first.total,runtime_originality_proved:false,clone_resistance_proved:false,hardware_root_used:false,cryptographic_guest_authentication:false},note:adapter.actualVm?'A real VM snapshot was restored, but the security result is only an L1 single-registry, registry-relative continuation decision. It does not identify the physical or original runtime.':'Only the orchestration and evidence pipeline ran. No VM or hypervisor was exercised; the security claim remains limited to the L1 registry decision model.'},counts,total_trials:chained.length,passed_trials:chained.filter(t=>t.pass).length,evidence_chain_head:previous,source_hashes:{manifest_sha256:fileSha(join(here,'manifest.json')),guest_probe_sha256:fileSha(probePath),runner_sha256:fileSha(fileURLToPath(import.meta.url))}};
writeFileSync(join(outputDir,'trials.jsonl'),chained.map(x=>JSON.stringify(x)).join('\n')+'\n');
writeFileSync(join(outputDir,'commands.jsonl'),commandLog.map(x=>JSON.stringify(x)).join('\n')+'\n');
writeFileSync(join(outputDir,'summary.json'),JSON.stringify(summary,null,2)+'\n');
const integrity={format:'iepp-l2-integrity-v1',generated_at:now(),files:{'summary.json':fileSha(join(outputDir,'summary.json')),'trials.jsonl':fileSha(join(outputDir,'trials.jsonl')),'commands.jsonl':fileSha(join(outputDir,'commands.jsonl'))},evidence_chain_head:previous};
writeFileSync(join(outputDir,'integrity.json'),JSON.stringify(integrity,null,2)+'\n');
const report=`# IEPP L2 VM 스냅숏 시험 보고서\n\n- 실행 ID: \`${runId}\`\n- 생성 시각: ${summary.generated_at}\n- 실제 VM 실행: **${adapter.actualVm?'예':'아니오 — 드라이런'}**\n- 관측 수준: \`${summary.scope.observation_level}\`\n- 보안 주장 수준: \`${summary.scope.claim_level}\`\n- 어댑터: ${adapter.kind}\n- 통과: ${summary.passed_trials}/${summary.total_trials}\n- 증거 체인 head: \`${previous}\`\n\n## 시나리오\n\n${Object.entries(counts).map(([k,v])=>`- ${k}: ${v.passed}/${v.total}`).join('\n')}\n\n## 주장 경계\n\n${summary.scope.note}\n런타임 원본성, clone-resistance, 하드웨어 신뢰루트, 암호학적 게스트 인증은 이 시험으로 증명하지 않습니다.\n`;
writeFileSync(join(outputDir,'REPORT_KO.md'),report);
process.stdout.write(`Evidence: ${outputDir}\nActual VM executed: ${adapter.actualVm}\nPassed: ${summary.passed_trials}/${summary.total_trials}\n`);
if(!allPassed)process.exitCode=1;
