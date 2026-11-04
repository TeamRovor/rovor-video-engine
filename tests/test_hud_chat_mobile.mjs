import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const src=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-chat.js',import.meta.url),'utf8');

test('Ask ROVOR keeps iOS focus controls at Safari-safe 16px and preserves pinch zoom',()=>{
  assert.match(src, /iosTypeAndKeyboardCSS/);
  assert.match(src, /#rvc select, #rvc textarea, #rvc input[^{]*\{\s*font-size:16px!important;/);
  assert.match(src, /#rvc select\{font-size:16px!important;/);
  assert.doesNotMatch(src,/user-scalable\s*=\s*no|maximum-scale\s*=\s*1/);
});

test('mobile chat adjusts to visible iPhone viewport when keyboard appears',()=>{
  for(const marker of [
    'window.visualViewport','--rvc-vv-height','--rvc-vv-top',
    "addEventListener('resize',syncVisualViewport)",
    "addEventListener('orientationchange',syncVisualViewport)",
    "input.focus({preventScroll:true})",
    "const polishedMobileCSS =",
  ]) assert(src.includes(marker),marker);
  assert.match(src, /#rvc\[data-open=true\] \{ top:var\(--rvc-vv-top/);
  assert.match(src, /height:var\(--rvc-vv-height/);
});

test('responsive iPhone and tablet preserve model selection, closing and history access',()=>{
  for(const marker of [
    'grid-template-areas:"menu source clear close" "model model model model"',
    'grid-area:model','grid-area:source','data-side-open=true',
    'rvc-side-backdrop','max-width:1100px','max-width:760px',
    'const sideBackdrop=','document.body.style.overflow',
  ]) assert(src.includes(marker),marker);
});

test('Ask ROVOR is a private chat, not a silently running employee scheduler',()=>{
  assert(src.includes('/api/hud/chat/models'));
  assert(src.includes('/api/hud/chat/submit'));
  assert(src.includes('/api/hud/chat/status/'));
  assert(src.includes("'omniroute'"));
  assert(src.includes('No confirmed model reply'));
  assert.doesNotMatch(src,/fetch\(['"]https?:\/\//);
});


test('failed response is retained locally but never sent to a subsequent model as context',()=>{
  assert.match(src,/outcome:'failed'/);
  assert.match(src,/outcome:'complete'/);
  assert.match(src,/history\.filter\(m=>m\.role==='user'\|\|\(m\.role==='assistant'&&m\.outcome==='complete'\)\)/);
  assert.match(src,/rvc-receipt/);
  assert.match(src,/Copy response/);
  assert.match(src,/cancelConfirmed/);
  assert.match(src,/api\/hud\/chat\/cancel\//);
});


test('Ask ROVOR shows nine-provider inventory with explicit freshness and never treats enabled as verified',()=>{
  assert.match(src,/refreshProviderInventory/);
  assert.match(src,/\/api\/hud\/omniroute\?period=24h/);
  assert.match(src,/STALE \/ NOT LIVE/);
  assert.match(src,/PROVIDER INVENTORY UNAVAILABLE/);
  assert.match(src,/model access unverified/);
  assert.match(src,/rvc-provider-inspect/);
  assert.match(src,/Mac bridge reported · /);
  assert.match(src,/allowed routes · confirm a reply to verify use/);
  assert.match(src,/Free-tagged model routes/);
  assert.match(src,/Owner-allowlisted model routes/);
  assert.match(src,/refreshButton.onclick/);
  assert.match(src,/rvc-connection-bar/);
  assert.match(src,/Refresh model availability and provider status/);
});
