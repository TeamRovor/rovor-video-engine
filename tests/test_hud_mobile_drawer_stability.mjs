import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {Script} from 'node:vm';

const html=readFileSync(new URL('../dashboard/command-center/native-v8-9/index.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../dashboard/command-center/native-v8-9/hud-mobile.css',import.meta.url),'utf8');
const worker=readFileSync(new URL('../integrations/hud-cloud/worker.mjs',import.meta.url),'utf8');

test('existing 1MB+ native HUD is syntactically valid after surgical scroll fix',()=>{
 assert(html.length>1200000);
 const scripts=[...html.matchAll(/<script(?:\s+[^>]*)?>([\s\S]*?)<\/script>/g)];
 assert(scripts.length>0);
 for(const [i,m] of scripts.entries())new Script(m[1],{filename:'original-hud-'+i+'.js'});
});

test('five-second background telemetry skips re-renders while user scrolls or searches',()=>{
 assert.match(html,/const recentlyInteracting=\(\)=>performance\.now\(\)-lastLiveInteractionAt<1900/);
 assert.match(html,/document\.addEventListener\('touchmove',recordLiveInteraction/);
 assert.match(html,/document\.addEventListener\('scroll',recordLiveInteraction,true\)/);
 assert.match(html,/if\(!force&&popupHost\.firstElementChild&&[\s\S]*?recentlyInteracting\(\)/);
 assert.match(html,/document\.activeElement\?\.hasAttribute\('data-live-search'\)/);
 assert.match(html,/function applySearchFilter\(\)/);
 assert.match(html,/filter=event\.target\.value;[\s\S]*?applySearchFilter\(\)/);
 assert.doesNotMatch(html,/filter=event\.target\.value;paintPopup\(\)/);
 assert.match(html,/const outerScroll=popupHost\.closest\('\.drawer-inner'\)\?\.scrollTop/);
 assert.match(html,/outer\.scrollTop=outerScroll/);
 assert.match(html,/if\(b\.dataset\.liveTab\)\{tab=b\.dataset\.liveTab;redraw\(true\)/);
 assert.match(html,/finally\{inFlight=false;redraw\(\)/);
});

test('phone drawer has a stable viewport, readable tabs and a single vertical scroll owner',()=>{
 assert.match(worker,/<link rel="stylesheet" href="\/hud-mobile\.css">/);
 assert.match(css,/height:100dvh!important/);
 assert.match(css,/#screen \.drawer-inner/);
 assert.match(css,/overscroll-behavior-y:contain/);
 assert.match(css,/-webkit-overflow-scrolling:touch/);
 assert.match(css,/#rovor-workload-popup \.wl-model-scroll\{[\s\S]*?max-height:none!important/);
 assert.match(css,/#rovor-workload-popup \.wl-actions\{[\s\S]*?grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
 assert.match(css,/#screen \.drawer-inner \.tool-input\{[\s\S]*?font-size:16px!important/);
 assert.match(html,/originalBodyOverflow=document\.body\.style\.overflow/);
 assert.match(html,/document\.body\.style\.overflow=originalBodyOverflow\?\?''/);
 assert.match(html,/\(pointer:coarse\), \(max-width:780px\)/);
});

test('mobile style is read-only and never alters paid routing or model permissions',()=>{
 assert.doesNotMatch(css,/api_key|token|secret|fetch\(|display:none!important.*\.drawer/);
 assert.doesNotMatch(worker,/GEMINI_ACTIVATE_ONCE.*true.*true/);
});
