import {test} from 'node:test';
import assert from 'node:assert/strict';
import {projectRepoCatchupSnapshot,repoCatchupStatus} from '../integrations/hud-cloud/repo-catchup.mjs';

const NOW=1794916800000;
const A='a'.repeat(40),B='b'.repeat(40);
const good=()=>({
 head_sha:A,recent_commit_shas:[A,B],scanned_commit_count:2,
 commit_file_counts:[{sha:A,files_observed:2,paths_truncated:false},
  {sha:B,files_observed:30,paths_truncated:true}],
 changed_paths:['integrations/hud-cloud/worker.mjs','docs/test.md'],
 changed_paths_truncated:true,failed_run_ids:[123456],recent_success_run_ids:[123455],
 open_issue_numbers:[12],open_pr_numbers:[314,456]
});
const row=(snapshot,state='ready')=>({
 checked_at:NOW-1000,observed_at:NOW-2000,state,
 snapshot:typeof snapshot==='string'?snapshot:JSON.stringify(snapshot)
});
const envWith=entry=>({DB:{prepare(sql){
 assert.match(sql,/hud_native_repo_catchup/);
 return {bind(){return {first:async()=>entry}}};
}}});

test('valid last-good catch-up remains readable, including during a failed GitHub refresh',async()=>{
 const data=good();
 assert.deepEqual(projectRepoCatchupSnapshot(data),data);
 const status=await repoCatchupStatus(envWith(row(data,'read_unavailable')),NOW);
 assert.equal(status.state,'read_unavailable');
 assert.equal(status.snapshot_freshness,'fresh');
 assert.deepEqual(status.snapshot,data);
 assert.equal(status.open_pr_count_is_total,false);
 assert.equal(status.model_called,false);
 assert.equal(status.repository_written,false);
 assert.equal(status.mac_required,false);
 assert.equal((await repoCatchupStatus(envWith(row(data)),NOW+3*3600000)).snapshot_freshness,'stale');
});

test('private D1 extra and nested fields are removed, not echoed to reader',async()=>{
 const data={...good(),api_token:'ghp_PRIVATE_NOT_METADATA',nested:{prompt:'private model text'},
  commit_file_counts:[{...good().commit_file_counts[0],secret:'DO_NOT_EXPOSE'},
   {...good().commit_file_counts[1],extra:{hidden:true}}]};
 const original=JSON.stringify(data);
 const status=await repoCatchupStatus(envWith(row(original)),NOW);
 assert.equal(status.state,'ready');
 assert.equal(status.snapshot_freshness,'fresh');
 assert.deepEqual(status.snapshot,good());
 const output=JSON.stringify(status);
 assert(!output.includes('PRIVATE_NOT_METADATA'));
 assert(!output.includes('DO_NOT_EXPOSE'));
 assert(!output.includes('private model text'));
 assert(!output.includes('"extra"'));
 assert.equal(JSON.stringify(data),original,'projection must not mutate the receipt');
});

test('inconsistent and forged snapshots never become fresh agent evidence',async()=>{
 const samples=[
  {...good(),head_sha:B},
  {...good(),scanned_commit_count:3},
  {...good(),recent_commit_shas:[A,A]},
  {...good(),commit_file_counts:[{sha:B,files_observed:2,paths_truncated:false},good().commit_file_counts[1]]},
  {...good(),commit_file_counts:[{sha:A,files_observed:31,paths_truncated:false},good().commit_file_counts[1]]},
  {...good(),changed_paths_truncated:false},
  {...good(),changed_paths:['safe.js','secret\nBearer PRIVATE']},
  {...good(),changed_paths:Array.from({length:25},(_,i)=>'file-'+i+'.md')},
  {...good(),open_pr_numbers:[314,314]},
  {...good(),open_issue_numbers:['12']},
  {...good(),failed_run_ids:[Number.MAX_SAFE_INTEGER+1]},
  {...good(),open_pr_numbers:Array.from({length:9},(_,i)=>i+1)},
  {...good(),recent_success_run_ids:'123'},
  {...good(),commit_file_counts:[null,good().commit_file_counts[1]]},
  []
 ];
 for(const data of samples){
  assert.equal(projectRepoCatchupSnapshot(data),null);
  const status=await repoCatchupStatus(envWith(row(data)),NOW);
  assert.equal(status.state,'snapshot_invalid');
  assert.equal(status.snapshot,null);
  assert.equal(status.observed_at,null);
  assert.equal(status.snapshot_freshness,'unavailable');
 }
});

test('malformed, oversized and missing D1 snapshots fail closed',async()=>{
 for(const invalid of ['{','x'.repeat(16001),'{"secret":"PRIVATE"}']){
  const s=await repoCatchupStatus(envWith(row(invalid)),NOW);
  assert.equal(s.state,'snapshot_invalid');
  assert.equal(s.snapshot,null);
  assert(!JSON.stringify(s).includes('PRIVATE'));
 }
 const missing=await repoCatchupStatus(envWith(null),NOW);
 assert.equal(missing.state,'not_checked');
 assert.equal(missing.snapshot_freshness,'unavailable');
 assert.equal(missing.snapshot,null);
});

test('stored status and timestamps cannot inject unsupported or false freshness data',async()=>{
 const data=row(good());
 const s=await repoCatchupStatus(envWith({...data,state:'Bearer PRIVATE',observed_at:'PRIVATE',checked_at:'PRIVATE'}),NOW);
 assert.equal(s.state,'unavailable');
 assert.equal(s.checked_at,null);
 assert.equal(s.observed_at,null);
 assert.equal(s.snapshot_freshness,'unavailable');
 assert(!JSON.stringify(s).includes('PRIVATE'));
 const future=await repoCatchupStatus(envWith({...data,observed_at:NOW+1000}),NOW);
 assert.equal(future.snapshot_freshness,'unavailable');
});
