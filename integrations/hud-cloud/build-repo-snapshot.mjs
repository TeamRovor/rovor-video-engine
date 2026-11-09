#!/usr/bin/env node
// Executed only from a reviewed GitHub Actions checkout before Cloudflare deploy.
// Reads fixed tracked Git objects, never working-tree files or arbitrary input.
import {execFileSync} from 'node:child_process';
import {writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,dirname} from 'node:path';
import {REPO_SOURCE_FILES,createRepoSnapshot} from './repo-source.mjs';
const here=dirname(fileURLToPath(import.meta.url));
const root=resolve(here,'../..');
const output=resolve(root,'dashboard/command-center/native-v8-9/rovor-repo-source.json');
const git=(args,maxBuffer=300000)=>execFileSync('git',['-C',root,...args],{
 encoding:'utf8',timeout:5000,maxBuffer,stdio:['ignore','pipe','pipe']
});
export function buildAtCheckout(checkoutSha,resolveHead,readPath){
 if(!/^[a-f0-9]{40}$/.test(checkoutSha||'')||
    checkoutSha!==resolveHead().trim())throw Error('snapshot_not_trusted_checkout');
 return createRepoSnapshot(checkoutSha,readPath);
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
   if(process.argv.length!==2)throw Error('snapshot_no_dynamic_args');
   const head=git(['rev-parse','HEAD']).trim();
   const source=buildAtCheckout(process.env.GITHUB_SHA||head,()=>head,
     path=>{
       if(!REPO_SOURCE_FILES.includes(path))throw Error('source_path_not_allowlisted');
       return git(['show',head+':'+path]);
     });
   writeFileSync(output,JSON.stringify(source));
   console.log('Built private reviewed GitHub source excerpts for '+head+
     ' ('+REPO_SOURCE_FILES.length+' allowlisted files, no token or Mac).');
 }catch{
   console.error('Private GitHub source snapshot build refused.');
   process.exitCode=1;
 }
}
