#!/usr/bin/env node
// Periodic bridge from owner-reviewed private D1 to GitHub PRs.
// NEVER executes model-provided text. Every workflow proposal is compiled from
// a fixed read-only test template. No main writes, merges or model calls.
import {findOwnerPassedProposals} from './cloud_workflow_proposal_bridge.mjs';
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const REPO='TeamRovor/rovor-video-engine';
const run=(command,args,options={})=>execFileSync(command,args,{
 cwd:ROOT,encoding:'utf8',timeout:20000,
 stdio:['ignore','pipe','pipe'],...options
});

function ensureTrustedContext(env){
 if(env.GITHUB_REPOSITORY!==REPO||env.GITHUB_REF!=='refs/heads/main'||
    !['schedule','workflow_dispatch'].includes(env.GITHUB_EVENT_NAME)||
    typeof env.GITHUB_TOKEN!=='string'||env.GITHUB_TOKEN.length<20||
    typeof env.ROVOR_HUD_READER_TOKEN!=='string'||env.ROVOR_HUD_READER_TOKEN.length<32)
  throw Error('trusted_main_credentials_required');
}
export async function publishReviewed({env=process.env,send=fetch,git=run,read=readFileSync,
 write=writeFileSync,mkdir=mkdirSync,exists=existsSync}={}){
 ensureTrustedContext(env);
 const proposals=await findOwnerPassedProposals({readerToken:env.ROVOR_HUD_READER_TOKEN,send});
 if(proposals.length===0)return {state:'no_owner_passed_workflow_proposal',created:0,existing:0};
 let created=0,existing=0;
 for(const item of proposals){
  const rel='coordination/workflow-proposals/'+item.id+'.yml';
  const filename=path.join(ROOT,rel);
  // Even a reviewed model may not choose a non-colliding filename.
  if(exists(filename)){
   if(read(filename,'utf8')!==item.yaml)throw Error('existing_workflow_proposal_conflict');
   existing++;
   continue;
  }
  const branch='rovor/workflow-proposal-'+item.job_id.slice(3,19);
  if(!/^rovor\/workflow-proposal-[a-f0-9]{16}$/.test(branch))
   throw Error('proposal_branch_invalid');
  // Deterministic branch gives at-most-once proposal creation per receipt.
  const remote=git('git',['ls-remote','--heads','origin','refs/heads/'+branch]);
  if(remote){
   // A matching branch name and one PR are not proof that the approved
   // receipt is what that PR proposes. Fail closed on moved or altered refs.
   const branchRef='refs/heads/'+branch;
   const match=/^([a-f0-9]{40})\t(refs\/heads\/[^\s]+)\n?$/.exec(remote);
   if(!match||match[2]!==branchRef)
    throw Error('existing_proposal_branch_unreviewable');
   git('git',['fetch','--no-tags','origin',branchRef]);
   const observed=git('git',['rev-parse','FETCH_HEAD']).trim();
   if(observed!==match[1])throw Error('existing_proposal_branch_unreviewable');
   // Checkout uses a shallow GitHub Actions clone. Trust GitHub's complete
   // PR diff metadata for one-file scope, not a locally missing merge-base.
   if(git('git',['show','FETCH_HEAD:'+rel])!==item.yaml)
    throw Error('existing_proposal_branch_unreviewable');
   const prs=JSON.parse(git('gh',['pr','list','--repo',REPO,'--head',branch,
     '--state','all','--json',
     'number,url,state,baseRefName,headRefName,headRefOid,changedFiles,files',
     '--limit','5']));
   if(!Array.isArray(prs)||prs.length!==1||
      !Number.isInteger(prs[0].number)||prs[0].number<1||
      prs[0].headRefOid!==observed||prs[0].baseRefName!=='main'||
      prs[0].headRefName!==branch||!['OPEN','MERGED'].includes(prs[0].state)||
      prs[0].changedFiles!==1||!Array.isArray(prs[0].files)||
      prs[0].files.length!==1||prs[0].files[0]?.path!==rel||
      typeof prs[0].url!=='string'||
      !prs[0].url.startsWith('https://github.com/'+REPO+'/pull/'))
    throw Error('existing_proposal_branch_unreviewable');
   existing++;
   continue;
  }
  const clean=git('git',['status','--porcelain']);
  if(clean)throw Error('workflow_bridge_worktree_not_clean');
  // Worktree is a disposable, trusted, GitHub-hosted checkout, not the Mac.
  try{
   git('git',['checkout','-b',branch]);
   mkdir(path.dirname(filename),{recursive:true});
   write(filename,item.yaml,{encoding:'utf8',flag:'wx'});
   git('git',['add','--',rel]);
   git('git',['-c','user.name=ROVOR workflow proposer',
     '-c','user.email=rovor-workflow-bot@users.noreply.github.com',
     'commit','-m','Propose validated owner-reviewed workflow '+item.id]);
   git('git',['push','--set-upstream','origin',branch]);
   git('gh',['pr','create','--repo',REPO,'--base','main','--head',branch,
     '--title','ROVOR: owner-reviewed workflow proposal '+item.id,
     '--body','Validated read-only test-workflow proposal compiled from one private D1 Gemini draft.\\n\\n'+
     'Owner review: PASS; SHA-256: '+item.receipt+'; actual model: gemini-3.5-flash-lite.\\n'+
     'This file under coordination/workflow-proposals is NOT active GitHub Actions code.\\n'+
     'Inspect the generated tests and cadence before installing it as .github/workflows/'+item.id+'.yml.\\n'+
     'No code ran from the model output, no paid route, no auto-merge or main edit.']);
   created++;
  }finally{
   git('git',['checkout','--force','main']);
  }
 }
 return {state:created?'reviewed_workflow_proposals_opened':'no_new_proposals',
  created,existing};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))
 publishReviewed().then(x=>console.log('ROVOR workflow bridge '+JSON.stringify(x)))
 .catch(e=>{const code=String(e?.message||'workflow_bridge_unavailable');
  console.error('ROVOR workflow bridge failed: '+
   (/^[a-z0-9_]{5,100}$/.test(code)?code:'workflow_bridge_unavailable'));
  process.exitCode=1;
 });
