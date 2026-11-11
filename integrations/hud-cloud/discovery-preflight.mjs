// One independent metadata-only GitHub read before a free model attempt.
// GitHub source bodies, logs, raw issues, code and credentials never enter
// any model prompt. Failure to verify leaves a queued task untouched.
import {githubAppConfigured,mintGithubReadToken,readGithubReviewEvidence} from './github-app.mjs';
const KEY=/^cloud-discovery-((?:run|issue|pr)-[1-9][0-9]{0,11})$/;
const ALLOWED=new Set(['check_failed','newer_check_failed','issue_open','pull_open']);
export async function verifyDiscoveryJobFreshness(env,taskId,now=Date.now(),send=fetch){
 const match=KEY.exec(taskId||'');
 if(!match||!Number.isSafeInteger(now)||now<1||!githubAppConfigured(env))
  return {state:'unavailable'};
 try{
  const token=await mintGithubReadToken(env,now,send);
  const evidence=await readGithubReviewEvidence(token,match[1],send,now);
  return {state:ALLOWED.has(evidence.state)?'actionable':'stale',reason:evidence.state};
 }catch{
  return {state:'unavailable'};
 }
}
