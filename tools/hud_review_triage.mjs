#!/usr/bin/env node
/** Read-only triage of worker drafts awaiting review: ranks them so the best are reviewed first.
 * Usage: node tools/hud_review_triage.mjs <drafts-dir> [--json] [--top N]
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const REFUSAL = /\b(i (cannot|can't|am unable|'m unable)|unable to (access|browse|verify)|as an ai)\b/i;

export function scoreDraft(receipt, assignment = {}) {
  const answer = typeof receipt.answer === 'string' ? receipt.answer.trim() : '';
  const flags = [];
  let score = 100;
  if (!answer) { flags.push('empty'); score = 0; }
  else {
    if (answer.length < 400) { flags.push('very_short'); score -= 50; }
    else if (answer.length < 1200) { flags.push('short'); score -= 15; }
    if (!/[.!?)\]`*|]$/.test(answer)) { flags.push('looks_truncated'); score -= 30; }
    if (REFUSAL.test(answer)) { flags.push('refusal'); score -= 30; }
    if (!/\n/.test(answer)) { flags.push('no_structure'); score -= 10; }
  }
  if (receipt.external_effects_allowed || receipt.source_edits) { flags.push('unexpected_side_effects'); score -= 50; }
  return {
    id: receipt.id, packet: assignment.packet, model: receipt.model,
    chars: answer.length, score: Math.max(0, score), flags,
    created_at: receipt.created_at,
  };
}

export function triage(dir) {
  const rows = [];
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    if (!entry.isDirectory()) continue;
    const sub = path.join(dir, entry.name);
    const receiptFile = fs.readdirSync(sub).find(f => f.endsWith('.receipt.json'));
    if (!receiptFile) continue;
    try {
      const receipt = JSON.parse(fs.readFileSync(path.join(sub, receiptFile), 'utf8'));
      let assignment = {};
      try { assignment = JSON.parse(fs.readFileSync(path.join(sub, 'assignment.json'), 'utf8')); } catch {}
      rows.push({...scoreDraft(receipt, assignment), dir: entry.name});
    } catch { rows.push({dir: entry.name, score: 0, flags: ['unreadable']}); }
  }
  rows.sort((a, b) => b.score - a.score || (b.chars || 0) - (a.chars || 0));
  const flagCounts = {};
  rows.forEach(r => r.flags.forEach(f => { flagCounts[f] = (flagCounts[f] || 0) + 1; }));
  return {total: rows.length, ready: rows.filter(r => r.score >= 85).length, flagged: rows.filter(r => r.score < 60).length, flagCounts, rows};
}

if (process.argv[1] && fs.realpathSync(process.argv[1]) === fs.realpathSync(fileURLToPath(import.meta.url))) {
  const dir = process.argv[2];
  if (!dir) { console.error('usage: hud_review_triage.mjs <drafts-dir> [--json] [--top N]'); process.exit(2); }
  const result = triage(dir);
  const top = Number(process.argv[process.argv.indexOf('--top') + 1]) || 10;
  if (process.argv.includes('--json')) console.log(JSON.stringify({...result, rows: result.rows.slice(0, top)}, null, 1));
  else {
    console.log(`${result.total} drafts: ${result.ready} look review-ready, ${result.flagged} flagged`);
    console.log('flags:', JSON.stringify(result.flagCounts));
    console.log(`Top ${top} to review first:`);
    result.rows.slice(0, top).forEach(r => console.log(` ${String(r.score).padStart(3)}  ${String(r.chars).padStart(5)}c  ${r.packet}  [${r.dir.slice(0, 8)}]`));
  }
}
