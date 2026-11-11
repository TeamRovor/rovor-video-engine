import {test} from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {queueGithubPatch,githubPatchTick,githubPatchStatus,parsePatch,replaceExact} from '../integrations/hud-cloud/github-patch-gateway.mjs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
const NOW=Date.now(),R='r'.repeat(40),W='w'.repeat(40);
const base='a'.repeat(40),tree='b'.repeat(40),blob='c'.repeat(40),newTree='d'.repeat(40),commit='e'.repeat(40);
const pem=generateKeyPairSync('rsa',{modulusLength:2048}).privateKey.export({type:'pkcs8',format:'pem'});
const path='dashboard/command-center/native-v8-9/hud-mobile.css',original='.x { color: blue; }';
const proposal={version:1,base_commit:base,title:'Improve mobile contrast',summary:'Use brighter contrast.',change:{path,blob_sha:blob,before:'color: blue',after:'color: white'}};
const digest=s=>createHash('sha256').update(s).digest('hex');
function setup(p=proposal){
 const sqlite=new DatabaseSync(':memory:');sqlite.exec(readFileSync(new URL('../integrations/hud-cloud/schema.sql',import.meta.url),'utf8'));
 const DB={prepare(sql){return{bind(...a){return{
 first:async()=>sqlite.prepare(sql).get(...a)??null,all:async()=>({results:sqlite.prepare(sql).all(...a)}),
 run:async()=>({meta:{changes:sqlite.prepare(sql).run(...a).changes}})
 }}}}};
 const env={DB,HUD_READER_TOKEN:R,HUD_WRITER_TOKEN:W,ROVOR_GITHUB_APP_ID:'123',
 ROVOR_GITHUB_INSTALLATION_ID:'456',ROVOR_GITHUB_APP_PRIVATE_KEY:pem,
 ROVOR_GITHUB_PATCH_ENABLED:'true',ROVOR_GITHUB_PATCH_PATHS:JSON.stringify([path])};
 const output=JSON.stringify(p),hash=digest(output),job='gc-patch-example';
 sqlite.prepare(`INSERT INTO hud_cloud_workforce_jobs
 (id,task_id,employee,kind,title,prompt,source_commit,revision,created_at,state,actual_model,output,output_sha256,human_review,reviewed_at)
 VALUES(?,?,?,?,?,?,?,?,?,'needs_review','gemini-3.5-flash-lite',?,?,'passed',?)`)
 .run(job,'patch','Mike','code_review','Fix UI','reviewed public packet',base,'v2',NOW,output,hash,NOW);
 return {env,sqlite,body:{job_id:job,output_sha256:hash}};
}
function enable(s){s.sqlite.exec('UPDATE hud_cloud_workforce_control SET enabled=1');}
function upstream(s,calls,{stale=false,stopOnBranch=false,failPr=false}={}){
 let branch=null;
 return async(url,init)=>{
 calls.push({url,method:init.method,body:init.body?JSON.parse(init.body):null});
 assert.equal(init.redirect,'manual');
 if(url.endsWith('/access_tokens')){
  assert.deepEqual(JSON.parse(init.body).permissions,{contents:'write',pull_requests:'write'});
  return Response.json({token:'mock-write-token-123456789',expires_at:new Date(NOW+3600000).toISOString(),permissions:{contents:'write',pull_requests:'write',metadata:'read'}},{status:201});
 }
 assert.equal(init.headers.Authorization,'Bearer mock-write-token-123456789');
 assert(url.startsWith('https://api.github.com/repos/TeamRovor/rovor-video-engine/'));
 const route=url.split('/rovor-video-engine')[1];
 if(route==='/git/ref/heads/main')return Response.json({object:{sha:stale?'f'.repeat(40):base}});
 if(route==='/git/commits/'+base)return Response.json({sha:base,tree:{sha:tree}});
 if(route==='/git/trees/'+tree+'?recursive=1')return Response.json({sha:tree,truncated:false,tree:[{path,mode:'100644',type:'blob',sha:blob}]});
 if(route==='/git/blobs/'+blob)return Response.json({sha:blob,encoding:'base64',size:Buffer.byteLength(original),content:Buffer.from(original).toString('base64')});
 if(route==='/git/trees'){assert.deepEqual(JSON.parse(init.body),{base_tree:tree,tree:[{path,mode:'100644',type:'blob',content:'.x { color: white; }'}]});return Response.json({sha:newTree},{status:201});}
 if(route==='/git/commits'){assert.deepEqual(JSON.parse(init.body).parents,[base]);return Response.json({sha:commit,tree:{sha:newTree},parents:[{sha:base}]},{status:201});}
 if(route==='/git/refs'){const doc=JSON.parse(init.body);branch=doc.ref.slice('refs/heads/'.length);if(stopOnBranch)s.sqlite.exec('UPDATE hud_cloud_workforce_control SET enabled=0');return Response.json({ref:doc.ref,object:{sha:commit}},{status:201});}
 if(route==='/pulls'){const doc=JSON.parse(init.body);assert.equal(doc.draft,true);assert.equal(doc.base,'main');assert.equal(doc.head,branch);if(failPr)throw Error('transport interrupted');return Response.json({number:99,draft:true,head:{sha:commit,ref:branch},base:{ref:'main',repo:{full_name:'TeamRovor/rovor-video-engine'}}},{status:201});}
 throw Error('unexpected route');
 };
}
test('owner-reviewed exact output queues once; native tick opens one draft PR and records writes',async()=>{
 const s=setup(),calls=[];
 assert.equal((await queueGithubPatch(s.env,s.body,NOW)).status,409);
 enable(s);assert.equal((await queueGithubPatch(s.env,s.body,NOW)).status,202);
 assert.equal((await queueGithubPatch(s.env,s.body,NOW)).status,409);
 const out=await githubPatchTick(s.env,NOW,upstream(s,calls));
 assert.equal(out.state,'opened');assert.equal(out.pr_number,99);
 assert.equal(s.sqlite.prepare('SELECT COUNT(*) n FROM hud_github_patch_events').get().n,4);
 assert.equal((await githubPatchStatus(s.env)).items[0].pr_number,99);
 const n=calls.length;assert.equal((await githubPatchTick(s.env,NOW+1,upstream(s,calls))).state,'idle_or_safety_limited');assert.equal(calls.length,n);
 assert(!calls.some(x=>/merge|deploy/.test(x.url)));
});
test('deny nonreviewed output, wrong digest, protected paths and nonunique anchor',async()=>{
 const s=setup();enable(s);
 assert.equal((await queueGithubPatch(s.env,{...s.body,output_sha256:'f'.repeat(64)},NOW)).status,409);
 s.sqlite.exec("UPDATE hud_cloud_workforce_jobs SET human_review='failed'");
 assert.equal((await queueGithubPatch(s.env,s.body,NOW)).status,409);
 const protectedPath='.github/workflows/test.yml';
 assert.throws(()=>parsePatch(JSON.stringify({...proposal,change:{...proposal.change,path:protectedPath}}),base,{...s.env,ROVOR_GITHUB_PATCH_PATHS:JSON.stringify([protectedPath])}));
 assert.throws(()=>replaceExact('blue blue','blue','white'));
 assert.throws(()=>parsePatch(JSON.stringify({...proposal,base_commit:'f'.repeat(40)}),base,s.env));
});
test('stale base causes zero repository writes; STOP after branch prevents PR and never retries',async()=>{
 const s=setup();enable(s);await queueGithubPatch(s.env,s.body,NOW);
 let calls=[];let out=await githubPatchTick(s.env,NOW,upstream(s,calls,{stale:true}));
 assert.equal(out.state,'failed');assert.equal(calls.filter(x=>x.method==='POST').length,1);
 const q=setup();enable(q);await queueGithubPatch(q.env,q.body,NOW);
 calls=[];out=await githubPatchTick(q.env,NOW,upstream(q,calls,{stopOnBranch:true}));
 assert.equal(out.state,'uncertain');assert(!calls.some(x=>x.url.endsWith('/pulls')));
 enable(q);assert.equal((await githubPatchTick(q.env,NOW+86400001,async()=>{throw Error('no replay')})).state,'idle_or_safety_limited');
 assert.equal(q.sqlite.prepare('SELECT COUNT(*) n FROM hud_github_patch_events').get().n,3);
});
test('uncertain PR transport preserves exact branch/commit evidence, blocks replay',async()=>{
 const s=setup();enable(s);await queueGithubPatch(s.env,s.body,NOW);
 const out=await githubPatchTick(s.env,NOW,upstream(s,[],{failPr:true}));
 assert.equal(out.state,'uncertain');assert.equal(out.commit_sha,commit);
 assert.equal(s.sqlite.prepare('SELECT COUNT(*) n FROM hud_github_patch_events').get().n,3);
});
test('reader cannot authorize patch; writer does not supply arbitrary content or credentials',async()=>{
 const s=setup();enable(s);
 const url='https://hud.test/api/hud/workforce/github-patch';
 const req=token=>new Request(url,{method:'POST',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(s.body)});
 assert.equal((await handle(req(R),s.env)).status,401);
 assert.equal((await handle(req(W),s.env)).status,202);
 const status=await handle(new Request(url,{headers:{Authorization:'Bearer '+R}}),s.env);
 assert.equal(status.status,200);const raw=await status.text();assert(!raw.includes('PRIVATE KEY'));assert(!raw.includes(original));
});
