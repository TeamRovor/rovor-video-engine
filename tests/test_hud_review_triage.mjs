import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {scoreDraft, triage} from '../tools/hud_review_triage.mjs';

const good = 'Line one.\n' + 'Solid supported point. '.repeat(80) + '\nDone.';

test('scores empty, short, truncated and refused drafts lower than a complete one', () => {
  assert.equal(scoreDraft({answer: good}).score, 100);
  assert.deepEqual(scoreDraft({answer: ''}).flags, ['empty']);
  assert(scoreDraft({answer: 'Short.'}).flags.includes('very_short'));
  assert(scoreDraft({answer: good.slice(0, -1) + ' and then'}).flags.includes('looks_truncated'));
  assert(scoreDraft({answer: good + '\nI cannot verify this.'}).flags.includes('refusal'));
  assert(scoreDraft({answer: good, source_edits: true}).score <= 50);
});

test('triage ranks drafts best first and tolerates broken files', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'triage-'));
  const make = (name, receipt) => { fs.mkdirSync(path.join(dir, name)); fs.writeFileSync(path.join(dir, name, 'x.receipt.json'), receipt); };
  make('a', JSON.stringify({id: 'a', answer: ''}));
  make('b', JSON.stringify({id: 'b', answer: good}));
  make('c', '{bad');
  const r = triage(dir);
  assert.equal(r.total, 3); assert.equal(r.rows[0].dir, 'b'); assert.equal(r.ready, 1); assert.equal(r.flagged, 2);
  fs.rmSync(dir, {recursive: true});
});
