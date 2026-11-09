import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkGroqCatalogueKey} from '../integrations/hud-cloud/verify-groq-key.mjs';
const KEY='dummy-private-token-for-tests';
test('runner only GETs pinned Groq catalogue with key in Authorization, no prompts',async()=>{
  let calls=0;
  const result=await checkGroqCatalogueKey(KEY,async(url,options)=>{
    calls++;
    assert.equal(url,'https://api.groq.com/openai/v1/models');
    assert.equal(options.method,'GET');
    assert.equal(options.headers.Authorization,'Bearer '+KEY);
    assert(!('body' in options));
    return Response.json({data:[{id:'openai/gpt-oss-20b'}]});
  });
  assert.equal(calls,1);
  assert.deepEqual(result,{connection:'catalog_received',http_status:200,model_listed:true});
  assert(!JSON.stringify(result).includes(KEY),'no key material in readback');
});
test('runner gives clear non-sensitive auth, HTTP, timeout and malformed categories',async()=>{
  assert.equal((await checkGroqCatalogueKey(KEY,async()=>Response.json({error:'secret'},{status:401}))).connection,'auth_rejected');
  assert.equal((await checkGroqCatalogueKey(KEY,async()=>Response.json({error:'secret'},{status:429}))).connection,'rate_limited');
  assert.deepEqual(await checkGroqCatalogueKey('',async()=>{throw Error('must not call');}),
    {connection:'no_key_configured',http_status:null,model_listed:null});
  assert.equal((await checkGroqCatalogueKey(KEY,async()=>{throw new Error('TOKEN MUST NOT APPEAR')})).connection,'network_error');
  assert.equal((await checkGroqCatalogueKey(KEY,async()=>new Response('bad json',{status:200}))).connection,'catalog_invalid');
});
