import test from 'node:test';
import assert from 'node:assert/strict';
import {verifyGemini} from '../tools/verify_hud_gemini_activation.mjs';
import {selectGeminiRoute} from '../tools/activate_hud_gemini_route.mjs';

const route='gemini/gemini-3.1-flash-lite',reader='r'.repeat(48);
const json=data=>new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});

test('exact direct Google route only, Cloudflare Gemma and combos excluded',()=>{
  assert.equal(selectGeminiRoute(['@cf/google/gemma-3-12b-it','rovor-fast-free-v1']),null);
  assert.equal(selectGeminiRoute([route,'google/gemini-2.5-flash-lite']),route);
  assert.throws(()=>selectGeminiRoute([route,'google/gemini-3.1-flash-lite']),/ambiguous/);
});

test('one bounded canary proves a real HUD completion, never double submits',async()=>{
  let submits=0,polls=0;
  const send=async(url,init)=>{
    assert.match(init.headers.Authorization,/^Bearer r+$/);
    if(url.endsWith('/api/hud/chat/models'))return json({source:'omniroute_outbound_bridge',online:true,models:[route]});
    if(url.endsWith('/api/hud/chat/submit')){
      submits++;
      assert.equal(init.headers.Origin,'https://rovor-hud-telemetry.rovordigital.workers.dev');
      assert.equal(JSON.parse(init.body).model,route);
      return json({status:202,job_id:'00000000-0000-0000-0000-000000000001'});
    }
    if(url.includes('/api/hud/chat/status/')){
      polls++;
      return json({state:'complete',requested_model:route,output:'Connected.'});
    }
    throw Error('unexpected endpoint');
  };
  const result=await verifyGemini({reader,route,send,pause:async()=>{},log:()=>{}});
  assert.deepEqual(result,{route,available:true,inference_verified:true});
  assert.equal(submits,1);assert.equal(polls,1);
});

test('missing/incorrect Gemini route fails closed without inference',async()=>{
  let submits=0;
  const send=async()=>{submits++;return json({source:'omniroute_outbound_bridge',online:false,models:[]});};
  await assert.rejects(()=>verifyGemini({reader,route:'@cf/google/gemma-3-12b-it',send}),/unverified_direct_gemini_route/);
  assert.equal(submits,0);
  await assert.rejects(()=>verifyGemini({reader,route,send,pause:async()=>{},log:()=>{}}),/gemini_not_advertised/);
  assert.equal(submits,10);
});
