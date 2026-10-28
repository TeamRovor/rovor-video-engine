'use strict';
// Guard the ROVOR quota glance and workload controls against the compact
// 47px rings / <10px text regressions. No live network or inference needed.
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const board=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/live-quota-board.js'),'utf8');
const workload=fs.readFileSync(path.join(__dirname,'../dashboard/command-center/native-v8-9/workload-popup.css'),'utf8');

test('nine connection overview has readable 5/3/2-column breakpoints and circular rings',()=>{
 assert.match(board,/\.rvq-overview\{display:grid;grid-template-columns:repeat\(5,minmax\(0,1fr\)\)/);
 assert.match(board,/@media\(max-width:1150px\)\{#rovor-workload-popup \.rvq-overview\{grid-template-columns:repeat\(3,minmax\(0,1fr\)\)\}\}/);
 assert.match(board,/@media\(max-width:650px\)\{[\s\S]*?\.rvq-overview\{grid-template-columns:repeat\(2,minmax\(0,1fr\)\)/);
 assert.match(board,/\.rvq-overview \.rvq-ring\{width:68px;height:68px\}/);
 assert.match(board,/\.rvq-overview \.rvq-ring-core small\{font-size:9px\}/);
 assert.match(board,/\.rvq-overview-name\{[^\n]*font:700 12px/);
});

test('missing telemetry is not described as a failed connection',()=>{
 assert.match(board,/!live\?'TELEMETRY STALE'/);
 assert.doesNotMatch(board,/!live\?'DISCONNECTED'/);
 assert.match(board,/slot\.enabled===true\?'GATEWAY ENABLED · PROVIDER UNVERIFIED'/);
 // The existing data checks must remain in place: only verified evidence fills quotas.
 assert.match(board,/const pct=local\?100\*local\.used\/local\.total:verified\?100\*used\/limit:null/);
 assert.match(board,/aria-label="Provider quota unknown"/);
});

test('compact workload switches and rows remain finger-sized on phones',()=>{
 assert.match(workload,/#workloadPanel \.wl-compact-tabs button\{[^\n]*min-height:44px/);
 assert.match(workload,/#workloadPanel \.wl-compact-row\{[^\n]*min-height:44px/);
 assert.match(workload,/#workloadPanel \.wl-compact-status\{font-size:11px/);
 assert.match(workload,/#workloadPanel \.wl-compact-name\{white-space:normal;[^\n]*font-size:12px/);
 assert.match(workload,/#rovor-workload-popup \.wl-period \.wl-button\{min-height:44px/);
});
