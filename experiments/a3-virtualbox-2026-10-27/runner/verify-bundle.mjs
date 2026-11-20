#!/usr/bin/env node
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {join,resolve} from 'node:path';

const dir=resolve(process.argv[2]||'.');
const sha=input=>createHash('sha256').update(input).digest('hex');
const readJson=name=>JSON.parse(readFileSync(join(dir,name),'utf8'));
const readJsonl=name=>readFileSync(join(dir,name),'utf8').trim().split(/\r?\n/).filter(Boolean).map(line=>JSON.parse(line));
const integrity=readJson('integrity.json');
for(const [file,expected] of Object.entries(integrity.files)){
 const actual=sha(readFileSync(join(dir,file)));
 if(actual!==expected)throw Error(`HASH_MISMATCH:${file}`);
}

let previous='0'.repeat(64);
const trials=readJsonl('trials.jsonl');
for(const row of trials){
 const given=row.evidence_hash;
 const body={...row};
 delete body.evidence_hash;
 if(row.evidence_prev_hash!==previous||sha(JSON.stringify(body))!==given)throw Error(`CHAIN_MISMATCH:${row.trial_id}`);
 previous=given;
}
if(previous!==integrity.evidence_chain_head)throw Error('CHAIN_HEAD_MISMATCH');

const summary=readJson('summary.json');
const events=readJsonl('registry-events.jsonl');
if(events.length!==integrity.registry_event_count||events.length!==summary.registry_event_count)throw Error('REGISTRY_EVENT_COUNT_MISMATCH');
const requestIds=new Set();
const acceptedByPredecessor=new Map();
const firstUseByChallenge=new Map();
for(const event of events){
 if(!event.request_id||requestIds.has(event.request_id))throw Error(`DUPLICATE_REQUEST_ID:${event.request_id||'missing'}`);
 requestIds.add(event.request_id);
 if(sha(JSON.stringify(event.candidate||null))!==event.candidate_digest)throw Error(`CANDIDATE_DIGEST_MISMATCH:${event.request_id}`);
 const challengeKey=`${event.trial_id}|${event.candidate?.challenge||''}`;
 if(event.decision.challenge_first_use)firstUseByChallenge.set(challengeKey,(firstUseByChallenge.get(challengeKey)||0)+1);
 if(event.decision.accepted){
  const predecessorKey=`${event.trial_id}|${event.candidate?.predecessor||''}`;
  acceptedByPredecessor.set(predecessorKey,(acceptedByPredecessor.get(predecessorKey)||0)+1);
 }
}
if([...acceptedByPredecessor.values()].some(count=>count>1))throw Error('MULTIPLE_ACCEPTED_SUCCESSORS');
if([...firstUseByChallenge.values()].some(count=>count>1))throw Error('MULTIPLE_FIRST_USE_FOR_CHALLENGE');

const embeddedIds=new Set(trials.flatMap(trial=>trial.steps.map(step=>step.registry_event.request_id)));
if(embeddedIds.size!==events.length||events.some(event=>!embeddedIds.has(event.request_id)))throw Error('TRIAL_REGISTRY_EVENT_SET_MISMATCH');
const raceTrials=trials.filter(trial=>trial.race_observation);
for(const trial of raceTrials){
 if(!trial.race_observation.server_processing_interval_overlap)throw Error(`NO_SERVER_OVERLAP:${trial.trial_id}`);
 if(trial.race_observation.cas_interval_overlap)throw Error(`CAS_OVERLAP:${trial.trial_id}`);
 if(trial.race_observation.accepted_count!==1)throw Error(`RACE_ACCEPT_COUNT:${trial.trial_id}`);
 if(!trial.race_observation.barrier_released_by_participant_count)throw Error(`BARRIER_TIMEOUT:${trial.trial_id}`);
}
if(summary.total_trials!==trials.length||summary.passed_trials!==trials.filter(trial=>trial.pass).length)throw Error('SUMMARY_TRIAL_COUNT_MISMATCH');
if(summary.scope.claim_level!=='L1_REGISTRY_RELATIVE_CONTINUATION')throw Error('CLAIM_BOUNDARY_MISMATCH');
for(const key of ['runtime_originality_proved','clone_resistance_proved','hardware_root_used','cryptographic_guest_authentication','distributed_consensus_proved','independent_entropy_benefit_proved']){
 if(summary.scope.claims[key]!==false)throw Error(`OVERCLAIM:${key}`);
}

process.stdout.write(JSON.stringify({ok:true,verified_files:Object.keys(integrity.files).length,verified_trials:trials.length,verified_registry_events:events.length,verified_races:raceTrials.length,evidence_chain_head:previous,observation_level:summary.scope.observation_level},null,2)+'\n');
