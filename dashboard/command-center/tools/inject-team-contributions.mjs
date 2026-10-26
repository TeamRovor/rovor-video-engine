#!/usr/bin/env node
/* Preserve the complete native HUD and add one isolated team activity module to the staged Pages artifact. */
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
const root = process.argv[2];
if (!root) throw new Error('Usage: node inject-team-contributions.mjs <pages-root>');
const target = resolve(join(root, 'native-v8-9', 'index.html'));
const moduleFile = resolve(join(root, 'native-v8-9', 'team-contributions.js'));
const original = readFileSync(target, 'utf8');
readFileSync(moduleFile, 'utf8'); // Fail closed if the module is absent.
if (!original.includes('id="activityPanel"') || !original.includes('window.ROVOR_NATIVE')) {
  throw new Error('Unexpected native HUD: activity panel or controller missing; refusing to inject.');
}
const marker = '<script defer src="./team-contributions.js"></script>';
if (!original.includes(marker)) {
  if (!original.includes('</body>')) throw new Error('Native HUD closing body not found');
  writeFileSync(target, original.replace('</body>', marker + '\n</body>'), 'utf8');
}
console.log('Original native HUD retained; team attribution script staged.');
