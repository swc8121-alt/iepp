import {createHash} from 'node:crypto';

const sha=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');

export function verifyTransitionDigest(candidate){
 if(!candidate||typeof candidate!=='object')return false;
 const copy={...candidate};
 delete copy.transition_digest;
 return sha(JSON.stringify(copy))===candidate.transition_digest;
}

export class RegistryCore{
 constructor(){this.reset();}
 reset(){
  this.state={lineage_id:'L-vm-snapshot',status:'ACTIVE',counter:0,canonical_head:'H0',credential_id:'K1',policy_revision:3};
  this.usedChallenges=new Set();
  this.acceptedPredecessors=new Map();
  this.decisionSequence=0;
  return this.snapshot();
 }
 snapshot(){return {...this.state,used_challenge_count:this.usedChallenges.size,accepted_predecessor_count:this.acceptedPredecessors.size};}
 apply(candidate){
  const sequence=++this.decisionSequence;
  const challenge=typeof candidate?.challenge==='string'?candidate.challenge:null;
  const challengeFirstUse=Boolean(challenge)&&!this.usedChallenges.has(challenge);
  let accepted=false,reason='CONTINUITY_ACCEPTED';
  if(!candidate||typeof candidate!=='object')reason='MALFORMED_CANDIDATE';
  else if(candidate.lineage_id!==this.state.lineage_id)reason='LINEAGE_MISMATCH';
  else if(!challenge)reason='MISSING_CHALLENGE';
  else if(!challengeFirstUse)reason='CHALLENGE_REPLAY';
  else if(!verifyTransitionDigest(candidate))reason='TRANSITION_DIGEST_MISMATCH';
  else if(candidate.policy_revision!==this.state.policy_revision)reason='POLICY_REVISION_MISMATCH';
  else if(candidate.credential_id!==this.state.credential_id)reason='CREDENTIAL_MISMATCH';
  else if(candidate.predecessor!==this.state.canonical_head)reason=this.acceptedPredecessors.has(candidate.predecessor)?'FORK_CONFLICT':'STALE_PREDECESSOR';
  else if(candidate.counter!==this.state.counter+1)reason='COUNTER_MISMATCH';
  else {
   accepted=true;
   this.acceptedPredecessors.set(candidate.predecessor,candidate.successor);
   this.state.counter=candidate.counter;
   this.state.canonical_head=candidate.successor;
  }
  if(challenge)this.usedChallenges.add(challenge);
  return {accepted,reason,decision_sequence:sequence,challenge_first_use:challengeFirstUse,state:this.snapshot()};
 }
}

export {sha};
