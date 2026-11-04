// Read-only, bounded code excerpts from the installed ROVOR git checkout.
// Not a GitHub API client, GitHub write tool, shell agent, or credential reader.
// A model can reason about these excerpts, but cannot directly read arbitrary
// files, modify the repository, merge PRs, or dispatch a background task.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';

const exec = promisify(execFile);
const ROOT = fileURLToPath(new URL('../',import.meta.url));
const MAX_CONTEXT = 6200;
const MAX_FILE_BYTES = 240000;
const ALLOWLIST = Object.freeze([
  'README.md',
  'dashboard/command-center/native-v8-9/hud-chat.js',
  'integrations/hud-cloud/worker.mjs',
  'integrations/hud-cloud/omniroute-chat-relay.mjs',
  'integrations/hud-cloud/ASK-ROVOR-SETUP.md',
  'tools/hud_chat.mjs',
  'tools/hud_chat_relay_client.mjs',
  'tools/manage_hud_telemetry_agent.sh',
  'tests/test_hud_chat.mjs',
  'tests/test_hud_omniroute_chat_relay.mjs',
  '.github/workflows/deploy-private-hud-cloudflare.yml',
]);
const SENSITIVE = /-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:gh[pousr]_|gsk_|sk-|hf_|AIza)[A-Za-z0-9_\-]{16,}|\b(?:api[_-]?key|password|secret|token)\s*[:=]\s*['"]?[A-Za-z0-9_\-]{24,}/i;
const TOKENS = /[a-z0-9][a-z0-9._/-]{2,}/g;
const sanitize = line => SENSITIVE.test(line) ? '[line omitted: may contain a credential]' : line.slice(0,260);

export async function readRepoContext(question, {root=ROOT, readFile=fs.readFile, realpath=fs.realpath, git=exec}={}) {
  if (typeof question!=='string') return 'Local ROVOR code context unavailable.';
  let repoRoot;
  try {
    repoRoot=await realpath(root);
    const {stdout}=await git('git',['rev-parse','--show-toplevel'],{cwd:repoRoot,timeout:3000,maxBuffer:4096});
    if (path.resolve(stdout.trim())!==repoRoot) throw Error('unexpected_repository_root');
  } catch {return 'Git checkout unavailable. No GitHub code was read or searched.';}
  let commit='unknown';
  try {
    const {stdout}=await git('git',['rev-parse','--short=12','HEAD'],{cwd:repoRoot,timeout:3000,maxBuffer:4096});
    commit=stdout.trim().replace(/[^a-f0-9]/gi,'').slice(0,12)||'unknown';
  }catch{}
  const words=[...new Set((question.toLowerCase().match(TOKENS)||[])
    .filter(w=>w.length>=4&&!['what','with','from','this','that','please','could','should','github','repository','rovor','code'].includes(w)))].slice(0,12);
  const files=[];
  for(const file of ALLOWLIST){
    const full=path.join(repoRoot,file);
    try{
      // Never follow symlinked files to locations outside this checkout.
      const resolved=await realpath(full);
      if(!resolved.startsWith(repoRoot+path.sep))continue;
      const stat=await fs.stat(resolved);
      if(!stat.isFile()||stat.size>MAX_FILE_BYTES)continue;
      const body=await readFile(resolved,'utf8');
      const lines=body.split('\n');
      const lower=file.toLowerCase();
      const rank=words.reduce((n,w)=>n+(lower.includes(w)?12:0),0)
        +words.reduce((n,w)=>n+(body.toLowerCase().includes(w)?1:0),0);
      files.push({file,lines,rank});
    }catch{/* Missing or unsupported file: omit it rather than searching elsewhere. */}
  }
  // Stable listing gives the model a truthful map of accessible files even
  // when no excerpt matches. It is an allowlist, not complete repository access.
  const title='ROVOR local git checkout (read-only, bounded, commit '+commit+'). Not a live GitHub main fetch; may be stale.\n'
    +'Accessible allowlisted paths: '+files.map(f=>f.file).join(', ')+'.\n'
    +'No repository write, GitHub API, secrets, workflow trigger or arbitrary file access.\n';
  if(!files.length)return title+'No readable approved source files.';
  files.sort((a,b)=>b.rank-a.rank||a.file.localeCompare(b.file));
  let result=title;
  for(const entry of files.slice(0,3)){
    const hits=[];
    for(let i=0;i<entry.lines.length;i++){
      if(words.some(w=>entry.lines[i].toLowerCase().includes(w)))hits.push(i);
      if(hits.length>=3)break;
    }
    const centers=hits.length?hits:[0];
    let parts=[];
    for(const hit of centers.slice(0,2)){
      const start=Math.max(0,hit-3),end=Math.min(entry.lines.length,hit+8);
      parts.push(entry.lines.slice(start,end).map((line,index)=>String(start+index+1)+': '+sanitize(line)).join('\n'));
    }
    const excerpt='\nFILE '+entry.file+' (excerpt; not complete source)\n'+parts.join('\n…\n')+'\n';
    if(result.length+excerpt.length>MAX_CONTEXT)break;
    result+=excerpt;
  }
  return result.slice(0,MAX_CONTEXT);
}
