import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const SITE='appgprj_6add1e2cc8c08191839344b34d7dbf50';
const END='export default {fetch: siteFetch};';
const own=path.dirname(fileURLToPath(import.meta.url));
const clean=s=>s.replace(/^import[^\n]*;\s*$/gm,'').replace(/\bexport\s+(?=(?:const|function|async function)\b)/g,'');

export function compileOperations(site,runtime,worker,canary,operations) {
 if(![site,runtime,worker,canary,operations].every(s=>typeof s==='string')||!site.trimEnd().endsWith(END)||site.split(END).length!==2||!site.includes('const siteFetch = createSitesHandler(')||site.includes('ROVOR_CLOUD_OPERATIONS_V1'))throw Error('unexpected_base_site');
 const rt=clean(runtime),wk=clean(worker).replace('export default {','return {'),probe=clean(canary),ops=clean(operations);
 if([rt,probe,ops,wk].some(s=>/^\s*(import|export)\s/m.test(s))||!wk.includes('return {'))throw Error('unsupported_module_shape');
 const hash=createHash('sha256').update([runtime,worker,canary,operations].join('\0')).digest('hex');
 return site.slice(0,site.lastIndexOf(END))+`\n// ROVOR_CLOUD_OPERATIONS_V1 ${hash}\n`+
  `const __cloud = (() => {\n`+
  `const rt = (() => {\n${rt}\nreturn {PROVIDERS,eligibility,tick,validateJob,requestFor};})();\n`+
  `const worker = (() => {const {PROVIDERS,eligibility,tick,validateJob}=rt;\n${wk}\n})();\n`+
  `const canary = (() => {const {PROVIDERS,requestFor}=rt;\n${probe}\nreturn runCanary;})();\n`+
  `return {...rt,worker,canary};})();\n`+
  `const __operations = (() => {\n${ops}\nreturn createCloudOperations(siteFetch,__cloud);})();\n`+
  `export default {fetch:(request,env)=>__operations.fetch(request,env),scheduled(event,env,ctx){if(env.GHOST_CRON_OPT_IN==='owner-approved-ghost-cron-v1')return __cloud.worker.scheduled(event,env,ctx);}};\n`;
}

function safe(root,relative) {
 let current=root;if(fs.lstatSync(root).isSymbolicLink())throw Error('redirected_site');
 for(const part of relative.split('/')){current=path.join(current,part);if(fs.existsSync(current)&&fs.lstatSync(current).isSymbolicLink())throw Error('redirected_site');}
 return current;
}
export function composeOperations(directory,{sourceDirectory=own,apply=false}={}) {
 const root=path.resolve(directory),manifestPath=safe(root,'.openai/hosting.json');
 const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8'));
 if(manifest.project_id!==SITE||!(manifest.d1==='DB'||manifest.d1?.binding==='DB'))throw Error('wrong_site_or_database');
 manifest.d1='DB';
 const source=safe(root,'worker/index.js'),built=safe(root,'dist/server/index.js');
 const base=fs.readFileSync(source,'utf8');if(base!==fs.readFileSync(built,'utf8'))throw Error('site_bundle_mismatch');
 const read=name=>fs.readFileSync(path.join(sourceDirectory,name),'utf8');
 const code=compileOperations(base,read('runtime.mjs'),read('worker.mjs'),read('canary-preflight.mjs'),read('site-operations.mjs'));
 const journalPath=safe(root,'drizzle/meta/_journal.json'),journal=JSON.parse(fs.readFileSync(journalPath,'utf8'));
 if(journal.version!=='7'||journal.dialect!=='sqlite'||!Array.isArray(journal.entries)||journal.entries.some((e,i)=>e.idx!==i||!/^\d{4}_[a-z0-9_]+$/.test(e.tag)||!fs.existsSync(safe(root,'drizzle/'+e.tag+'.sql'))))throw Error('invalid_migration_journal');
 if(journal.entries.length>9999||journal.entries.some(e=>e.tag.endsWith('_cloud_operations')))throw Error('migration_already_present');
 const index=journal.entries.length,tag=String(index).padStart(4,'0')+'_cloud_operations';
 const migrationPath=safe(root,'drizzle/'+tag+'.sql');if(fs.existsSync(migrationPath))throw Error('migration_collision');
 // The hosted migration is schema-only. control() inserts the singleton on
 // explicit owner action; absence defaults to disabled in the existing runtime.
 const schema=read('schema.sql').replace(/^INSERT OR IGNORE INTO ghost_cloud_control[^\n]*\n/m,'')+
  '\nCREATE TABLE IF NOT EXISTS ghost_cloud_reviews (id TEXT PRIMARY KEY,attempt_id TEXT NOT NULL UNIQUE REFERENCES ghost_cloud_attempts(id),actor TEXT NOT NULL,verdict TEXT NOT NULL CHECK(verdict IN (\'passed\',\'failed\')),output_sha256 TEXT NOT NULL,reviewed_at INTEGER NOT NULL);\n';
 if(/(^|\n)\s*(INSERT|UPDATE|DELETE|DROP|ALTER)\b/i.test(schema))throw Error('non_schema_migration');
 const migration=(schema+'\nCREATE TABLE IF NOT EXISTS ghost_cloud_provider_checks(provider TEXT PRIMARY KEY,observed_at INTEGER NOT NULL,status TEXT NOT NULL,error_category TEXT);\n').replace(/;[ \t]*\n/g,';\n--> statement-breakpoint\n');
 journal.entries.push({idx:index,version:'6',when:Date.now(),tag,breakpoints:true});
 if(apply){
  fs.writeFileSync(migrationPath,migration,{flag:'wx'});
  fs.writeFileSync(journalPath,JSON.stringify(journal,null,2)+'\n');
  fs.writeFileSync(manifestPath,JSON.stringify(manifest,null,2)+'\n');
  fs.writeFileSync(safe(root,'dist/.openai/hosting.json'),JSON.stringify(manifest,null,2)+'\n');
  fs.writeFileSync(source,code);fs.writeFileSync(built,code);
 }
 return {project_id:SITE,applied:apply,migration:tag+'.sql',deployment_performed:false,provider_execution_enabled:false};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(!process.argv[2]||process.argv.slice(3).some(v=>v!=='--apply'))throw Error('Usage: compose-operations.mjs EXISTING_SITE [--apply]');
 console.log(JSON.stringify(composeOperations(process.argv[2],{apply:process.argv.includes('--apply')})));
}
