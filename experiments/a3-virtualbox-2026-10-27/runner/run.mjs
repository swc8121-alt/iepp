#!/usr/bin/env node
import {createHash,randomBytes,randomUUID} from 'node:crypto';
import {spawn,spawnSync} from 'node:child_process';
import {copyFileSync,existsSync,mkdirSync,readFileSync,rmSync,writeFileSync} from 'node:fs';
import {basename,dirname,join,resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import os from 'node:os';
import {resolveGuestPlatform} from './guest-platform.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const argv=process.argv.slice(2);
const value=name=>{const i=argv.indexOf('--'+name);return i>=0?argv[i+1]:undefined;};
const flag=name=>argv.includes('--'+name);
if(flag('help')||flag('h')){
 process.stdout.write(`IEPP A3 two-VM VirtualBox runner v0.2.4.2

Easy Windows-host launch:
  CHECK_IEPP_A3.cmd
  START_IEPP_A3.cmd

Dry-run (no hypervisor evidence):
  node run.mjs --dry-run --output ./evidence-run

Two-VM VirtualBox run:
  node run.mjs --vm-a "IEPP-A" --vm-b "IEPP-B" --guest-user iepp --password-file "C:\\secure\\guest-password.txt" --output ./evidence-run

Required for live evidence:
  Two distinct disposable VMs, Guest Additions, and Node.js 22+ in both guests.

Options:
  --guest-os <auto|linux|windows>  Default guest OS mode for A and B
  --guest-os-a / --guest-os-b     Per-VM guest OS override
  --guest-user-a / --guest-user-b Per-VM account override
  --password-file-a / -b          Per-VM password-file override
  --guest-node-a / --guest-node-b Per-VM Node executable override
  --guest-workdir-a / -b          Per-VM work directory override
  --registry-host <host>           Local registry bind address (default 127.0.0.1)
  --registry-port <port>           Local registry port (default ephemeral)
  --vboxmanage <path>              VBoxManage executable
`);
 process.exit(0);
}

const dryRun=flag('dry-run');
const vmA=value('vm-a');
const vmB=value('vm-b');
const defaultGuestUser=value('guest-user');
const defaultPasswordFile=value('password-file');
const defaultGuestOs=(value('guest-os')||'auto').toLowerCase();
const outputDir=resolve(value('output')||join(process.cwd(),'iepp-a3-evidence-'+new Date().toISOString().replace(/[:.]/g,'-')));
const registryHost=value('registry-host')||'127.0.0.1';
const registryPort=Number(value('registry-port')||0);
const vbox=value('vboxmanage')||'VBoxManage';
if(!['auto','linux','windows'].includes(defaultGuestOs))throw Error('--guest-os must be auto, linux, or windows.');
if(!Number.isInteger(registryPort)||registryPort<0||registryPort>65535)throw Error('--registry-port must be an integer from 0 through 65535.');
if(!dryRun&&(!vmA||!vmB||!defaultGuestUser||!defaultPasswordFile))throw Error('Live mode requires --vm-a, --vm-b, --guest-user, and --password-file.');
if(!dryRun&&vmA===vmB)throw Error('A real controlled race requires two distinct VM names.');

const configFor=(role,vm)=>{
 const lower=role.toLowerCase();
 const guestUser=value(`guest-user-${lower}`)||defaultGuestUser;
 const passwordFile=value(`password-file-${lower}`)||defaultPasswordFile;
 const guestOs=(value(`guest-os-${lower}`)||defaultGuestOs).toLowerCase();
 if(!['auto','linux','windows'].includes(guestOs))throw Error(`--guest-os-${lower} must be auto, linux, or windows.`);
 if(!dryRun&&(!guestUser||!passwordFile||!existsSync(resolve(passwordFile))))throw Error(`VM ${role} password file was not found.`);
 return {role,vm,guestUser,passwordFile:passwordFile?resolve(passwordFile):null,guestOs,nodeOverride:value(`guest-node-${lower}`),workdirOverride:value(`guest-workdir-${lower}`)};
};
const configA=configFor('A',vmA);
const configB=configFor('B',vmB);

mkdirSync(outputDir,{recursive:true});
const manifestPath=join(here,'manifest.json');
const probePath=join(here,'guest-probe.mjs');
const registryServerPath=join(here,'registry-server.mjs');
const manifest=JSON.parse(readFileSync(manifestPath,'utf8'));
const sha=input=>createHash('sha256').update(input).digest('hex');
const fileSha=path=>sha(readFileSync(path));
const now=()=>new Date().toISOString();
const sleep=ms=>new Promise(resolveSleep=>setTimeout(resolveSleep,ms));
const runId='a3-'+new Date().toISOString().replace(/[-:.TZ]/g,'').slice(0,14)+'-'+randomUUID().slice(0,8);
const enrollmentId='E-A3-'+fileSha(probePath).slice(0,24);
const commandLog=[];
const sensitiveStrings=[vmA,vmB,configA.passwordFile,configB.passwordFile].filter(Boolean);
const redact=text=>sensitiveStrings.reduce((result,item)=>result.split(item).join('[REDACTED]'),String(text||''));
function logCommand(program,args,result,meta={}){
 commandLog.push({at:now(),program:basename(program),args:args.map(redact),status:result?.status??0,stderr:redact(result?.stderr).slice(0,1000),...meta});
}
function vboxRun(args,{allowFailure=false,timeout=180000,logMeta={}}={}){
 const result=spawnSync(vbox,args,{encoding:'utf8',timeout,windowsHide:true});
 logCommand(vbox,args,result,logMeta);
 if(result.error&&!allowFailure)throw result.error;
 if(result.status!==0&&!allowFailure)throw Error(`VBoxManage failed (${redact(args.slice(0,3).join(' '))}): ${redact(result.stderr||result.stdout).trim()}`);
 return result;
}
function parseJsonOutput(text){
 for(const line of String(text).trim().split(/\r?\n/).reverse()){
  try{const parsed=JSON.parse(line);if(parsed&&typeof parsed==='object')return parsed;}catch{}
 }
 throw Error('Guest probe did not return JSON.');
}
function parseSnapshotUuid(text,name){
 const pairs=new Map();
 for(const line of String(text).split(/\r?\n/)){
  const match=/^Snapshot(Name|UUID)([^=]*)="([^"]*)"$/.exec(line.trim());
  if(match)pairs.set(`${match[1]}:${match[2]}`,match[3]);
 }
 for(const [key,item] of pairs)if(key.startsWith('Name:')&&item===name)return pairs.get(`UUID:${key.slice(5)}`)||null;
 return null;
}
const cleanOutput=input=>String(input||'').trim()||null;

class LocalAdapter{
 constructor(config){this.role=config.role;this.kind='filesystem-simulation';this.actualVm=false;this.root=join(outputDir,`.sim-guest-${this.role}`);this.state=join(this.root,'state.json');this.base=join(this.root,'snapshot-state.json');}
 async prepare(){mkdirSync(this.root,{recursive:true});this.call(['init','--state',this.state,'--enrollment-id',enrollmentId]);copyFileSync(this.state,this.base);return {role:this.role,product:'local-filesystem-simulator',version:process.version,snapshot:'simulated-genesis'};}
 async restore(){copyFileSync(this.base,this.state);}
 async advance({challenge,successor,branch}){return this.call(['advance','--state',this.state,'--challenge',challenge,'--successor',successor,'--branch',branch]);}
 call(args){const result=spawnSync(process.execPath,[probePath,...args],{encoding:'utf8'});logCommand(process.execPath,['guest-probe',this.role,...args],result,{role:this.role});if(result.status!==0)throw Error(result.stderr||result.stdout);return parseJsonOutput(result.stdout);}
 runtimeMetadata(){return {role:this.role,simulated:true};}
 async finish(){rmSync(this.root,{recursive:true,force:true});}
}

class VirtualBoxAdapter{
 constructor(config){
  Object.assign(this,config);
  this.kind='virtualbox';this.actualVm=true;this.guestNode=null;this.guestWorkdir=null;this.guestState=null;this.guestProbe=null;this.guestNodeVersion=null;this.guestAdditionsVersion=null;this.guestRuntime=null;this.metadataCollected=false;this.readinessSamples=[];
  this.snapshot='iepp-a3-genesis-'+fileSha(probePath).slice(0,10)+'-v'+manifest.runner_version.replace(/\D/g,'');
  this.snapshotUuid=null;
 }
 configure(info){
  const resolved=resolveGuestPlatform({machineInfo:info,requested:this.guestOs,guestUser:this.guestUser,nodeOverride:this.nodeOverride,workdirOverride:this.workdirOverride,role:this.role});
  Object.assign(this,{guestOs:resolved.guestOs,guestOsDeclared:resolved.declaredType,guestNode:resolved.guestNode,guestWorkdir:resolved.guestWorkdir,guestState:resolved.guestState,guestProbe:resolved.guestProbe});
 }
 auth(){return ['--username',this.guestUser,'--passwordfile',this.passwordFile];}
 async state(){
  let lastResult=null;
  for(let attempt=1;attempt<=30;attempt++){
   const result=vboxRun(['showvminfo',this.vm,'--machinereadable'],{allowFailure:true,logMeta:{role:this.role,phase:'vm_state_probe',retry_allowed:true,probe_number:attempt}});
   lastResult=result;
   if(result.status===0)return (/^VMState="([^"]+)"/m.exec(result.stdout)||[])[1]||'unknown';
   const detail=String(result.stderr||result.stdout||'');
   const transient=/VBOX_E_INVALID_OBJECT_STATE|Failed to get a console object from the direct session|VBOX_E_OBJECT_IN_USE|already locked for a session/i.test(detail);
   if(!transient||attempt===30)break;
   await sleep(1000);
  }
  throw Error(`VBoxManage failed (showvminfo [REDACTED] --machinereadable): ${redact(lastResult?.stderr||lastResult?.stdout).trim()}`);
 }
 async ensureOff(){
  const current=await this.state();
  if(current==='poweroff'||current==='saved')return;
  vboxRun(['controlvm',this.vm,'acpipowerbutton'],{allowFailure:true,logMeta:{role:this.role}});
  for(let i=0;i<60;i++){
   await sleep(1000);
   if(await this.state()==='poweroff'){
    await sleep(1000);
    if(await this.state()==='poweroff')return;
   }
  }
  vboxRun(['controlvm',this.vm,'poweroff'],{logMeta:{role:this.role}});
  await sleep(1000);
  if(await this.state()!=='poweroff')throw Error(`Guest ${this.role} did not reach the powered-off state.`);
 }
 guest(args,allowFailure=false,logMeta={}){return vboxRun(['guestcontrol',this.vm,...args],{allowFailure,timeout:180000,logMeta:{role:this.role,...logMeta}});}
 async start(){
  const startedAt=Date.now();let failedProbes=0;
  const candidates=this.guestOs==='linux'&&!this.nodeOverride?[...new Set([this.guestNode,'/snap/node/current/bin/node'])]:[this.guestNode];
  if(await this.state()!=='running')vboxRun(['startvm',this.vm,'--type','headless'],{logMeta:{role:this.role}});
  for(let i=0;i<90;i++){
   await sleep(2000);let unsupported=null;
   for(const nodeCandidate of candidates){
    const result=this.guest(['run',...this.auth(),'--quiet','--exe',nodeCandidate,'--wait-stdout','--wait-stderr','--','--version'],true,{phase:'guest_readiness_probe',retry_allowed:true,probe_number:i+1,node_candidate:nodeCandidate});
    if(result.status===0){
     const version=(/v(\d+)\.[\d.]+/.exec(result.stdout)||[])[0];
     const major=Number((/v(\d+)/.exec(result.stdout)||[])[1]);
     if(major>=22){this.guestNode=nodeCandidate;this.guestNodeVersion=version;this.readinessSamples.push({ready:true,elapsed_ms:Date.now()-startedAt,failed_probes:failedProbes});await this.collectGuestMetadata();return;}
     if(major)unsupported=version;
    }else failedProbes++;
   }
   if(unsupported)throw Error(`Guest ${this.role} requires Node.js 22 or newer; found ${unsupported}.`);
  }
  this.readinessSamples.push({ready:false,elapsed_ms:Date.now()-startedAt,failed_probes:failedProbes});
  throw Error(`Guest ${this.role} Additions, credentials, or Node did not become ready within 180 seconds.`);
 }
 async collectGuestMetadata(){
  if(this.metadataCollected)return;
  this.metadataCollected=true;
  const additions=vboxRun(['guestproperty','get',this.vm,'/VirtualBox/GuestAdd/Version'],{allowFailure:true,logMeta:{role:this.role,phase:'guest_metadata'}});
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
  return {role:this.role,guest_os_declared:this.guestOsDeclared,guest_node:this.guestNode,guest_node_version:this.guestNodeVersion,guest_additions_version:this.guestAdditionsVersion,guest_runtime:this.guestRuntime,snapshot_uuid:this.snapshotUuid,readiness:{timeout_seconds:180,sessions:this.readinessSamples.length,successful_sessions:durations.length,failed_probe_attempts:this.readinessSamples.reduce((n,x)=>n+x.failed_probes,0),elapsed_ms:{min:durations.length?durations[0]:null,median,max:durations.length?durations.at(-1):null,mean:durations.length?Math.round(sum/durations.length):null}}};
 }
 async prepare(){
  const vmInfo=vboxRun(['showvminfo',this.vm,'--machinereadable'],{logMeta:{role:this.role}});
  this.configure(vmInfo.stdout);
  const snapshots=vboxRun(['snapshot',this.vm,'list','--machinereadable'],{allowFailure:true,logMeta:{role:this.role}}).stdout;
  this.snapshotUuid=parseSnapshotUuid(snapshots,this.snapshot);
  if(this.snapshotUuid)return {role:this.role,product:'Oracle VM VirtualBox',version:vboxRun(['--version']).stdout.trim(),guest_os:this.guestOs,guest_node:this.guestNode,snapshot:this.snapshot,reused_snapshot:true};
  await this.start();
  this.guest(['mkdir',...this.auth(),'--parents',this.guestWorkdir],true);
  this.guest(['copyto',...this.auth(),probePath,this.guestProbe]);
  const init=this.guest(['run',...this.auth(),'--quiet','--exe',this.guestNode,'--wait-stdout','--wait-stderr','--',this.guestProbe,'init','--state',this.guestState,'--enrollment-id',enrollmentId]);
  const initialized=parseJsonOutput(init.stdout);
  if(!initialized.ok||initialized.state_public?.probe_instance_id!==enrollmentId)throw Error(`Guest ${this.role} enrollment failed.`);
  await this.ensureOff();
  const taken=vboxRun(['snapshot',this.vm,'take',this.snapshot,'--description','IEPP A3 v0.2.4.2 clean genesis; probe '+fileSha(probePath).slice(0,16)],{logMeta:{role:this.role}});
  this.snapshotUuid=(/UUID:\s*([0-9a-f-]+)/i.exec(String(taken.stdout||''))||[])[1]||null;
  if(!this.snapshotUuid)this.snapshotUuid=parseSnapshotUuid(vboxRun(['snapshot',this.vm,'list','--machinereadable'],{logMeta:{role:this.role}}).stdout,this.snapshot);
  return {role:this.role,product:'Oracle VM VirtualBox',version:vboxRun(['--version']).stdout.trim(),guest_os:this.guestOs,guest_node:this.guestNode,snapshot:this.snapshot,reused_snapshot:false};
 }
 async restore(){await this.ensureOff();vboxRun(['snapshot',this.vm,'restore',this.snapshot],{logMeta:{role:this.role}});await this.start();}
 async advance({challenge,successor,branch}){
  const result=this.guest(['run',...this.auth(),'--quiet','--exe',this.guestNode,'--wait-stdout','--wait-stderr','--',this.guestProbe,'advance','--state',this.guestState,'--challenge',challenge,'--successor',successor,'--branch',branch]);
  return parseJsonOutput(result.stdout);
 }
 async finish(){await this.ensureOff();}
}

async function startRegistry(){
 const eventLog=join(outputDir,'registry-events.jsonl');
 rmSync(eventLog,{force:true});
 const adminToken=randomBytes(32).toString('hex');
 const child=spawn(process.execPath,[registryServerPath,'--host',registryHost,'--port',String(registryPort),'--event-log',eventLog],{env:{...process.env,IEPP_REGISTRY_ADMIN_TOKEN:adminToken},stdio:['ignore','pipe','pipe'],windowsHide:true});
 commandLog.push({at:now(),program:'node',args:['registry-server.mjs','--host',registryHost,'--port',String(registryPort),'--event-log','registry-events.jsonl'],status:0,phase:'registry_start'});
 let stderr='',buffer='';
 child.stderr.on('data',chunk=>{stderr+=String(chunk).slice(0,4000);});
 const ready=await new Promise((resolveReady,reject)=>{
  const timer=setTimeout(()=>reject(Error('Registry process did not become ready within 10 seconds.')),10000);
  child.once('exit',code=>{clearTimeout(timer);reject(Error(`Registry process exited before ready (${code}): ${stderr}`));});
  child.stdout.on('data',chunk=>{
   buffer+=String(chunk);
   while(buffer.includes('\n')){
    const index=buffer.indexOf('\n'),line=buffer.slice(0,index);buffer=buffer.slice(index+1);
    try{const parsed=JSON.parse(line);if(parsed.ready){clearTimeout(timer);resolveReady(parsed);return;}}catch{}
   }
  });
 });
 const base=`http://${ready.host}:${ready.port}`;
 const request=async(path,{method='GET',body,admin=false,timeout=15000}={})=>{
  const headers={'accept':'application/json'};
  if(body!==undefined)headers['content-type']='application/json';
  if(admin)headers['x-iepp-admin-token']=adminToken;
  const response=await fetch(base+path,{method,headers,body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(timeout)});
  const parsed=await response.json();
  if(!response.ok||!parsed.ok)throw Error(`REGISTRY_${response.status}:${parsed.error||'UNKNOWN'}`);
  return parsed;
 };
 await request('/health');
 return {
  child,base,eventLog,pid:ready.pid,
  reset:()=>request('/admin/reset',{method:'POST',body:{},admin:true}),
  events:()=>request('/admin/events',{admin:true}),
  submit:async({trialId,label,candidate,raceId=null,barrierExpected=1,delayMs=0})=>{
   if(delayMs)await sleep(delayMs);
   const requestId=randomUUID();
   const clientStarted=process.hrtime.bigint();
   const result=await request('/submit',{method:'POST',body:{request_id:requestId,trial_id:trialId,label,candidate,race_id:raceId,barrier_expected:barrierExpected},timeout:30000});
   const clientFinished=process.hrtime.bigint();
   return {...result.event,client_timing_ns:{request_started:clientStarted.toString(),response_received:clientFinished.toString()},configured_client_delay_ms:delayMs};
  },
  shutdown:async()=>{try{await request('/admin/shutdown',{method:'POST',body:{},admin:true,timeout:3000});}catch{}if(child.exitCode===null)child.kill('SIGTERM');}
 };
}

const adapters=dryRun?[new LocalAdapter(configA),new LocalAdapter(configB)]:[new VirtualBoxAdapter(configA),new VirtualBoxAdapter(configB)];
const [adapterA,adapterB]=adapters;
const actualVm=adapters.every(adapter=>adapter.actualVm);
const challenge=(trialId,label)=>sha(`${runId}|${trialId}|${label}|${randomUUID()}`);
async function restoreBoth(){await adapterA.restore();await adapterB.restore();}
async function makeCandidate(adapter,trialId,label,challengeValue){
 const response=await adapter.advance({challenge:challengeValue,successor:`H-${trialId}-${label}`,branch:label});
 if(!response.ok)throw Error(response.error||'GUEST_PROBE_FAILED');
 if(response.candidate.probe_instance_id!==enrollmentId)throw Error(`Guest ${adapter.role} has a mismatched enrollment state. Delete only the v0.2.4.2 snapshot and retry.`);
 return response.candidate;
}
const processingOverlap=(left,right)=>BigInt(left.timing_ns.server_received)<BigInt(right.timing_ns.cas_finished)&&BigInt(right.timing_ns.server_received)<BigInt(left.timing_ns.cas_finished);
const casOverlap=(left,right)=>BigInt(left.timing_ns.cas_started)<BigInt(right.timing_ns.cas_finished)&&BigInt(right.timing_ns.cas_started)<BigInt(left.timing_ns.cas_finished);
const acceptedCount=events=>events.filter(event=>event.decision.accepted).length;
const reasonCount=(events,reason)=>events.filter(event=>event.decision.reason===reason).length;

async function executeTrial(registry,trialId,scenario,indexInGroup){
 await registry.reset();
 const steps=[];
 const record=(label,candidate,event)=>{steps.push({label,candidate,registry_event:event});return event;};
 const submit=async(label,candidate,options={})=>record(label,candidate,await registry.submit({trialId,label,candidate,...options}));
 let pass=false,raceObservation=null;
 if(scenario==='r1_baseline_continue'){
  await adapterA.restore();
  const a=await makeCandidate(adapterA,trialId,'A',challenge(trialId,'A'));
  const first=await submit('A',a);
  pass=first.decision.accepted&&first.decision.reason==='CONTINUITY_ACCEPTED';
 }
 if(scenario==='r2_fresh_order_ab'||scenario==='r3_fresh_order_ba'){
  await restoreBoth();
  const a=await makeCandidate(adapterA,trialId,'A',challenge(trialId,'A'));
  const b=await makeCandidate(adapterB,trialId,'B',challenge(trialId,'B'));
  const order=scenario.endsWith('ab')?[['A',a],['B',b]]:[['B',b],['A',a]];
  const first=await submit(order[0][0],order[0][1]);
  const second=await submit(order[1][0],order[1][1]);
  pass=first.decision.accepted&&!second.decision.accepted&&second.decision.reason==='FORK_CONFLICT';
 }
 if(scenario==='r4_controlled_race_fresh'||scenario==='r7_controlled_race_shared_challenge'){
  await restoreBoth();
  const shared=scenario.includes('shared')?challenge(trialId,'shared'):null;
  const a=await makeCandidate(adapterA,trialId,'A',shared||challenge(trialId,'A'));
  const b=await makeCandidate(adapterB,trialId,'B',shared||challenge(trialId,'B'));
  const [delayA,delayB]=manifest.race_delay_profiles_ms[indexInGroup%manifest.race_delay_profiles_ms.length];
  const raceId=`${trialId}-${randomUUID()}`;
  const [eventA,eventB]=await Promise.all([
   registry.submit({trialId,label:'A',candidate:a,raceId,barrierExpected:2,delayMs:delayA}),
   registry.submit({trialId,label:'B',candidate:b,raceId,barrierExpected:2,delayMs:delayB})
  ]);
  record('A',a,eventA);record('B',b,eventB);
  const events=[eventA,eventB];
  raceObservation={race_id:raceId,configured_client_delay_ms:{A:delayA,B:delayB},server_processing_interval_overlap:processingOverlap(eventA,eventB),cas_interval_overlap:casOverlap(eventA,eventB),barrier_released_by_participant_count:events.every(event=>event.barrier.released_by==='participant-count'),accepted_count:acceptedCount(events),received_order:[...events].sort((x,y)=>BigInt(x.timing_ns.server_received)<BigInt(y.timing_ns.server_received)?-1:1).map(event=>event.label)};
  const losingReason=scenario.startsWith('r4_')?'FORK_CONFLICT':'CHALLENGE_REPLAY';
  pass=raceObservation.server_processing_interval_overlap&&!raceObservation.cas_interval_overlap&&raceObservation.barrier_released_by_participant_count&&acceptedCount(events)===1&&reasonCount(events,losingReason)===1;
 }
 if(scenario==='r5_shared_challenge_ab'||scenario==='r6_shared_challenge_ba'){
  await restoreBoth();
  const shared=challenge(trialId,'shared');
  const a=await makeCandidate(adapterA,trialId,'A',shared);
  const b=await makeCandidate(adapterB,trialId,'B',shared);
  const order=scenario.endsWith('ab')?[['A',a],['B',b]]:[['B',b],['A',a]];
  const first=await submit(order[0][0],order[0][1]);
  const second=await submit(order[1][0],order[1][1]);
  pass=first.decision.accepted&&!second.decision.accepted&&second.decision.reason==='CHALLENGE_REPLAY'&&first.decision.challenge_first_use&&!second.decision.challenge_first_use;
 }
 if(scenario==='r8_consumed_before_restore'){
  await restoreBoth();
  const beforeChallenge=challenge(trialId,'before-restore');
  const before=await makeCandidate(adapterA,trialId,'before-restore',beforeChallenge);
  const accepted=await submit('before-restore',before);
  await restoreBoth();
  const afterChallenge=challenge(trialId,'after-restore-distinct');
  const after=await makeCandidate(adapterB,trialId,'after-restore-distinct',afterChallenge);
  const rejected=await submit('after-restore-distinct',after);
  pass=beforeChallenge!==afterChallenge&&accepted.decision.accepted&&!rejected.decision.accepted&&rejected.decision.reason==='FORK_CONFLICT';
 }
 const finalRegistry=steps.at(-1)?.registry_event.decision.state||null;
 return {trial_id:trialId,scenario,pass,vm_restore_observed:actualVm,guest_roles:[...new Set(steps.map(step=>step.label.startsWith('B')||step.label.includes('after')?'B':'A'))],race_observation:raceObservation,steps,final_registry:finalRegistry};
}

let registry=null,environment=[],trials=[],registryEvents=[];
let executionError=null;
try{
 registry=await startRegistry();
 environment.push(await adapterA.prepare());
 environment.push(await adapterB.prepare());
 let trialNumber=0;
 for(const group of manifest.groups){
  for(let index=0;index<group.count;index++){
   trialNumber++;
   const trialId=String(trialNumber).padStart(2,'0');
   const trial=await executeTrial(registry,trialId,group.scenario,index);
   trials.push(trial);
   process.stdout.write(`[${trialNumber}/${manifest.total_trials}] ${group.scenario} ${trial.pass?'PASS':'FAIL'}\n`);
  }
 }
 registryEvents=(await registry.events()).events;
}catch(error){executionError=error;}
finally{
 if(registry)await registry.shutdown();
 for(const adapter of adapters){try{await adapter.finish();}catch(error){executionError=executionError||error;}}
}
if(executionError)throw executionError;

let previous='0'.repeat(64);
const chained=trials.map(row=>{const body={...row,evidence_prev_hash:previous};const evidenceHash=sha(JSON.stringify(body));previous=evidenceHash;return {...body,evidence_hash:evidenceHash};});
const counts=Object.fromEntries(manifest.groups.map(group=>[group.scenario,{passed:chained.filter(trial=>trial.scenario===group.scenario&&trial.pass).length,total:group.count}]));
const allPassed=chained.length===manifest.total_trials&&chained.every(trial=>trial.pass);
const raceTrials=chained.filter(trial=>trial.race_observation);
const allRaceOverlap=raceTrials.length===8&&raceTrials.every(trial=>trial.race_observation.server_processing_interval_overlap);
const noCasOverlap=raceTrials.length===8&&raceTrials.every(trial=>!trial.race_observation.cas_interval_overlap);
const oneAcceptedEveryRace=raceTrials.length===8&&raceTrials.every(trial=>trial.race_observation.accepted_count===1);
const vmHashes=actualVm?[sha(vmA),sha(vmB)]:[];
const summary={
 format:'iepp-a3-virtualbox-summary-v1',runner_version:manifest.runner_version,run_id:runId,generated_at:now(),
 execution:{actual_vm_executed:actualVm,distinct_vm_count:actualVm?new Set([vmA,vmB]).size:0,adapter:actualVm?'virtualbox-two-vm':'two-filesystem-simulators',registry:{process_boundary:'separate-node-process',transport:'HTTP/1.1',bind_host:registryHost,port_mode:registryPort===0?'ephemeral':'fixed',event_count:registryEvents.length},hypervisor:environment.map((item,index)=>({...item,...adapters[index].runtimeMetadata()})),host:{platform:os.platform(),release:os.release(),arch:os.arch()},vm_name_hashes:vmHashes},
 scope:{
  observation_level:actualVm?'TWO_VM_OBSERVED':'SIMULATION_ONLY',claim_level:'L1_REGISTRY_RELATIVE_CONTINUATION',
  claims:{orchestration_completed:allPassed,network_registry_process_exercised:allPassed,two_distinct_vm_snapshots_restored:actualVm&&allPassed,symmetric_ordering_observed:actualVm&&counts.r2_fresh_order_ab.passed===counts.r2_fresh_order_ab.total&&counts.r3_fresh_order_ba.passed===counts.r3_fresh_order_ba.total,server_observed_request_overlap:actualVm&&allRaceOverlap,atomic_single_successor_observed:actualVm&&oneAcceptedEveryRace&&noCasOverlap,single_use_challenge_observed:actualVm&&counts.r5_shared_challenge_ab.passed===counts.r5_shared_challenge_ab.total&&counts.r6_shared_challenge_ba.passed===counts.r6_shared_challenge_ba.total&&counts.r7_controlled_race_shared_challenge.passed===counts.r7_controlled_race_shared_challenge.total,pre_restore_challenge_survived_guest_restore:actualVm&&counts.r8_consumed_before_restore.passed===counts.r8_consumed_before_restore.total,runtime_originality_proved:false,clone_resistance_proved:false,hardware_root_used:false,cryptographic_guest_authentication:false,distributed_consensus_proved:false,independent_entropy_benefit_proved:false},
  note:actualVm?'Two distinct VM snapshots and a separate HTTP registry process were exercised. The result remains an L1, registry-relative canonical-continuation observation; it does not identify a physical or original runtime.':'The two-producer orchestration, HTTP registry boundary, concurrency barrier, and evidence pipeline ran without VirtualBox. No VM or hypervisor evidence was produced.'
 },
 race_metrics:{race_trials:raceTrials.length,server_processing_overlap_trials:raceTrials.filter(trial=>trial.race_observation.server_processing_interval_overlap).length,cas_overlap_trials:raceTrials.filter(trial=>trial.race_observation.cas_interval_overlap).length,single_accept_trials:raceTrials.filter(trial=>trial.race_observation.accepted_count===1).length},
 counts,total_trials:chained.length,passed_trials:chained.filter(trial=>trial.pass).length,registry_event_count:registryEvents.length,evidence_chain_head:previous,
 source_hashes:{manifest_sha256:fileSha(manifestPath),guest_probe_sha256:fileSha(probePath),registry_core_sha256:fileSha(join(here,'registry-core.mjs')),registry_server_sha256:fileSha(registryServerPath),runner_sha256:fileSha(fileURLToPath(import.meta.url))}
};

writeFileSync(join(outputDir,'trials.jsonl'),chained.map(row=>JSON.stringify(row)).join('\n')+'\n');
writeFileSync(join(outputDir,'commands.jsonl'),commandLog.map(row=>JSON.stringify(row)).join('\n')+'\n');
writeFileSync(join(outputDir,'summary.json'),JSON.stringify(summary,null,2)+'\n');
const integrity={format:'iepp-a3-integrity-v1',generated_at:now(),files:{'summary.json':fileSha(join(outputDir,'summary.json')),'trials.jsonl':fileSha(join(outputDir,'trials.jsonl')),'commands.jsonl':fileSha(join(outputDir,'commands.jsonl')),'registry-events.jsonl':fileSha(join(outputDir,'registry-events.jsonl'))},evidence_chain_head:previous,registry_event_count:registryEvents.length};
writeFileSync(join(outputDir,'integrity.json'),JSON.stringify(integrity,null,2)+'\n');
const report=`# IEPP A3 2-VM 경쟁 시험 보고서\n\n- 실행 ID: \`${runId}\`\n- 생성 시각: ${summary.generated_at}\n- 실제 VM 실행: **${actualVm?'예 — 서로 다른 VM 2개':'아니오 — 드라이런'}**\n- 관측 수준: \`${summary.scope.observation_level}\`\n- 보안 주장 수준: \`${summary.scope.claim_level}\`\n- 레지스트리: 별도 Node 프로세스 / HTTP\n- 통과: ${summary.passed_trials}/${summary.total_trials}\n- 서버 관측 요청 겹침: ${summary.race_metrics.server_processing_overlap_trials}/${summary.race_metrics.race_trials}\n- CAS 구간 겹침: ${summary.race_metrics.cas_overlap_trials}/${summary.race_metrics.race_trials}\n- 증거 체인 head: \`${previous}\`\n\n## 시나리오\n\n${Object.entries(counts).map(([name,count])=>`- ${name}: ${count.passed}/${count.total}`).join('\n')}\n\n## 주장 경계\n\n${summary.scope.note}\n런타임 원본성, clone-resistance, PUF/TEE/하드웨어 신뢰루트, 분산 합의, 복구 거버넌스, 독립적인 엔트로피 효과는 이 시험으로 증명하지 않습니다.\n`;
writeFileSync(join(outputDir,'REPORT_KO.md'),report);
process.stdout.write(`Evidence: ${outputDir}\nActual VM executed: ${actualVm}\nPassed: ${summary.passed_trials}/${summary.total_trials}\n`);
if(!allPassed)process.exitCode=1;
