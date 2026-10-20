'use strict';
// Technical smoke checks using unchanged repository artwork. Not artistic acceptance.
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const sharp = require(process.env.EVAN_SHARP || 'sharp');
const {renderReference, overlay} = require('./evan_reference.cjs');
const {render} = require('./evan_puppet.cjs');
const {wrapCaption} = require('./caption_utils.cjs');

function scene(extra = {}) {
  return {duration: 2, characterStyle: 'reference',
    segments: [{start: 0, end: 2, text: 'An existing artwork smoke check.'}],
    captions: [{start: 0, end: 2, text: 'Rovor <menu> & "captions"'}],
    mouthCues: [{start: 0, end: 2, value: 'X'}],
    gestures: [], scenePlan: [{start: 0, end: 2, kind: 'browser', title: 'Your website'}],
    ...extra};
}

test('reference poses decode to complete portrait JPEGs', async () => {
  for (const sample of [
    scene(),
    scene({gestures: [{start: 0, end: 2, kind: 'point'}], mouthCues: [{start: 0, end: 2, value: 'B'}]}),
    scene({gestures: [{start: 0, end: 2, kind: 'present'}], mouthCues: [{start: 0, end: 2, value: 'E'}]})
  ]) {
    const frame = await renderReference(0.5, sample);
    const meta = await sharp(frame).metadata();
    assert.equal(meta.format, 'jpeg');
    assert.equal(meta.width, 720);
    assert.equal(meta.height, 1280);
    // Force full pixel decoding, rather than only accepting a readable header.
    const {info} = await sharp(frame).raw().toBuffer({resolveWithObject: true});
    assert.equal(info.width * info.height, 720 * 1280);
  }
});

test('existing vector renderer rasterizes with escaped caption text', async () => {
  const sample = scene({characterStyle: 'vector'});
  const image = await sharp(Buffer.from(render(0.5, sample))).png().toBuffer();
  const metadata = await sharp(image).metadata();
  assert.equal(metadata.width, 720);
  assert.equal(metadata.height, 1280);
  const svg = overlay(0.5, sample);
  assert.ok(svg.includes('&lt;menu&gt;'));
  assert.ok(svg.includes('&amp;'));
  assert.ok(svg.includes('&quot;captions&quot;'));
});

test('caption wrapping stays bounded and callers cannot mutate cached lines', () => {
  const text = 'A very long caption '.repeat(30);
  const lines = wrapCaption(text, 34, 3);
  assert.ok(lines.length <= 3);
  assert.ok(lines.every(line => line.length <= 34));
  assert.ok(lines.at(-1).endsWith('…'));
  lines[0] = 'mutated by a caller';
  assert.notEqual(wrapCaption(text, 34, 3)[0], lines[0]);
});

test('frame subprocess writes only the requested completed frame range', async () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'rovor-frames-'));
  try {
    const sceneFile = path.join(folder, 'scene.json');
    const frames = path.join(folder, 'frames');
    fs.writeFileSync(sceneFile, JSON.stringify(scene({duration: 2 / 24})));
    const result = spawnSync(process.execPath, [path.join(__dirname, 'render_frames.cjs'),
      sceneFile, frames, '0', '2'], {encoding: 'utf8', timeout: 45000});
    assert.equal(result.status, 0, result.stderr || String(result.error));
    assert.equal(JSON.parse(result.stdout).nextFrame, 2);
    assert.deepEqual(fs.readdirSync(frames).sort(), ['000000.jpg', '000001.jpg']);
    for (const name of fs.readdirSync(frames)) {
      const metadata = await sharp(path.join(frames, name)).metadata();
      assert.equal(metadata.width, 720);
      assert.equal(metadata.height, 1280);
    }
    const bad = spawnSync(process.execPath, [path.join(__dirname, 'render_frames.cjs'),
      sceneFile, frames, '-1', '2'], {encoding: 'utf8', timeout: 10000});
    assert.notEqual(bad.status, 0);
    assert.match(bad.stderr, /Invalid frame range/);
  } finally {
    fs.rmSync(folder, {recursive: true, force: true});
  }
});
