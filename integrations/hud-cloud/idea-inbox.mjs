// Owner-private Ask ROVOR idea inbox. A queue receipt is not an AI job or
// approval to start inference, create GitHub branches, or spend model quota.
const MAX_TEXT=1600;
const MAX_PER_DAY=30;
const COOLDOWN_MS=5000;
const DAY_MS=86400000;
const invalid=()=>({status:400,body:{error:'invalid_idea'}});
export function validateIdea(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||
    Object.keys(value).length!==1||typeof value.text!=='string')return null;
  const text=value.text.trim();
  if(text.length<8||text.length>MAX_TEXT||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))return null;
  // Reject common pasted credential forms; user must not put secrets in ideas.
  if(/-----BEGIN [A-Z ]*PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9_]{20,}|\bsk-[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._~+/-]{20,}/i.test(text))return null;
  return text;
}
export async function submitIdea(db,body,now=Date.now(),uuid=()=>crypto.randomUUID()){
  const content=validateIdea(body);
  if(!content||!Number.isSafeInteger(now)||now<=0)return invalid();
  const day=Math.floor(now/DAY_MS);
  let reservation;
  try{
    reservation=await db.prepare(`INSERT INTO hud_idea_intake_limits(day_id,submissions,last_at)
      VALUES (?,1,?) ON CONFLICT(day_id) DO UPDATE SET
      submissions=hud_idea_intake_limits.submissions+1,last_at=excluded.last_at
      WHERE hud_idea_intake_limits.submissions<? AND
            hud_idea_intake_limits.last_at<=? RETURNING submissions`)
      .bind(day,now,MAX_PER_DAY,now-COOLDOWN_MS).first();
  }catch{return {status:503,body:{error:'idea_inbox_unavailable'}};}
  if(!reservation)return {status:429,body:{error:'idea_inbox_rate_limited'}};
  const id=uuid();
  if(typeof id!=='string'||!/^[a-f0-9-]{36}$/i.test(id))
    return {status:503,body:{error:'idea_inbox_unavailable'}};
  try{
    await db.prepare(`INSERT INTO hud_idea_inbox(id,created_at,content,state,source)
      VALUES (?,?,?,'pending_review','ask_rovor')`).bind(id,now,content).run();
    return {status:202,body:{id,state:'pending_review',queued:true,
      owner_review_required:true,model_call_started:false,mac_required:false}};
  }catch{return {status:503,body:{error:'idea_inbox_unavailable'}};}
}
export async function listIdeas(db){
  try{
    const result=await db.prepare(`SELECT id,created_at,content,state,source FROM hud_idea_inbox
      ORDER BY created_at DESC,id DESC LIMIT 20`).bind().all();
    return {status:200,body:{source:'private_rovor_idea_inbox',
      execution_authorized:false,mac_required:false,
      items:(result.results||[]).map(row=>({id:row.id,created_at:new Date(row.created_at).toISOString(),
        text:row.content,state:row.state,source:row.source}))}};
  }catch{return {status:503,body:{error:'idea_inbox_unavailable'}};}
}
