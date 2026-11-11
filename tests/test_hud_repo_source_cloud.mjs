import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {handle} from '../integrations/hud-cloud/worker.mjs';
import {REPO_SOURCE_FILES,createRepoSnapshot,selectRepoSnapshot,getRepoSource} from '../integrations/hud-cloud/repo-source.mjs';
import {buildAtCheckout} from '../integrations/hud-cloud/build-repo-snapshot.mjs';
const SHA='a'.repeat(40),READER='r'.repeat(40),WRITER='w'.repeat(40);
const DOC='coordination/TASK-INTAKE.md';
const sample=()=>createRepoSnapshot(SHA,p=>'EXCERPT OF '+p+'\n'.repeat(120));
const env=()=>({HUD_READER_TOKEN:READER,HUD_WRITER_TOKEN:WRITER,DB:{},
  ASSETS:{fetch:async req=>{
    assert.equal(new URL(req.url).pathname,'/rovor-repo-source.json');
    assert.equal(req.redirect,'manual');
    return Response.json(sample());
  }}});
const query=(path=DOC,auth=true)=>new Request('https://hud.test/api/hud/github/source?path='+encodeURIComponent(path),
  {headers:auth?{Cookie:'rovor_hud_reader='+READER}:{}});
test('Snapshot builder only accepts verified exact git checkout and fixed source paths',()=>{
  assert(REPO_SOURCE_FILES.length>=4);
  assert.equal(new Set(REPO_SOURCE_FILES).size,REPO_SOURCE_FILES.length);
  const calls=[];
  const snap=buildAtCheckout(SHA,()=>SHA, p=>{calls.push(p);return 'verified excerpt from '+p});
  assert.deepEqual(calls,REPO_SOURCE_FILES);
  assert.equal(snap.commit,SHA);
  assert.equal(snap.mac_required,false);
  assert.throws(()=>buildAtCheckout(SHA,()=>('b'.repeat(40)),()=>''),/snapshot_not_trusted_checkout/);
  assert.throws(()=>buildAtCheckout('definitely-not-a-sha',()=>SHA,()=>''),/snapshot_not_trusted_checkout/);
  assert.throws(()=>createRepoSnapshot(SHA,()=>''),/repo_source_invalid/);
});
test('Source is read-only, bounded and carries exact reviewed commit, not a live Github claim',()=>{
  const snap=sample();
  const result=selectRepoSnapshot(snap,DOC);
  assert.equal(result.status,200);
  assert.equal(result.body.source,'reviewed_github_checkout');
  assert.equal(result.body.fetched_live,false);
  assert.equal(result.body.can_write,false);
  assert.equal(result.body.mac_required,false);
  assert.equal(result.body.commit,SHA);
  assert.equal(result.body.path,DOC);
  assert(result.body.text.length<=1800);
  const big=createRepoSnapshot(SHA,()=>('x'.repeat(2400)));
  assert.equal(big.files[DOC].text.length,1800);
  assert.equal(big.files[DOC].truncated,true);
  assert.equal(selectRepoSnapshot(big,'../../.env').status,400);
  assert.equal(selectRepoSnapshot(big,'https://github.com/foo').status,400);
  assert.equal(selectRepoSnapshot(big,'').status,400);
  assert.equal(selectRepoSnapshot({...big,commit:'not-pinned'},DOC).status,503);
});
test('Private HTTP endpoint uses existing reader identity; an anonymous caller sees no source',async()=>{
  const e=env();
  const anon=await handle(query(DOC,false),e);
  assert.equal(anon.status,401);
  const ok=await handle(query(),e);
  assert.equal(ok.status,200);
  const data=await ok.json();
  assert.equal(data.commit,SHA);
  assert.equal(data.can_write,false);
  assert.match(data.text,/EXCERPT OF coordination\/TASK-INTAKE.md/);
  assert.equal((await handle(query('../../secret'),e)).status,400);
  assert.equal((await handle(query(DOC),{...e,ASSETS:null})).status,503);
});
test('Missing or malformed reviewed bundle fails closed and cannot become arbitrary GitHub fetch',async()=>{
  for(const fetcher of [
    async()=>new Response('not found',{status:404}),
    async()=>new Response('{invalid',{status:200}),
    async()=>Response.json({...sample(),commit:null}),
    async()=>new Response('x'.repeat(24001),{status:200})
  ]){
    const result=await getRepoSource({ASSETS:{fetch:fetcher}},query(),DOC);
    assert.equal(result.status,503);
  }
  assert.equal((await getRepoSource({},query(),'../.git/config')).status,400);
});
test('Cloud UI requires explicit selected file and never exposes GitHub credentials to models',()=>{
 const src=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');
 assert.match(src,/\/api\/hud\/github\/source\?path=/);
 assert.match(src,/source\.can_write!==false/);
 assert.match(src,/source\.mac_required!==false/);
 assert.match(src,/source\.commit/);
 assert.match(src,/UNTRUSTED READ-ONLY GITHUB REFERENCE/);
 assert.match(src,/platform!=='omniroute'/);
 assert.match(src,/if\(attachedSource && platform!=='omniroute'\)/);
 assert.doesNotMatch(src,/fetch\(['"]https?:\/\//);
});
