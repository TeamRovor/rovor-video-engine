import {test} from 'node:test';
import assert from 'node:assert/strict';
import {normalizeProviderCatalog} from '../integrations/ghost-cloud/site-operations.mjs';

// These are read-only catalog metadata tests. A candidate is never an
// inference permit, proof of free billing, or a quota/canary receipt.
test('Hugging Face requires an explicit upstream suffix for pin candidates',()=>{
 const models=normalizeProviderCatalog('huggingface',{data:[
  {id:'Qwen/Qwen3-32B'},
  {id:'Qwen/Qwen3-32B:novita'},
  {id:'Qwen/Qwen3-32B:latest'},
  {id:'Qwen/Qwen3-32B:auto'}
 ]});
 assert.deepEqual(models.map(m=>[m.id,m.pinned_model_candidate]),[
  ['Qwen/Qwen3-32B',false],
  ['Qwen/Qwen3-32B:novita',true],
  ['Qwen/Qwen3-32B:latest',false],
  ['Qwen/Qwen3-32B:auto',false]
 ]);
 assert(models.every(m=>m.catalog_zero_price===null));
 assert(models.every(m=>!Object.hasOwn(m,'online_verified')&&
  !Object.hasOwn(m,'billing_verified')&&
  !Object.hasOwn(m,'quota_remaining')));
});

test('Gemini model prefix and Cloudflare @cf names preserve exact pinned candidates',()=>{
 const gemini=normalizeProviderCatalog('gemini',{models:[
  {name:'models/gemini-2.5-flash-lite'},
  {name:'models/gemini-flash-latest'}
 ]});
 assert.deepEqual(gemini.map(m=>[m.id,m.pinned_model_candidate]),[
  ['gemini-2.5-flash-lite',true],
  ['gemini-flash-latest',false]
 ]);
 const cf=normalizeProviderCatalog('cloudflare-ai',{result:[
  {id:'private-uuid',name:'@cf/meta/llama-3.2-3b-instruct'}
 ]});
 assert.deepEqual(cf.map(m=>[m.id,m.pinned_model_candidate]),[
  ['@cf/meta/llama-3.2-3b-instruct',true]
 ]);
});

test('OpenRouter catalog must have explicit literal zero prices, not coerced blanks',()=>{
 const entries=[
  {id:'vendor/free:free',pricing:{prompt:'0',completion:'0.000'}},
  {id:'vendor/numeric:free',pricing:{prompt:0,completion:0}},
  {id:'vendor/blank:free',pricing:{prompt:'',completion:'0'}},
  {id:'vendor/space:free',pricing:{prompt:' ',completion:'0'}},
  {id:'vendor/hex:free',pricing:{prompt:'0x0',completion:'0'}},
  {id:'vendor/missing:free',pricing:{prompt:'0'}},
  {id:'vendor/paid:free',pricing:{prompt:'0.0001',completion:'0'}},
  {id:'vendor/no-suffix',pricing:{prompt:'0',completion:'0'}}
 ];
 const models=normalizeProviderCatalog('openrouter',{data:entries});
 assert.deepEqual(models.map(m=>m.id),['vendor/free:free','vendor/numeric:free']);
 assert(models.every(m=>m.catalog_zero_price===true&&m.pinned_model_candidate===true));
});

test('catalog normalization is bounded and rejects ambiguous metadata',()=>{
 const oversized='vendor/'+ 'x'.repeat(200);
 const results=normalizeProviderCatalog('groq',{data:[
  {id:oversized},
  {id:'model-latest'},
  ...Array.from({length:40},(_,i)=>({id:'model-'+i}))
 ]});
 assert.equal(results.length,20);
 assert(!results.some(m=>m.id===oversized));
 assert.equal(results[0].pinned_model_candidate,false);
 assert.equal(normalizeProviderCatalog('groq',{data:[]}).length,0);
 assert.equal(normalizeProviderCatalog('groq',{data:'not-an-array'}),null);
 assert.throws(()=>normalizeProviderCatalog('unrecognized',{}),/unknown_provider/);
});
