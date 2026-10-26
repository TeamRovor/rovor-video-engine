#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateCloudFeed, validateCloudReceipt} from './cloud-activity.mjs';
import {latestOwnerReviews} from './cloud-reviews.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const TAG = '<script type="module" src="./cloud-activity.mjs"></script>';

export function compileCloudActivity(receipts, now = Date.now()) {
  if (!Array.isArray(receipts) || receipts.length > 1000) throw Error('Cloud receipt inventory invalid');
  const checked = receipts.map(r => validateCloudReceipt(r, now));
  if (new Set(checked.map(r => r.id)).size !== checked.length) throw Error('Duplicate receipt');
  checked.sort((a, b) => Date.parse(b.completed_at) - Date.parse(a.completed_at));
  return validateCloudFeed({schema_version: 1, source: 'recorded_cloud_shifts', generated_at: new Date(now).toISOString(), receipts: checked.slice(0, 200)}, now);
}

export function injectCloudActivity(html) {
  if (!html.includes('id="activityPanel"') || html.split('</body>').length !== 2) throw Error('Unexpected original HUD');
  if (html.includes(TAG)) return html;
  return html.replace('</body>', TAG + '\n</body>');
}

export function readCloudReceipts() {
  const dir = path.join(root, 'coordination/cloud-shifts');
  const names = fs.readdirSync(dir).filter(name => /^[a-z0-9-]+\.json$/.test(name));
  if (names.length > 1000) throw Error('Archive older cloud receipts before adding more');
  return names.map(name => {
    const file = path.join(dir, name), stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 4096) throw Error('Invalid receipt file');
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  });
}

export function buildCloudActivity(target, now = Date.now()) {
  const receipts = readCloudReceipts(), feed = compileCloudActivity(receipts, now);
  const reviewDir = path.join(root, 'coordination/cloud-reviews');
  const names = fs.existsSync(reviewDir) ? fs.readdirSync(reviewDir).filter(n => /^issue-[1-9]\d*\.json$/.test(n)) : [];
  if (names.length > 2000) throw Error('Archive older owner reviews');
  const rows = names.map(name => {
    const file = path.join(reviewDir, name), stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.isSymbolicLink() || stat.size > 8192) throw Error('Invalid owner review file');
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  });
  const reviews = latestOwnerReviews(rows, receipts, now).filter(r => feed.receipts.some(x => x.id === r.receipt_id));
  const native = path.join(path.resolve(target), 'native-v8-9');
  const index = path.join(native, 'index.html'), original = fs.readFileSync(index, 'utf8');
  const html = injectCloudActivity(original);
  fs.writeFileSync(path.join(native, 'cloud-activity.json'), JSON.stringify(feed, null, 2) + '\n');
  fs.writeFileSync(path.join(native, 'cloud-reviews.json'), JSON.stringify({schema_version: 1, source: 'github_owner_review_ledger', reviews}, null, 2) + '\n');
  fs.copyFileSync(path.join(here, 'cloud-activity.mjs'), path.join(native, 'cloud-activity.mjs'));
  fs.copyFileSync(path.join(here, 'cloud-reviews.mjs'), path.join(native, 'cloud-reviews.mjs'));
  fs.writeFileSync(index, html);
  return {receipts: feed.receipts.length, original_hud_bytes: Buffer.byteLength(original), artifact_hud_bytes: Buffer.byteLength(html)};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!process.argv[2]) throw Error('Pass the Pages artifact directory');
  console.log(JSON.stringify(buildCloudActivity(process.argv[2])));
}
