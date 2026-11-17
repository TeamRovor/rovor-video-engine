import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readBoundedGroqResponse} from '../integrations/hud-cloud/groq-cloud-chat.mjs';

const encoder=new TextEncoder();
function reply(chunks){
  let cancelled=false,reads=0;
  const response=new Response(new ReadableStream({
    pull(controller){
      reads++;
      const chunk=chunks.shift();
      if(chunk)controller.enqueue(chunk);
      else controller.close();
    },
    cancel(){cancelled=true;}
  }));
  return {response,get cancelled(){return cancelled;},get reads(){return reads;}};
}

test('accepts a valid JSON result split across byte chunks',async()=>{
  const bytes=encoder.encode(JSON.stringify({model:'openai/gpt-oss-20b',ok:true}));
  const r=reply([bytes.subarray(0,9),bytes.subarray(9)]);
  assert.deepEqual(await readBoundedGroqResponse(r.response),{model:'openai/gpt-oss-20b',ok:true});
});

test('rejects an oversized first chunk before requesting the next chunk',async()=>{
  const r=reply([new Uint8Array(65537),encoder.encode('not read')]);
  await assert.rejects(readBoundedGroqResponse(r.response),/oversized_response/);
  assert.equal(r.reads,1);
  assert.equal(r.cancelled,true);
});

test('bounds cumulative bytes rather than individual chunks',async()=>{
  const r=reply([new Uint8Array(32768),new Uint8Array(32769)]);
  await assert.rejects(readBoundedGroqResponse(r.response),/oversized_response/);
  assert.equal(r.cancelled,true);
});

test('accepts exactly 65536 bytes of valid JSON',async()=>{
  const payload=JSON.stringify({message:'x'.repeat(65522)});
  assert.equal(encoder.encode(payload).byteLength,65536);
  const r=reply([encoder.encode(payload)]);
  assert.equal((await readBoundedGroqResponse(r.response)).message.length,65522);
});

test('rejects invalid UTF-8 and missing body',async()=>{
  const r=reply([new Uint8Array([0x7b,0x22,0x61,0x22,0x3a,0xff,0x7d])]);
  await assert.rejects(readBoundedGroqResponse(r.response));
  await assert.rejects(readBoundedGroqResponse({body:null}),/missing_body/);
});
