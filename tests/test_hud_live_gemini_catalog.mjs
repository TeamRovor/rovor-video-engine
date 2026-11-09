import test from 'node:test';
import assert from 'node:assert/strict';
import {readLiveGemini} from '../integrations/hud-cloud/verify-live-gemini-catalog.mjs';
const token='r'.repeat(48);
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
function response(body,status=200){return new Response(JSON.stringify(body),{status});}
function fake({online=true,anonymous=401,usageValid=true}={}){
  const visited=[];
  const send=async(url,opts)=>{
    visited.push({url,opts});
    assert(url.startsWith(ORIGIN+'/api/hud/gemini/'));
    assert.equal(opts.redirect,'manual');
    assert.equal(opts.method,'GET');
    assert.equal(opts.cache,'no-store');
    if(!opts.headers.Authorization)return new Response(null,{status:anonymous});
    assert.equal(opts.headers.Authorization,'Bearer '+token);
    if(url.endsWith('/models')){
      return response({source:'google_gemini_cloud_direct',provider:'google',mac_required:false,
        online,models:online?['gemini-auto-free','gemini-3.1-flash-lite']:[],
        directly_listed_models:online?['gemini-3.1-flash-lite']:[],
        discovery_reason:online?'catalog_listed_unverified_for_inference':'free_project_or_key_unconfigured'});
    }
    if(url.endsWith('/usage'))return response(usageValid?
      {source:'cloud_gemini_direct',models:[{model:'gemini-3.1-flash-lite',completed:2}],completed:2}:
      {source:'other_source',completed:0});
    throw Error('unexpected_url');
  };
  return {send,visited};
}
test('live private catalog reports approved key models and historical receipts without inference',async()=>{
  const f=fake();
  const result=await readLiveGemini({token,send:f.send});
  assert.equal(result.private_auth_verified,true);
  assert.equal(result.model_catalog_state,'key_listed_free_text_models');
  assert.equal(result.eligible_text_model_count,1);
  assert.equal(result.completed_today,2);
  assert.equal(result.inference_proven,false);
  assert.equal(result.mac_required,false);
  assert.equal(f.visited.length,3);
  assert(f.visited.every(x=>x.opts.method==='GET'));
});
test('missing cloud Google key is honestly blocked, not a fake connected result',async()=>{
  const f=fake({online:false});
  const result=await readLiveGemini({token,send:f.send});
  assert.equal(result.model_catalog_state,'not_ready');
  assert.equal(result.eligible_text_model_count,0);
  assert.equal(result.completed_today,null);
  assert.equal(f.visited.length,2);
});
test('anonymous exposure fails before reading private state',async()=>{
  const f=fake({anonymous:200});
  await assert.rejects(()=>readLiveGemini({token,send:f.send}),/gemini_catalog_not_private/);
  assert.equal(f.visited.length,1);
});
test('invalid D1 usage is not silently treated as a verified receipt',async()=>{
  const f=fake({usageValid:false});
  await assert.rejects(()=>readLiveGemini({token,send:f.send}),/gemini_model_usage_unavailable/);
});
test('incorrect credentials are rejected before network access',async()=>{
  let calls=0;
  await assert.rejects(()=>readLiveGemini({token:'',send:async()=>{calls++}}),/private_reader_secret_missing/);
  assert.equal(calls,0);
});