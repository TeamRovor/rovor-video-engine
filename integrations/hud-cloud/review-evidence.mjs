// Private current-source metadata. No inference, review, or repository write.
import {githubAppConfigured,mintGithubReadToken,readGithubReviewEvidence} from './github-app.mjs';
const ID=/^[a-z0-9][a-z0-9-]{0,149}$/;
const KEY=/^cloud-discovery-((?:run|issue|pr)-[1-9][0-9]{0,11})$/;
const TTL=15*60000;
function reply(job,key,row,state){
 return {status:200,body:{source:'rovor_private_review_evidence',job_id:job,source_key:key,
  state:state||row?.result_state||'unavailable',title:row?.source_title||null,
  related_id:row?.related_id??null,finished_at:row?.finished_at??null,
  model_called:false,github_written:false}};
}
export async function reviewEvidence(env,id,now=Date.now(),send=fetch){
 if(!ID.test(id||'')||!Number.isSafeInteger(now)||now<1)return {status:400,body:{error:'invalid_evidence_job'}};
 const db=env.DB;
 try{
  const job=await db.prepare("SELECT task_id FROM hud_cloud_workforce_jobs WHERE id=? AND state='needs_review' AND human_review='not_recorded'").bind(id).first();
  const key=KEY.exec(job?.task_id||'')?.[1];
  if(!key)return {status:404,body:{error:'evidence_job_not_found'}};
  if(!githubAppConfigured(env))return reply(id,key,null,'not_configured');
  const get=()=>db.prepare('SELECT source_key,checked_at,finished_at,result_state,source_title,related_id FROM hud_workforce_review_evidence WHERE job_id=?').bind(id).first();
  const claim=await db.prepare("INSERT INTO hud_workforce_review_evidence(job_id,source_key,checked_at,result_state) VALUES(?,?,?,'checking') ON CONFLICT(job_id) DO UPDATE SET checked_at=excluded.checked_at,finished_at=NULL,result_state='checking',source_title=NULL,related_id=NULL WHERE hud_workforce_review_evidence.source_key=excluded.source_key AND hud_workforce_review_evidence.checked_at<=? RETURNING job_id").bind(id,key,now,now-TTL).first();
  if(!claim){
   const current=await get();
   if(!current||current.source_key!==key)return reply(id,key,null,'unavailable');
   return reply(id,key,current);
  }
  let result={state:'unavailable',title:null,related_id:null};
  try{const token=await mintGithubReadToken(env,now,send);result=await readGithubReviewEvidence(token,key,send);}catch{}
  const end=Math.max(now,Date.now());
  const saved=await db.prepare('UPDATE hud_workforce_review_evidence SET finished_at=?,result_state=?,source_title=?,related_id=? WHERE job_id=? AND source_key=? AND checked_at=?').bind(end,result.state,result.title,result.related_id,id,key,now).run();
  if(saved.meta?.changes!==1)return reply(id,key,null,'unavailable');
  return reply(id,key,{finished_at:end,result_state:result.state,source_title:result.title,related_id:result.related_id});
 }catch{return {status:503,body:{error:'review_evidence_unavailable'}};}
}
