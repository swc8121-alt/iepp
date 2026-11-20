#!/usr/bin/env node
import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
const dir=resolve(process.argv[2]||'.');
const sha=value=>createHash('sha256').update(value).digest('hex');
const integrity=JSON.parse(readFileSync(join(dir,'integrity.json'),'utf8'));
for(const [file,expected] of Object.entries(integrity.files)){const actual=sha(readFileSync(join(dir,file)));if(actual!==expected)throw Error(`HASH_MISMATCH:${file}`);}
let previous='0'.repeat(64),count=0;
for(const line of readFileSync(join(dir,'trials.jsonl'),'utf8').trim().split(/\r?\n/)){const row=JSON.parse(line),given=row.evidence_hash;delete row.evidence_hash;if(row.evidence_prev_hash!==previous||sha(JSON.stringify(row))!==given)throw Error(`CHAIN_MISMATCH:${row.trial_id}`);previous=given;count++;}
if(previous!==integrity.evidence_chain_head)throw Error('CHAIN_HEAD_MISMATCH');
process.stdout.write(JSON.stringify({ok:true,verified_files:Object.keys(integrity.files).length,verified_trials:count,evidence_chain_head:previous},null,2)+'\n');
