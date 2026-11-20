#!/usr/bin/env node
import {appendFileSync,mkdirSync} from 'node:fs';
import {createServer} from 'node:http';
import {dirname,resolve} from 'node:path';
import {RegistryCore,sha} from './registry-core.mjs';

const argv=process.argv.slice(2);
const value=name=>{const i=argv.indexOf('--'+name);return i>=0?argv[i+1]:undefined;};
const host=value('host')||'127.0.0.1';
const port=Number(value('port')||0);
const eventLog=resolve(value('event-log')||'registry-events.jsonl');
const adminToken=process.env.IEPP_REGISTRY_ADMIN_TOKEN||'';
if(!adminToken)throw Error('IEPP_REGISTRY_ADMIN_TOKEN is required.');
mkdirSync(dirname(eventLog),{recursive:true});

const core=new RegistryCore();
const events=[];
const barriers=new Map();
const ns=()=>process.hrtime.bigint();
const nsString=value=>value.toString();
const reply=(res,status,body)=>{const text=JSON.stringify(body);res.writeHead(status,{'content-type':'application/json','content-length':Buffer.byteLength(text),'cache-control':'no-store'});res.end(text);};
const readBody=req=>new Promise((resolveBody,reject)=>{let bytes=0,text='';req.setEncoding('utf8');req.on('data',chunk=>{bytes+=Buffer.byteLength(chunk);if(bytes>1024*1024){reject(Error('BODY_TOO_LARGE'));req.destroy();return;}text+=chunk;});req.on('end',()=>{try{resolveBody(text?JSON.parse(text):{});}catch{reject(Error('INVALID_JSON'));}});req.on('error',reject);});
const isAdmin=req=>req.headers['x-iepp-admin-token']===adminToken;

function waitAtBarrier(raceId,expected,timeoutMs=5000){
 if(!raceId)return Promise.resolve({participants:1,released_by:'not-required'});
 let barrier=barriers.get(raceId);
 if(!barrier){barrier={expected,arrived:0,waiters:[],timer:null};barriers.set(raceId,barrier);}
 if(barrier.expected!==expected)return Promise.reject(Error('BARRIER_EXPECTED_MISMATCH'));
 barrier.arrived++;
 return new Promise((resolveWait,reject)=>{
  barrier.waiters.push(resolveWait);
  if(barrier.arrived===barrier.expected){
   if(barrier.timer)clearTimeout(barrier.timer);
   const result={participants:barrier.arrived,released_by:'participant-count'};
   for(const waiter of barrier.waiters)waiter(result);
   barriers.delete(raceId);
  }else if(!barrier.timer){
   barrier.timer=setTimeout(()=>{
    barriers.delete(raceId);
    for(const waiter of barrier.waiters)waiter({participants:barrier.arrived,released_by:'timeout'});
   },timeoutMs);
  }
 });
}

const server=createServer(async(req,res)=>{
 const received=ns();
 try{
  if(req.method==='GET'&&req.url==='/health')return reply(res,200,{ok:true,service:'iepp-a3-registry',version:'0.2.4.2'});
  if(req.url?.startsWith('/admin/')&&!isAdmin(req))return reply(res,403,{ok:false,error:'ADMIN_FORBIDDEN'});
  if(req.method==='POST'&&req.url==='/admin/reset'){
   barriers.clear();
   return reply(res,200,{ok:true,state:core.reset()});
  }
  if(req.method==='GET'&&req.url==='/admin/events')return reply(res,200,{ok:true,events});
  if(req.method==='POST'&&req.url==='/admin/shutdown'){
   reply(res,200,{ok:true});
   setImmediate(()=>server.close(()=>process.exit(0)));
   return;
  }
  if(req.method!=='POST'||req.url!=='/submit')return reply(res,404,{ok:false,error:'NOT_FOUND'});
  const body=await readBody(req);
  const verificationStarted=ns();
  const candidate=body.candidate;
  const candidateDigest=sha(JSON.stringify(candidate||null));
  const verificationReady=ns();
  const barrierResult=await waitAtBarrier(body.race_id||null,Number(body.barrier_expected||1));
  const barrierReleased=ns();
  const casStarted=ns();
  const decision=core.apply(candidate);
  const casFinished=ns();
  const event={
   format:'iepp-a3-registry-event-v1',
   request_id:String(body.request_id||''),
   trial_id:String(body.trial_id||''),
   label:String(body.label||''),
   race_id:body.race_id||null,
   candidate_digest:candidateDigest,
   candidate,
   timing_ns:{
    server_received:nsString(received),
    verification_started:nsString(verificationStarted),
    verification_ready:nsString(verificationReady),
    barrier_released:nsString(barrierReleased),
    cas_started:nsString(casStarted),
    cas_finished:nsString(casFinished)
   },
   barrier:barrierResult,
   decision
  };
  events.push(event);
  appendFileSync(eventLog,JSON.stringify(event)+'\n');
  reply(res,200,{ok:true,event});
 }catch(error){reply(res,400,{ok:false,error:String(error?.message||error)});}
});

server.listen(port,host,()=>{
 const address=server.address();
 process.stdout.write(JSON.stringify({ok:true,ready:true,host,port:address.port,pid:process.pid})+'\n');
});

for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>server.close(()=>process.exit(0)));
