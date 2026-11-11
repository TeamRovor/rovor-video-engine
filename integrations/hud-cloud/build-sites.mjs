#!/usr/bin/env node
// Build a self-contained private Site without forking the original HUD source.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
export function bundleSitesWorker(core, adapter, html, quotaJS = '') {
  // Allow the Cloudflare worker to have a scheduled D1 cleanup handler without
  // leaking that worker-specific export into the legacy self-contained Site.
  // Exactly one default export is required; duplicated or unexpected shapes fail.
  const exportPositions = [...core.matchAll(/\nexport default \{/g)];
  const coreEnd = exportPositions.length === 1 ? core.slice(exportPositions[0].index) : '';
  if (!coreEnd.includes('fetch(request, env) { return handle(request, env); }') ||
      !coreEnd.trimEnd().endsWith('};')) throw Error('Unexpected source module shape');
  const adapterImport = "import {handle} from './worker.mjs';";
  if (adapter.split(adapterImport).length !== 2) throw Error('Unexpected source module shape');
  if (!html.includes('window.ROVOR_START_OMNIROUTE') || !html.includes('</body>')) throw Error('Original HUD live adapter missing');
  const plain = code => code.replace(/^export (?=(?:(?:async )?function|(?:const|let|class))\b)/gm, '');
  const monitorImport = "import {readGoogleGeminiQuota} from './gemini-cloud-monitoring.mjs';";
  const cloudGeminiImport = "import {cloudGeminiModels,cloudGeminiChat,cloudGeminiUsage} from './cloud-gemini-chat.mjs';";
  const workforceImport = "import {intake as workforceIntake,control as workforceControl,status as workforceStatus,\n  draft as workforceDraft,review as workforceReview,tick as workforceTick,recordNativeTick}\n  from './approved-workforce.mjs';";
  if(core.split(workforceImport).length!==2)throw Error('Unexpected Cloudflare workforce import');
  // The original legacy Site is a separate private D1 and has no Cloudflare
  // workforce tables. Fail its new routes CLOSED rather than bundling a
  // second execution/review ledger into the old Site by accident.
  const workforceUnavailable = [
    'const __cloudflareOnlyWorkforce=()=>({status:404,body:{error:"cloudflare_workforce_not_on_site"}});',
    'const workforceIntake=__cloudflareOnlyWorkforce, workforceControl=__cloudflareOnlyWorkforce;',
    'const workforceStatus=__cloudflareOnlyWorkforce, workforceDraft=__cloudflareOnlyWorkforce;',
    'const workforceReview=__cloudflareOnlyWorkforce, workforceTick=__cloudflareOnlyWorkforce;'
  ].join('\n')+'\n';
  const groqImport = "import {GROQ_CLOUD_ROUTE,groqCloudReady,cloudGroqChat,cloudGroqStatus} from './groq-cloud-chat.mjs';";
  const groqProbeImport = "import {probeGroqCatalogue} from './groq-quota-monitor.mjs';";
  const groqCatalogImport = "import {groqCatalogEvidence,recordGroqCompletionQuota,groqCompletionQuotaEvidence} from './groq-quota-monitor.mjs';";
  const ideaImport = "import {submitIdea,listIdeas} from './idea-inbox.mjs';";
  const discoveryImport = "import {submitDiscovery,discoveryStatus} from './discovery-inbox.mjs';";
  const sourceImport = "import {getRepoSource} from './repo-source.mjs';";
  const nativeDiscoveryImport = "import {nativeDiscoveryTick,nativeDiscoveryStatus} from './native-github-discovery.mjs';";
  const githubPatchImport = "import {queueGithubPatch,githubPatchStatus,githubPatchTick,previewGithubPatchSource,queueGithubPatchTask} from './github-patch-gateway.mjs';";
  if(core.split(githubPatchImport).length!==2)throw Error('Unexpected GitHub patch import');
  const githubPatchUnavailable = "const queueGithubPatch=()=>({status:404,body:{error:'cloudflare_only'}}),githubPatchStatus=()=>({source:'cloudflare_only',configured:false,items:[]}),previewGithubPatchSource=queueGithubPatch,queueGithubPatchTask=queueGithubPatch;\n";
  if(core.split(nativeDiscoveryImport).length!==2)throw Error('Unexpected native discovery import');
  const nativeDiscoveryUnavailable = "const nativeDiscoveryStatus=()=>({source:'cloudflare_only',configured:false,enabled:false});\n";
  const discoveryValidatorImport = "import {validateIdea} from './idea-inbox.mjs';";
  const relayImport = "import {catalog as relayCatalog, publishCatalog, enqueue as enqueueChat, claim as claimChat, finish as finishChat, status as chatStatus, cancel as cancelChat, expire as expireChat} from './omniroute-chat-relay.mjs';";
  const chatParserImport = "import {parseChatRequest} from '../../tools/hud_chat.mjs';";
  if (core.split(relayImport).length !== 2) throw Error('Unexpected private chat relay import');
  const parserSource = fs.readFileSync(path.join(root, 'tools/hud_chat.mjs'), 'utf8');
  const relaySource = fs.readFileSync(path.join(here, 'omniroute-chat-relay.mjs'), 'utf8');
  if (relaySource.split(chatParserImport).length !== 2) throw Error('Unexpected chat request parser import');
  const relay = 'const {catalog:relayCatalog,publishCatalog,enqueue:enqueueChat,claim:claimChat,finish:finishChat,status:chatStatus,cancel:cancelChat,expire:expireChat} = (() => {\n' +
    'const {parseChatRequest} = (() => {\n' + plain(parserSource) + '\nreturn {parseChatRequest};})();\n' +
    plain(relaySource.replace(chatParserImport, '')) +
    '\nreturn {catalog,publishCatalog,enqueue,claim,finish,status,cancel,expire};})();\n';
  if (core.split(monitorImport).length !== 2) throw Error('Unexpected Gemini monitoring import');
  const monitor = fs.readFileSync(path.join(here, 'gemini-cloud-monitoring.mjs'), 'utf8');
  const dependency = 'const {readGoogleGeminiQuota} = (() => {\n' + plain(monitor) + '\nreturn {readGoogleGeminiQuota};})();\n';
  const geminiCloudSource = fs.readFileSync(path.join(here, 'cloud-gemini-chat.mjs'), 'utf8');
  if (core.split(cloudGeminiImport).length !== 2) throw Error('Unexpected cloud Gemini import');
  const geminiCloud = plain(geminiCloudSource) + '\n';
  // The original ChatGPT-hosted private Site uses a self-contained data URL.
  // Inline the new cloud-only Groq modules in dependency order, isolated in
  // closures to prevent collisions (e.g. ENDPOINT/MODEL) with Gemini.
  if (core.split(groqImport).length !== 2 || core.split(groqProbeImport).length !== 2)
    throw Error('Unexpected cloud Groq imports');
  const groqQuotaSource = fs.readFileSync(path.join(here, 'groq-quota-monitor.mjs'), 'utf8');
  const groqCloudSource = fs.readFileSync(path.join(here, 'groq-cloud-chat.mjs'), 'utf8');
  if (groqCloudSource.split(groqCatalogImport).length !== 2)
    throw Error('Unexpected Groq quota module import');
  const groqQuota = 'const {groqCatalogEvidence,probeGroqCatalogue,recordGroqCompletionQuota,groqCompletionQuotaEvidence} = (() => {\n' +
    plain(groqQuotaSource) + '\nreturn {groqCatalogEvidence,probeGroqCatalogue,recordGroqCompletionQuota,groqCompletionQuotaEvidence};})();\n';
  const groqCloud = 'const {GROQ_CLOUD_ROUTE,groqCloudReady,cloudGroqChat,cloudGroqStatus} = (() => {\n' +
    plain(groqCloudSource.replace(groqCatalogImport, '')) +
    '\nreturn {GROQ_CLOUD_ROUTE,groqCloudReady,cloudGroqChat,cloudGroqStatus};})();\n';
  // The legacy Site's self-contained worker must not retain ES module
  // imports from the cloud HUD. Inline the newer modules in dependency order,
  // with private lexical scopes so identical local constants cannot clash.
  if(core.split(ideaImport).length!==2 || core.split(discoveryImport).length!==2 ||
     core.split(sourceImport).length!==2)
    throw Error('Unexpected private cloud intake/source import');
  const ideaSrc = fs.readFileSync(path.join(here,'idea-inbox.mjs'),'utf8');
  const discoverySrc = fs.readFileSync(path.join(here,'discovery-inbox.mjs'),'utf8');
  const sourceSrc = fs.readFileSync(path.join(here,'repo-source.mjs'),'utf8');
  if(discoverySrc.split(discoveryValidatorImport).length!==2)
    throw Error('Unexpected discovery validation import');
  const idea = 'const {submitIdea,listIdeas,validateIdea} = (() => {\n'+
    plain(ideaSrc)+'\nreturn {submitIdea,listIdeas,validateIdea};})();\n';
  const discovery = 'const {submitDiscovery,discoveryStatus} = (() => {\n'+
    plain(discoverySrc.replace(discoveryValidatorImport,''))+
    '\nreturn {submitDiscovery,discoveryStatus};})();\n';
  const repoSource = 'const {getRepoSource} = (() => {\n'+
    plain(sourceSrc)+'\nreturn {getRepoSource};})();\n';
  return dependency + relay + groqQuota + groqCloud + idea + discovery + repoSource + geminiCloud +
    workforceUnavailable + nativeDiscoveryUnavailable + githubPatchUnavailable +
    plain(core.replace(monitorImport, '').replace(relayImport, '').replace(cloudGeminiImport, '')
      .replace(groqImport, '').replace(groqProbeImport, '').replace(workforceImport, '')
      .replace(ideaImport, '').replace(discoveryImport, '').replace(sourceImport, '').replace(nativeDiscoveryImport, '').replace(githubPatchImport, '')
      .replace(coreEnd, '')) +
    '\n' + plain(adapter.replace(adapterImport, '')) +
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
  const migration = fs.readFileSync(path.join(here, 'sites-schema.sql'), 'utf8').replace(/;\s*(?=CREATE)/g, ';\n--> statement-breakpoint\n');
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
