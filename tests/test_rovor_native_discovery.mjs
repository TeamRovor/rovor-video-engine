import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,verify} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {mintGithubReadToken} from '../integrations/hud-cloud/github-app.mjs';
import {repoCatchupStatus} from '../integrations/hud-cloud/repo-catchup.mjs';
import {nativeDiscoveryTick,nativeDiscoveryStatus} from '../integrations/hud-cloud/native-github-discovery.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
const NOW=Date.now(),R='r'.repeat(40),W='w'.repeat(40);
const pair=generateKeyPairSync('rsa',{modulusLength:2048});
const pem=pair.privateKey.export({type:'pkcs1',format:'pem'});
function setup(){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(sql){return{bind(...a){return{
 first:async()=>sqlite.prepare(sql).get(...a)??null,all:async()=>({results:sqlite.prepare(sql).all(...a)}),
 run:async()=>({meta:{changes:sqlite.prepare(sql).run(...a).changes}})
 }}}}};
 return {sqlite,env:{DB,HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,
  ROVOR_GITHUB_APP_ID:'123',ROVOR_GITHUB_INSTALLATION_ID:'456',ROVOR_GITHUB_APP_PRIVATE_KEY:pem,
  ROVOR_NATIVE_DISCOVERY_ENABLED:'true'}};
}
function arm(sqlite){sqlite.exec("UPDATE hud_cloud_workforce_control SET enabled=1");sqlite.prepare("UPDATE hud_cloud_workforce_series SET active=1,source_commit=?,approved_at=?,expires_at=?").run('a'.repeat(40),NOW-1000,NOW+86400000);}
function upstream(calls,extra={}){
 return async(url,init)=>{
 calls.push({url,method:init.method});assert.equal(init.redirect,'manual');
 if(url==='https://api.github.com/app/installations/456/access_tokens'){
  const [h,p,s]=init.headers.Authorization.slice(7).split('.');
  assert(verify('RSA-SHA256',Buffer.from(h+'.'+p),pair.publicKey,Buffer.from(s,'base64url')));
  assert.equal(JSON.parse(Buffer.from(p,'base64url')).iss,'123');
  assert.deepEqual(JSON.parse(init.body),{repositories:['rovor-video-engine'],permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read'}});
  return Response.json({token:'mock-installation-token-123456',expires_at:new Date(NOW+3600000).toISOString(),permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read',metadata:'read'},...extra},{status:201});
 }
 assert.equal(init.headers.Authorization,'Bearer mock-installation-token-123456');
 assert.equal(init.method,'GET');assert(url.startsWith('https://api.github.com/repos/TeamRovor/rovor-video-engine/'));
 if(url.includes('/actions/runs'))return Response.json({workflow_runs:[{id:123456,head_branch:'main',conclusion:'failure',event:'push',created_at:new Date(NOW-5000).toISOString(),name:'CI'}]});
 if(url.endsWith('/commits?sha=main&per_page=4'))return Response.json([{sha:'a'.repeat(40)},{sha:'b'.repeat(40)}]);
 if(url.endsWith('/commits/'+'a'.repeat(40)+'?per_page=30'))return Response.json({sha:'a'.repeat(40),files:[{filename:'architecture/ROVOR-AUTONOMOUS-DISCOVERY.md'},{filename:'integrations/hud-cloud/worker.mjs'}]});
 if(url.endsWith('/commits/'+'b'.repeat(40)+'?per_page=30'))return Response.json({sha:'b'.repeat(40),files:[{filename:'design/pipeline.md'},{filename:'integrations/hud-cloud/worker.mjs'}]});
 if(url.includes('/issues'))return Response.json([]);
 if(url.includes('/pulls'))return Response.json([]);
 throw Error('unexpected_url');
 };
}
test('native clock discovers one real evidence key with scoped GitHub App token and D1 lease',async()=>{
 const {env,sqlite}=setup();let calls=[];const send=upstream(calls);
 assert.equal((await nativeDiscoveryTick(env,NOW,send)).state,'stopped');assert.equal(calls.length,0);
 arm(sqlite);
 const results=await Promise.all([nativeDiscoveryTick(env,NOW,send),nativeDiscoveryTick(env,NOW,send)]);
 assert.equal(results.filter(x=>x.state==='owner_review_draft_queued').length,1);
 assert.equal(calls.length,8);
 assert.equal(sqlite.prepare('SELECT discovery_key FROM hud_auto_discovery_inbox').get().discovery_key,'run-123456');
 assert.equal((await nativeDiscoveryStatus(env)).last_check.result_state,'owner_review_draft_queued');
 assert.equal((await nativeDiscoveryTick(env,NOW+1000,send)).state,'interval_not_due');
 assert.equal(calls.length,8);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM hud_cloud_workforce_jobs').get().n,0);
});
test('credential scope escalation and redirect fail closed without repository access',async()=>{
 const {env,sqlite}=setup();arm(sqlite);
 const calls=[];const result=await nativeDiscoveryTick(env,NOW,upstream(calls,{permissions:{contents:'write',issues:'read',pull_requests:'read',actions:'read'}}));
 assert.equal(result.state,'github_read_unavailable');assert.equal(calls.length,1);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM hud_auto_discovery_inbox').get().n,0);
 await assert.rejects(()=>mintGithubReadToken(env,NOW,async()=>new Response(null,{status:302,headers:{Location:'https://evil.test/'}})));
});
test('private readback never exposes app key or installation token; absent setup makes no calls',async()=>{
 const {env}=setup();
 const route='https://hud.test/api/hud/workforce/native-discovery';
 assert.equal((await handle(new Request(route),env)).status,401);
 const reply=await handle(new Request(route,{headers:{Authorization:'Bearer '+R}}),env);
 assert.equal(reply.status,200);const raw=await reply.text();assert(!raw.includes('PRIVATE KEY'));assert(!raw.includes('mock-installation-token'));
 const result=await nativeDiscoveryTick({...env,ROVOR_NATIVE_DISCOVERY_ENABLED:'false'},NOW,async()=>{throw Error('no request');});
 assert.equal(result.state,'not_configured');
});

test('full shared draft budget still records independent read-only proof without intake or inference',async()=>{
 const {env,sqlite}=setup();arm(sqlite);
 const insert=sqlite.prepare("INSERT INTO hud_auto_discovery_inbox(id,discovery_key,day_id,created_at,content,priority,state) VALUES(?,?,?,?,?,?,'pending_review')");
 for(let i=0;i<6;i++)insert.run(crypto.randomUUID(),'issue-'+(i+1),Math.floor(NOW/86400000),NOW,'test draft',50);
 const calls=[];const result=await nativeDiscoveryTick(env,NOW,upstream(calls));
 assert.equal(result.state,'daily_draft_budget_reached');assert.equal(calls.length,8);
 const status=await nativeDiscoveryStatus(env);assert.equal(status.standing_ready,true);
 assert.equal(status.last_check.result_state,'daily_draft_budget_reached');assert.equal(status.last_check.discovery_key,null);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM hud_auto_discovery_inbox').get().n,6);
 assert.equal(sqlite.prepare('SELECT count(*) n FROM hud_cloud_workforce_jobs').get().n,0);
 assert.equal((await nativeDiscoveryTick(env,NOW+1000,upstream(calls))).state,'interval_not_due');assert.equal(calls.length,8);
 sqlite.exec('UPDATE hud_cloud_workforce_control SET enabled=0');
 assert.equal((await nativeDiscoveryStatus(env)).standing_ready,false);
 assert.equal((await nativeDiscoveryTick(env,NOW+3600000,upstream(calls))).state,'stopped');assert.equal(calls.length,8);
});


test('native read-only catch-up records bounded GitHub metadata, not source or messages',async()=>{
 const {env,sqlite}=setup();arm(sqlite);const calls=[];
 assert.equal((await nativeDiscoveryTick(env,NOW,upstream(calls))).state,'owner_review_draft_queued');
 const out=await repoCatchupStatus(env);
 assert.equal(out.state,'ready');assert.equal(out.observed_at,NOW);
 assert.equal(out.snapshot.head_sha,'a'.repeat(40));
 assert.deepEqual(out.snapshot.recent_commit_shas,['a'.repeat(40),'b'.repeat(40)]);
 assert.deepEqual(out.snapshot.changed_paths,['architecture/ROVOR-AUTONOMOUS-DISCOVERY.md','integrations/hud-cloud/worker.mjs','design/pipeline.md']);
 assert.equal(out.snapshot.scanned_commit_count,2);
 assert.equal(out.snapshot.commit_file_counts.length,2);
 assert.equal(out.snapshot_freshness,'fresh');
 assert.deepEqual(out.snapshot.failed_run_ids,[123456]);
 assert.equal(out.model_called,false);assert.equal(out.repository_written,false);
 assert(!JSON.stringify(out).includes('mock-installation-token'));
 const url='https://hud.test/api/hud/workforce/repo-catchup';
 assert.equal((await handle(new Request(url),env)).status,401);
 const reader=await handle(new Request(url,{headers:{Authorization:'Bearer '+R}}),env);
 assert.equal(reader.status,200);
 assert.equal((await reader.json()).snapshot.head_sha,'a'.repeat(40));
 assert(calls.every(x=>x.method==='GET'||x.url.endsWith('/access_tokens')));
});
test('catch-up GitHub failure does not block evidence discovery or erase last successful snapshot',async()=>{
 const {env,sqlite}=setup();arm(sqlite);
 await nativeDiscoveryTick(env,NOW,upstream([]));
 const send=async(url,init)=>{
  if(url.includes('/commits?'))return new Response('denied',{status:403});
  const response=await upstream([])(url,init);
  if(url.endsWith('/access_tokens')){
   const token=await response.json();
   return Response.json({...token,expires_at:new Date(NOW+7200000).toISOString()},{status:201});
  }
  return response;
 };
 const later=await nativeDiscoveryTick(env,NOW+3600001,send);
 assert(['no_new_evidence_backed_work','owner_review_draft_queued'].includes(later.state));
 const out=await repoCatchupStatus(env);
 assert.equal(out.state,'read_unavailable');assert.equal(out.observed_at,NOW);
 assert.equal(out.snapshot.head_sha,'a'.repeat(40));assert.equal(out.checked_at,NOW+3600001);
 assert.equal(out.snapshot_freshness,'fresh');
 assert.equal((await repoCatchupStatus(env,NOW+3*3600000)).snapshot_freshness,'stale');
});
