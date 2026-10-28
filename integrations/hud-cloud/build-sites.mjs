#!/usr/bin/env node
// Build a self-contained private Site without forking the original HUD source.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
export function bundleSitesWorker(core, adapter, html, quotaJS = '') {
  const coreEnd = 'export default {fetch(request, env) { return handle(request, env); }};';
  const adapterImport = "import {handle} from './worker.mjs';";
  if (core.split(coreEnd).length !== 2 || adapter.split(adapterImport).length !== 2) throw Error('Unexpected source module shape');
  if (!html.includes('window.ROVOR_START_OMNIROUTE') || !html.includes('</body>')) throw Error('Original HUD live adapter missing');
  const plain = code => code.replace(/^export (?=(?:async )?function )/gm, '');
  const monitorImport = "import {readGoogleGeminiQuota} from './gemini-cloud-monitoring.mjs';";
  if (core.split(monitorImport).length !== 2) throw Error('Unexpected Gemini monitoring import');
  const monitor = fs.readFileSync(path.join(here, 'gemini-cloud-monitoring.mjs'), 'utf8');
  const dependency = 'const {readGoogleGeminiQuota} = (() => {\n' + plain(monitor) + '\nreturn {readGoogleGeminiQuota};})();\n';
  return dependency + plain(core.replace(monitorImport, '').replace(coreEnd, '')) + '\n' + plain(adapter.replace(adapterImport, '')) +
    '\nconst siteFetch = createSitesHandler(' + JSON.stringify(html) + ', ' + JSON.stringify(quotaJS) + ');\nexport default {fetch: siteFetch};\n';
}

export function buildSite(destination) {
  const directory = path.resolve(destination);
  const manifestPath = path.join(directory, '.openai/hosting.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (typeof manifest.project_id !== 'string' || !manifest.project_id.startsWith('appgprj_')) throw Error('Registered Site identity required');
  if (manifest.static) throw Error('Refusing static hosting configuration');
  const html = fs.readFileSync(path.join(root, 'dashboard/command-center/native-v8-9/index.html'), 'utf8');
  const quotaJS = fs.readFileSync(path.join(root, 'dashboard/command-center/native-v8-9/live-quota-board.js'), 'utf8');
  const code = bundleSitesWorker(fs.readFileSync(path.join(here, 'worker.mjs'), 'utf8'),
    fs.readFileSync(path.join(here, 'sites-adapter.mjs'), 'utf8'), html, quotaJS);
  const nextManifest = {...manifest, d1: manifest.d1 || {binding: 'DB'}, r2: manifest.r2 || null,
    capabilities: [...new Set([...(manifest.capabilities || []), 'mcp'])]};
  // A first schema-only migration; never replace a previously applied migration.
  const migrationDir = path.join(directory, 'drizzle');
  const migration = fs.readFileSync(path.join(here, 'schema.sql'), 'utf8').replace(/;\s*(?=CREATE)/g, ';\n--> statement-breakpoint\n');
  const migrationPath = path.join(migrationDir, '0000_hud_telemetry.sql');
  if (fs.existsSync(migrationPath) && fs.readFileSync(migrationPath, 'utf8') !== migration) throw Error('Existing migration differs; append a migration instead');
  const journal = {version: '7', dialect: 'sqlite', entries: [{idx: 0, version: '6', when: 1792838400000,
    tag: '0000_hud_telemetry', breakpoints: true}]};
  const journalPath = path.join(migrationDir, 'meta/_journal.json');
  if (fs.existsSync(journalPath) && JSON.stringify(JSON.parse(fs.readFileSync(journalPath, 'utf8'))) !== JSON.stringify(journal)) throw Error('Existing migration journal differs');
  fs.mkdirSync(path.join(directory, 'worker'), {recursive: true});
  fs.mkdirSync(path.join(directory, 'dist/server'), {recursive: true});
  fs.mkdirSync(path.join(directory, 'dist/.openai'), {recursive: true});
  fs.writeFileSync(path.join(directory, 'worker/index.js'), code);
  fs.writeFileSync(path.join(directory, 'dist/server/index.js'), code);
  fs.writeFileSync(manifestPath, JSON.stringify(nextManifest, null, 2) + '\n');
  fs.writeFileSync(path.join(directory, 'dist/.openai/hosting.json'), JSON.stringify(nextManifest, null, 2) + '\n');
  fs.mkdirSync(path.dirname(journalPath), {recursive: true});
  fs.writeFileSync(migrationPath, migration);
  fs.writeFileSync(journalPath, JSON.stringify(journal, null, 2) + '\n');
  return {project_id: manifest.project_id, worker_bytes: Buffer.byteLength(code), original_hud_bytes: Buffer.byteLength(html)};
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!process.argv[2]) throw Error('Pass the existing registered Site checkout directory');
  console.log(JSON.stringify(buildSite(process.argv[2])));
}
