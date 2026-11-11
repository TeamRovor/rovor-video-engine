import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {buildHudSecretPayload} from '../integrations/hud-cloud/private-worker-secret-payload.mjs';
const now=Date.now(),origin='https://hud.test',R='r'.repeat(40),W='w'.repeat(40),O='o'.repeat(40),SHA='a'.repeat(40),DIGEST='d'.repeat(64);
function setup(){
 const sql=new DatabaseSync(':memory:');sql.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(q){const stmt=sql.prepare(q);let args=[];const handle={bind(...a){args=a;return handle;},
  async first(){return stmt.get(...args)||null;},async all(){return {results:stmt.all(...args)};},
  async run(){return {meta:{changes:Number(stmt.run(...args).changes)}};}};return handle;},
  async batch(stmts){sql.exec('BEGIN');try{const result=[];for(const s of stmts)result.push(await s.run());sql.exec('COMMIT');return result;}catch(e){sql.exec('ROLLBACK');throw e;}}};
 const env={DB,HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,HUD_OWNER_TOKEN:O,
  ASSETS:{fetch:async request=>{
   assert.equal(new URL(request.url).pathname,'/rovor-repo-source.json');
   return Response.json({source:'reviewed_github_checkout',commit:SHA,mac_required:false,files:{'coordination/TASK-INTAKE.md':{text:'Reviewed source.',truncated:false}}});
  }}};
 const req=(path,{method='GET',cookie='',body=null,requestOrigin=origin,token=null}={})=>new Request(origin+path,{
  method,headers:{Origin:requestOrigin,...(cookie?{Cookie:cookie}:{}),...(token?{Authorization:'Bearer '+token}:{}),
    ...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})});
 return {sql,env,req};
}
function passed(s){
 s.sql.prepare(`INSERT INTO hud_cloud_workforce_jobs(id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,actual_model,output,output_sha256,human_review,reviewed_at)
 VALUES('gc-owner-pilot','pilot','Gus','research','Pilot','public prompt',?,'v2',?,'needs_review','gemini-3.5-flash-lite','verified draft',?,'passed',?)`).run(SHA,now,DIGEST,now);
}
async function login(s,token=O){
 const r=await handle(s.req('/login',{method:'POST',body:{token}}),s.env,now);
 assert.equal(r.status,204);const parts=r.headers.getSetCookie();
 return {parts,cookie:parts.filter(x=>!x.includes('Max-Age=0')).map(x=>x.split(';')[0]).join('; ')};
}
test('owner login uses signed expiring HttpOnly cookie; viewer session has no owner authority',async()=>{
 const s=setup(),owner=await login(s);
 assert.equal(owner.parts.length,2);assert(!owner.cookie.includes(O));assert(!owner.cookie.includes(W));
 assert.match(owner.parts[1],/Path=\/api\/hud\/; Max-Age=86400; Secure; HttpOnly; SameSite=Strict/);
 assert.equal((await (await handle(s.req('/api/hud/owner/session',{cookie:owner.cookie}),s.env,now)).json()).owner_authenticated,true);
 assert.equal((await (await handle(s.req('/api/hud/owner/session',{cookie:owner.cookie}),s.env,now+86400001)).json()).owner_authenticated,false);
 const tampered=owner.cookie.slice(0,-1)+(owner.cookie.endsWith('a')?'b':'a');
 assert.equal((await (await handle(s.req('/api/hud/owner/session',{cookie:tampered}),s.env,now)).json()).owner_authenticated,false);
 const viewer=await login(s,R);assert(viewer.parts.some(x=>x.includes('Max-Age=0')));
 assert.equal((await (await handle(s.req('/api/hud/owner/session',{cookie:viewer.cookie}),s.env,now)).json()).owner_authenticated,false);
});
test('direct HUD start uses deployed commit, requires exact explicit consent and prior PASS, then STOP',async()=>{
 const s=setup(),owner=await login(s);
 const act=(body,extra={})=>handle(s.req('/api/hud/owner/workforce',{method:'POST',cookie:owner.cookie,body,...extra}),s.env,now);
 const start={action:'start',confirm:'authorize_7_day_discovery'};
 assert.equal((await act(start)).status,409);
 passed(s);
 assert.equal((await act({action:'start'})).status,400);
 assert.equal((await act({...start,source_commit:'b'.repeat(40)})).status,400);
 assert.equal((await act(start,{requestOrigin:'https://evil.test'})).status,403);
 const r=await act(start);assert.equal(r.status,200);assert.equal((await r.json()).recurring_authorized,true);
 const series=s.sql.prepare('SELECT * FROM hud_cloud_workforce_series').get();assert.equal(series.source_commit,SHA);assert.equal(series.active,1);
 const stopped=await act({action:'stop'});assert.equal(stopped.status,200);
 assert.equal(s.sql.prepare('SELECT enabled FROM hud_cloud_workforce_control').get().enabled,0);
 assert.equal(s.sql.prepare('SELECT active FROM hud_cloud_workforce_series').get().active,0);
});
test('reader/writer credentials cannot promote themselves to owner and configured owner review is separate',async()=>{
 const s=setup(),viewer=await login(s,R);passed(s);
 const body={action:'start',confirm:'authorize_7_day_discovery'};
 assert.equal((await handle(s.req('/api/hud/owner/workforce',{method:'POST',cookie:viewer.cookie,body}),s.env,now)).status,403);
 assert.equal((await handle(s.req('/api/hud/owner/workforce',{method:'POST',token:W,body}),s.env,now)).status,401);
 const review={job_id:'gc-owner-pilot',verdict:'passed',output_sha256:DIGEST};
 assert.equal((await handle(s.req('/api/hud/workforce/review',{method:'POST',cookie:viewer.cookie,body:review}),s.env,now)).status,403);
 assert.equal((await handle(s.req('/api/hud/owner/github-patch',{method:'POST',cookie:viewer.cookie,body:{confirm:'authorize_draft_pr',job_id:'gc-owner-pilot',output_sha256:DIGEST}}),s.env,now)).status,403);
 assert.throws(()=>buildHudSecretPayload({ROVOR_HUD_READER_TOKEN:R,ROVOR_HUD_WRITER_TOKEN:W,ROVOR_HUD_OWNER_TOKEN:R}));
 assert.equal(buildHudSecretPayload({ROVOR_HUD_READER_TOKEN:R,ROVOR_HUD_WRITER_TOKEN:W,ROVOR_HUD_OWNER_TOKEN:O}).HUD_OWNER_TOKEN,O);
});

test('an absent or invalid owner key never grants PASS/FAIL to the private viewer',async()=>{
 const s=setup();
 passed(s);
 // Simulate a real completed, undecided draft; authorization must be checked
 // before the immutable owner review helper sees this request.
 s.sql.prepare("UPDATE hud_cloud_workforce_jobs SET human_review='not_recorded',reviewed_at=NULL WHERE id='gc-owner-pilot'").run();
 const review={job_id:'gc-owner-pilot',verdict:'passed',output_sha256:DIGEST};
 const decision=(cookie='',token=null)=>handle(s.req('/api/hud/workforce/review',{
  method:'POST',cookie,token,body:review}),s.env,now);
 const state=()=>s.sql.prepare("SELECT human_review,reviewed_at FROM hud_cloud_workforce_jobs WHERE id='gc-owner-pilot'").get();
 delete s.env.HUD_OWNER_TOKEN;
 const viewer=await login(s,R);
 assert.equal((await (await handle(s.req('/api/hud/owner/session',{cookie:viewer.cookie}),s.env,now)).json()).configured,false);
 assert.equal((await decision(viewer.cookie)).status,403,'viewer session is not an owner session');
 assert.equal((await decision('',R)).status,403,'reader bearer is not an owner key');
 assert.deepEqual(state(),{human_review:'not_recorded',reviewed_at:null});
 s.env.HUD_OWNER_TOKEN=R; // A key mistakenly reused from viewer must also fail closed.
 assert.equal((await decision(viewer.cookie)).status,403);
 assert.deepEqual(state(),{human_review:'not_recorded',reviewed_at:null});
 s.env.HUD_OWNER_TOKEN=O;
 assert.equal((await decision(viewer.cookie)).status,403,'restoring owner key cannot upgrade an old viewer session');
 const owner=await login(s,O);
 assert.equal((await decision(owner.cookie)).status,200,'genuine signed owner session can still review');
 assert.deepEqual(state(),{human_review:'passed',reviewed_at:now});
 assert.equal((await decision(owner.cookie)).status,409,'owner decisions remain first-write-only');
});
