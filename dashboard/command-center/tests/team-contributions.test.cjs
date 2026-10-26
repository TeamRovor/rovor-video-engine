'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const inject = path.join(__dirname, '..', 'tools', 'inject-team-contributions.mjs');
const src = path.join(__dirname, '..', 'native-v8-9', 'team-contributions.js');

test('team tracking maps three unique branches and attributes shared Windows PR to Keona and Bakir', () => {
  const source = fs.readFileSync(src, 'utf8');
  for (const branch of ['amar-work', 'bakir-work', 'evan-work']) assert.match(source, new RegExp(branch));
  assert.match(source, /Keona \+ Bakir/);
  assert.match(source, /TeamRovor login cannot prove/);
  assert.match(source, /compare\/main/);
  assert.match(source, /ahead_by/);
  assert.match(source, /GitHub status unavailable/);
  assert.match(source, /behind_by/);
  assert.match(source, /behind main/);
  assert.match(source, /prsAvailable/);
  assert.match(source, /https:\/\/github\.dev\//);
  assert.match(source, /BAKIR-PUBLISH\.md/);
  assert.match(source, /merged_at/);
  assert.match(source, /MERGED INTO MAIN/);
  assert.match(source, /DRAFT \/ NOT PUBLISHED TO MAIN/);
  assert.match(source, /OPEN \/ REVIEW PENDING/);
  assert.match(source, /CLOSED WITHOUT MERGE/);
  assert.match(source, /No unmerged commits is expected after merge/);
  assert.match(source, /Last PR update:/);
  assert.match(source, /Latest recorded branch PR:/);
});

test('injector stages module in existing HUD, is idempotent, and refuses unexpected source', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'rovor-team-hud-'));
  const native = path.join(dir, 'native-v8-9');
  fs.mkdirSync(native);
  fs.writeFileSync(path.join(native, 'team-contributions.js'), fs.readFileSync(src));
  const page = path.join(native, 'index.html');
  const original = '<html><body><div id="activityPanel"></div><script>window.ROVOR_NATIVE={};</script></body></html>';
  try {
    fs.writeFileSync(page, original);
    execFileSync(process.execPath, [inject, dir]);
    const first = fs.readFileSync(page, 'utf8');
    assert.ok(first.includes('src="./team-contributions.js"'));
    assert.ok(first.includes('id="activityPanel"'));
    execFileSync(process.execPath, [inject, dir]);
    assert.equal(fs.readFileSync(page, 'utf8'), first);
    fs.writeFileSync(page, '<html><body>different HUD</body></html>');
    assert.throws(() => execFileSync(process.execPath, [inject, dir], { stdio: 'pipe' }));
    assert.equal(fs.readFileSync(page, 'utf8'), '<html><body>different HUD</body></html>');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
