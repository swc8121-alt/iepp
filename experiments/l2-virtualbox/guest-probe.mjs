#!/usr/bin/env node
import {createHash,randomUUID} from 'node:crypto';
import {existsSync,readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {dirname,resolve} from 'node:path';

const args=Object.fromEntries(process.argv.slice(2).reduce((a,v,i,x)=>v.startsWith('--')?a.concat([[v.slice(2),x[i+1]&&!x[i+1].startsWith('--')?x[i+1]:true]]):a,[]));
const command=process.argv[2];
const statePath=resolve(String(args.state||'iepp-l2-guest-state.json'));
const hash=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const output=value=>process.stdout.write(JSON.stringify(value)+'\n');

if(command==='ping'){
 output({ok:true,probe:'iepp-l2-guest-probe',version:'0.1.0',node:process.version,platform:process.platform,arch:process.arch});
 process.exit(0);
}
if(command==='init'){
 mkdirSync(dirname(statePath),{recursive:true});
 const state={format:'iepp-l2-guest-state-v1',lineage_id:'L-vm-snapshot',counter:0,canonical_head:'H0',credential_id:'K1',policy_revision:3,probe_instance_id:randomUUID()};
 writeFileSync(statePath,JSON.stringify(state,null,2));
 output({ok:true,operation:'init',state_public:{...state},state_digest:hash(state)});
 process.exit(0);
}
if(command!=='advance'||!existsSync(statePath)){
 output({ok:false,error:command!=='advance'?'UNKNOWN_COMMAND':'STATE_NOT_INITIALIZED'});
 process.exit(2);
}
const state=JSON.parse(readFileSync(statePath,'utf8'));
const challenge=String(args.challenge||'');
const successor=String(args.successor||'');
const branchId=String(args.branch||'');
if(!challenge||!successor||!branchId){output({ok:false,error:'MISSING_ARGUMENT'});process.exit(2);}
const candidate={type:'CONTINUE',lineage_id:state.lineage_id,policy_revision:state.policy_revision,predecessor:state.canonical_head,successor,counter:state.counter+1,credential_id:state.credential_id,challenge,branch_id:branchId,probe_instance_id:state.probe_instance_id};
candidate.transition_digest=hash(candidate);
const next={...state,counter:candidate.counter,canonical_head:candidate.successor};
writeFileSync(statePath,JSON.stringify(next,null,2));
output({ok:true,operation:'advance',candidate,guest_before_digest:hash(state),guest_after_digest:hash(next)});
