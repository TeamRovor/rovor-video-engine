import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {readGhostStatus} from '../integrations/hud-cloud/ghost-status-readback.mjs';
import {buildHudSecretPayload} from '../integrations/hud-cloud/private-worker-secret-payload.mjs';

const NOW=1794910000000;
const IDS=['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface'];
const SERVICE_URL='https://private-ledger.example.chatgpt.site/api/ghost/service';
const env={
  GHOST_SITE_SERVICE_URL:SERVICE_URL,
  GHOST_SITE_SERVICE_TOKEN:'s'.repeat(64),
  HUD_READER_TOKEN:'r'.repeat(64),
  HUD_WRITER_TOKEN:'w'.repeat(64)
};
const fixture=()=>({
  schema_version:1,execution_source:'cloud_provider',observed_at:NOW,
  enabled:true,
  providers:IDS.map(provider=>({provider,credentials_configured:true,
    admission:provider==='groq'?'eligibility_expired':'disabled_pending_verification',
    online_verified:false,quota:null,recorded_24h:null,
    configured_model:provider==='groq'?'openai/gpt-oss-20b':null,
    secret_internal_field:'SHOULD NEVER LEAK'})),
  attempts:[{id:'receipt-1',job_id:'gc-test-1',provider:'groq',
    started_at:NOW-86400000,finished_at:NOW-86399000,
    status:'needs_review',requested_model:'openai/gpt-oss-20b',
    actual_model:'openai/gpt-oss-20b',tokens_input:170,tokens_output:1637,
    title:'Existing historical workflow receipt',employee:'Walter',
    private_prompt:'SHOULD NEVER LEAK'}],
  raw_provider_api_key:'SHOULD NEVER LEAK',queue_pending:0,native_clock_verified:false
});
const mock=(data,intercept=()=>{})=>async(url,options)=>{
  intercept(url,options);
  return Response.json(data);
};

test('only fixed signed status operation reads source and preserves real historical receipt',async()=>{
  let called=false;
  const result=await readGhostStatus(env,mock(fixture(),(url,opts)=>{
    called=true;
    assert.equal(url,SERVICE_URL);
    assert.equal(opts.method,'POST');
    assert.deepEqual(JSON.parse(opts.body),{operation:'status'});
    assert.equal(opts.headers.Authorization,'Bearer '+env.GHOST_SITE_SERVICE_TOKEN);
    assert.equal(opts.redirect,'manual');
  }),NOW);
  assert(called);
  assert.equal(result.status,200);
  assert.equal(result.body.providers.length,9);
  assert.equal(result.body.providers.filter(p=>p.online_verified).length,0);
  assert.equal(result.body.providers[0].admission,'eligibility_expired');
  assert.equal(result.body.providers[0].quota,null);
  assert.equal(result.body.providers[0].recorded_24h,null);
  assert.equal(result.body.attempts.length,1);
  assert.equal(result.body.attempts[0].tokens_input,170);
  assert.equal(result.body.attempts[0].tokens_output,1637);
  assert.equal(result.body.attempts[0].actual_model,'openai/gpt-oss-20b');
  assert.equal(result.body.attempts[0].started_at,NOW-86400000);
  const output=JSON.stringify(result.body);
  assert(!output.includes('SHOULD NEVER LEAK'));
  assert(!output.includes(env.GHOST_SITE_SERVICE_TOKEN));
});

test('fresh private catalog receipts survive the bridge without creating admission or inference evidence',async()=>{
  const source=fixture();
  for(const p of source.providers) {
    p.last_check={provider:p.provider,status:'catalog_received',
      observed_at:NOW-60000,private_detail:'SHOULD NEVER LEAK'};
    p.recent_inference_verified=false;
  }
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers.filter(p=>p.last_check?.status==='catalog_received').length,9);
  assert(result.body.providers.every(p=>p.last_check.observed_at===NOW-60000));
  assert(result.body.providers.every(p=>p.recent_inference_verified===false));
  assert(result.body.providers.every(p=>p.admission!=='eligible'&&p.online_verified===false));
  assert(!JSON.stringify(result.body).includes('SHOULD NEVER LEAK'));
});

test('catalog receipt cannot authenticate a different provider row',async()=>{
  const source=fixture();
  source.providers[0].last_check={provider:'gemini',status:'catalog_received',observed_at:NOW-1000};
  source.providers[1].last_check={provider:'gemini',status:'catalog_received',observed_at:NOW-1000};
  const result=await readGhostStatus(env,async()=>Response.json(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers[0].last_check,null);
  assert.deepEqual(result.body.providers[1].last_check,{status:'catalog_received',observed_at:NOW-1000});
  assert.equal(result.body.providers.filter(p=>p.last_check?.status==='catalog_received').length,1);
  assert.equal(result.body.providers.filter(p=>p.online_verified).length,0);
});

test('stale or unsupported catalog check records never look authenticated',async()=>{
  const source=fixture();
  source.providers[0].last_check={status:'catalog_received',observed_at:NOW-75*60000-1};
  source.providers[1].last_check={status:'catalog_received',observed_at:NOW+60001};
  source.providers[2].last_check={status:'catalog_failed',observed_at:NOW-1000};
  source.providers[3].last_check={provider:source.providers[3].provider,status:'catalog_received',observed_at:NOW-75*60000};
  source.providers[4].recent_inference_verified=true;
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers[0].last_check,null);
  assert.equal(result.body.providers[1].last_check,null);
  assert.equal(result.body.providers[2].last_check,null);
  assert.deepEqual(result.body.providers[3].last_check,{
    status:'catalog_received',observed_at:NOW-75*60000
  });
  assert.equal(result.body.providers[4].recent_inference_verified,true);
  assert.equal(result.body.providers[4].online_verified,false);
});

test('existing protected deployment secret feeds readback without a second credential',async()=>{
  const payload=buildHudSecretPayload({
    ROVOR_HUD_READER_TOKEN:env.HUD_READER_TOKEN,
    ROVOR_HUD_WRITER_TOKEN:env.HUD_WRITER_TOKEN,
    ROVOR_GHOST_SERVICE_TOKEN:env.GHOST_SITE_SERVICE_TOKEN,
    ROVOR_GHOST_SITE_SERVICE_URL:env.GHOST_SITE_SERVICE_URL
  });
  assert.equal(payload.GHOST_SITE_SERVICE_TOKEN,env.GHOST_SITE_SERVICE_TOKEN);
  assert.equal(payload.GHOST_SITE_SERVICE_URL,env.GHOST_SITE_SERVICE_URL);
  assert.equal(Object.hasOwn(payload,'HUD_GHOST_SERVICE_TOKEN'),false);
  const result=await readGhostStatus(payload,mock(fixture()),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers.length,9);
});

test('readback preserves bounded catalog and inference evidence for nine-provider HUD counters',async()=>{
  const source=fixture();
  source.providers[0].catalog_connection={
    state:'authenticated',observed_at:NOW-60000,private_catalog_key:'SHOULD NEVER LEAK'
  };
  source.providers[0].last_check={
    provider:source.providers[0].provider,
    status:'catalog_received',observed_at:NOW-60000,raw_response:'SHOULD NEVER LEAK'
  };
  source.providers[0].recent_inference_verified=true;
  source.providers[1].catalog_connection={state:'authenticated',observed_at:NOW-80*60000};
  source.providers[1].recent_inference_verified='true';
  source.providers[2].catalog_connection={state:'unexpected-secret',observed_at:NOW+3600000};
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.deepEqual(result.body.providers[0].catalog_connection,{
    state:'authenticated',observed_at:NOW-60000
  });
  assert.deepEqual(result.body.providers[0].last_check,{
    status:'catalog_received',observed_at:NOW-60000
  });
  assert.equal(result.body.providers[0].recent_inference_verified,true);
  // A stale catalog read does not count as a current catalog result in the HUD.
  assert.deepEqual(result.body.providers[1].catalog_connection,{
    state:'authenticated',observed_at:NOW-80*60000
  });
  assert.equal(result.body.providers[1].recent_inference_verified,false);
  assert.deepEqual(result.body.providers[2].catalog_connection,{
    state:'unknown',observed_at:null
  });
  assert.equal(JSON.stringify(result.body).includes('SHOULD NEVER LEAK'),false);
});

test('manual Site redirects fail closed without following credential-bearing responses',async()=>{
  let calls=0;
  const result=await readGhostStatus(env,async(url,options)=>{
    calls++;
    assert.equal(url,SERVICE_URL);
    assert.equal(options.method,'POST');
    assert.equal(options.redirect,'manual');
    assert.equal(options.headers.Authorization,'Bearer '+env.GHOST_SITE_SERVICE_TOKEN);
    return new Response(null,{status:307,headers:{
      Location:'https://untrusted.invalid/collect?token=PRIVATE-MARKER'
    }});
  },NOW);
  assert.equal(calls,1);
  assert.equal(result.status,502);
  assert.equal(result.body.error,'cloud_readback_redirect_denied');
  assert(!JSON.stringify(result).includes('PRIVATE-MARKER'));
  assert(!JSON.stringify(result).includes(env.GHOST_SITE_SERVICE_TOKEN));
});

test('no credential or reused HUD credentials fail closed, without contacting Site',async()=>{
  let calls=0;const fetcher=()=>{calls++;throw Error('unexpected');};
  for(const secret of [null,'short',env.HUD_READER_TOKEN,env.HUD_WRITER_TOKEN]){
    const result=await readGhostStatus({...env,GHOST_SITE_SERVICE_TOKEN:secret},fetcher,NOW);
    assert.equal(result.status,503);
    assert.equal(result.body.error,'cloud_readback_not_configured');
  }
  assert.equal(calls,0);
});

test('malformed or stale private payloads and secret-rich upstream errors fail closed',async()=>{
  const cases=[
    {...fixture(),execution_source:'made_up'},
    {...fixture(),observed_at:NOW-999999},
    {...fixture(),providers:fixture().providers.slice(1)},
    {...fixture(),providers:[...fixture().providers.slice(0,8),fixture().providers[0]]},
    {...fixture(),attempts:Array.from({length:101},()=>fixture().attempts[0])}
  ];
  for(const payload of cases){
    const result=await readGhostStatus(env,mock(payload),NOW);
    assert.equal(result.status,502);
    assert.deepEqual(Object.keys(result.body),['error']);
  }
  const upstreamError=await readGhostStatus(env,async()=>new Response('private session denied; KEY-LEAK',{status:403}),NOW);
  assert.equal(upstreamError.status,502);
  assert(!JSON.stringify(upstreamError).includes('KEY-LEAK'));
});

test('transport failure, oversized payload, and missing quota denominator never synthesize usage',async()=>{
  const failure=await readGhostStatus(env,async()=>{throw Error('secret!');},NOW);
  assert.equal(failure.status,502);
  const huge=await readGhostStatus(env,async()=>new Response('x'.repeat(100000)),NOW);
  assert.equal(huge.status,502);
  const source=fixture();
  source.providers[0].quota={status:'verified',used:5,limit:4,observed_at:NOW};
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers[0].quota,null);
  assert.equal(result.body.native_clock_verified,false);
});

test('quota verification requires fresh per-provider evidence, not merely a fresh overall status',async()=>{
  const source=fixture();
  source.providers[0].quota={status:'verified',used:2,limit:100,observed_at:NOW-900001};
  source.providers[1].quota={status:'verified',used:2,limit:100,observed_at:NOW+120001};
  source.providers[2].quota={status:'verified',used:2,limit:100,observed_at:NOW-900000};
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers[0].quota,null);
  assert.equal(result.body.providers[1].quota,null);
  assert.equal(result.body.providers[2].quota?.status,'verified');
});

test('quota readback rejects mismatched remaining counts and expired reset clocks',async()=>{
  const source=fixture();
  source.providers[0].quota={status:'verified',used:2,limit:100,remaining:99,observed_at:NOW,resets_at:NOW+60000};
  source.providers[1].quota={status:'verified',used:2,limit:100,remaining:98,observed_at:NOW,resets_at:NOW-1};
  source.providers[2].quota={status:'verified',used:2,limit:100,remaining:98,observed_at:NOW-1000,resets_at:NOW+60000};
  const result=await readGhostStatus(env,mock(source),NOW);
  assert.equal(result.status,200);
  assert.equal(result.body.providers[0].quota,null);
  assert.equal(result.body.providers[1].quota,null);
  assert.equal(result.body.providers[2].quota?.status,'verified');
  assert.equal(result.body.providers[2].quota.used,2);
  assert.equal(result.body.providers[2].quota.limit,100);
});

test('HUD Worker protects readback behind existing authentication and disallows mutation',()=>{
  const worker=readFileSync(new URL('../integrations/hud-cloud/worker.mjs',import.meta.url),'utf8');
  const auth=worker.indexOf('if (!await authorized(authRequest, ingest || chatWriter');
  const gate=worker.indexOf("if (url.pathname === '/api/ghost/status')");
  const dispatch=worker.indexOf('const result = await readGhostStatus(env, fetcher, now)');
  assert(auth>=0 && gate>auth && dispatch>gate);
  assert.match(worker.slice(gate,dispatch),/request.method !== 'GET'/);
  assert.doesNotMatch(worker.slice(gate,dispatch),/workforceTick|GHOST_WRITER_TOKEN|cloudGeminiChat/);
});


test('private Site destination must be exact, owner-bound and non-redirectable',async()=>{
 let calls=0;const fetcher=()=>{calls++;throw Error('unexpected');};
 const bad=[
  null,'','http://private-ledger.example.chatgpt.site/api/ghost/service',
  'https://attacker.example/api/ghost/service',
  'https://private-ledger.example.chatgpt.site.evil.com/api/ghost/service',
  'https://private-ledger.example.chatgpt.site/api/ghost/service?next=1',
  'https://private-ledger.example.chatgpt.site/api/ghost/service#fragment',
  'https://user:pass@private-ledger.example.chatgpt.site/api/ghost/service',
  'https://private-ledger.example.chatgpt.site:8443/api/ghost/service',
  'https://private-ledger.example.chatgpt.site/api/ghost/service/../other'
 ];
 for(const url of bad){
  const result=await readGhostStatus({...env,GHOST_SITE_SERVICE_URL:url},fetcher,NOW);
  assert.equal(result.status,503);
  assert.equal(result.body.error,'cloud_readback_not_configured');
 }
 assert.equal(calls,0);
});
