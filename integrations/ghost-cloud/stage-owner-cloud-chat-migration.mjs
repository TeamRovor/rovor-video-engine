#!/usr/bin/env node
// Stage one forward-only migration in the EXISTING private ROVOR Site checkout.
// This does not publish a Site, touch credentials, enable inference, or mutate D1.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const PROJECT = 'appgprj_6add1e2cc8c08191839344b34d7dbf50';
const rootOfSource = path.dirname(fileURLToPath(import.meta.url));
function safe(root, relative) {
  let current = root;
  if (fs.lstatSync(root).isSymbolicLink()) throw Error('redirected_site');
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink())
      throw Error('redirected_site');
  }
  return current;
}
function safeMigration(sql) {
  if (typeof sql !== 'string' ||
      !sql.includes('CREATE TABLE IF NOT EXISTS ghost_cloud_owner_chat') ||
      !sql.includes('CREATE INDEX IF NOT EXISTS ghost_cloud_owner_chat_pool') ||
      /(^|\n)\s*(INSERT|UPDATE|DELETE|DROP|ALTER|REPLACE|ATTACH|PRAGMA)\b/i.test(sql))
    throw Error('unexpected_owner_chat_schema');
  return sql.replace(/;[ \t]*\n/g, ';\n--> statement-breakpoint\n');
}
export function stageOwnerCloudChatMigration(directory, {apply = false, sourceDirectory = rootOfSource} = {}) {
  const root = path.resolve(directory);
  if (fs.lstatSync(root).isSymbolicLink()) throw Error('redirected_site');
  const manifestPath = safe(root, '.openai/hosting.json');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  if (manifest.project_id !== PROJECT ||
      !(manifest.d1 === 'DB' || manifest.d1?.binding === 'DB'))
    throw Error('wrong_private_site_or_database');
  const active = fs.readFileSync(safe(root, 'worker/index.js'), 'utf8');
  const compiled = fs.readFileSync(safe(root, 'dist/server/index.js'), 'utf8');
  if (active !== compiled) throw Error('site_bundle_mismatch');
  if (!active.includes('ROVOR_CLOUD_OPERATIONS_V1') ||
      !active.includes('ROVOR_CLOUD_SCHEDULED_SHIFT_V1'))
    throw Error('not_existing_cloud_workforce_site');
  const journalPath = safe(root, 'drizzle/meta/_journal.json');
  const journal = JSON.parse(fs.readFileSync(journalPath, 'utf8'));
  if (journal.version !== '7' || journal.dialect !== 'sqlite' ||
      !Array.isArray(journal.entries) || journal.entries.length < 2 ||
      journal.entries.length > 9999 ||
      journal.entries.some((e, i) => e.idx !== i ||
        !/^\d{4}_[a-z0-9_]+$/.test(e.tag) ||
        !fs.existsSync(safe(root, 'drizzle/' + e.tag + '.sql'))))
    throw Error('invalid_existing_migration_journal');
  const already = journal.entries.find(e => e.tag.endsWith('_owner_cloud_chat'));
  if (already) return {project_id: PROJECT, prepared: false,
    migration: already.tag + '.sql', already_journaled: true,
    deployment_performed: false, d1_applied: 'unknown'};
  const source = safe(sourceDirectory, 'migrations/owner-cloud-chat.sql');
  const sql = safeMigration(fs.readFileSync(source, 'utf8'));
  const tag = String(journal.entries.length).padStart(4, '0') + '_owner_cloud_chat';
  const destination = safe(root, 'drizzle/' + tag + '.sql');
  if (fs.existsSync(destination)) throw Error('migration_collision');
  if (apply) {
    fs.writeFileSync(destination, sql, {flag: 'wx'});
    journal.entries.push({idx: journal.entries.length, version: '6',
      when: Date.now(), tag, breakpoints: true});
    const tmp = safe(root, 'drizzle/meta/_journal.json.owner_cloud_chat.tmp');
    fs.writeFileSync(tmp, JSON.stringify(journal, null, 2) + '\n', {flag: 'wx'});
    fs.renameSync(tmp, journalPath);
  }
  return {project_id: PROJECT, prepared: apply, migration: tag + '.sql',
    already_journaled: false, deployment_performed: false,
    d1_applied: false, runtime_bundle_contains_owner_chat:
      active.includes('function ownerChatModels(') &&
      active.includes('/api/ghost/chat')};
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  if (!process.argv[2] || process.argv.slice(3).some(arg => arg !== '--apply'))
    throw Error('Usage: stage-owner-cloud-chat-migration.mjs EXISTING_PRIVATE_SITE [--apply]');
  console.log(JSON.stringify(stageOwnerCloudChatMigration(process.argv[2],
    {apply: process.argv.includes('--apply')})));
}
