// Private, durable GitHub evidence discovery. This intake is restricted to
// the server-side HUD writer credential and NEVER authorizes an AI job,
// a provider call, a GitHub write, self-approval or a main deployment.
import {validateIdea} from './idea-inbox.mjs';
export const DAILY_AUTOMATED_LIMIT=6;
const DAY=86400000;
const KEY=/^(run|issue|pr)-[1-9][0-9]{0,11}$/;
const denied=(status,error)=>({status,body:{error}});
export function validateDiscovery(value){
  if(!value||typeof value!=='object'||Array.isArray(value)||
     Object.keys(value).sort().join(',')!=='key,priority,text')return null;
  const {key,priority}=value,text=validateIdea({text:value.text});
  if(typeof key!=='string'||!KEY.test(key)||!Number.isInteger(priority)||
     priority<1||priority>100||!text||
     !text.startsWith('[ROVOR-DISCOVERY:'+key+'] '))return null;
  return {key,priority,text};
}
export async function submitDiscovery(db,request,now=Date.now(),uuid=()=>crypto.randomUUID()){
  const value=validateDiscovery(request);
  if(!value||!Number.isSafeInteger(now)||now<1)return denied(400,'invalid_discovery');
  const id=uuid();
  if(typeof id!=='string'||!/^[a-f0-9-]{36}$/i.test(id))
    return denied(503,'discovery_store_unavailable');
  const day=Math.floor(now/DAY);
  try{
    // One atomic D1 statement enforces both the stable unique source key
    // and the global six-per-UTC-day limit across concurrent GitHub runners.
    // A separate daily counter could be consumed without a saved idea.
    const inserted=await db.prepare(`INSERT INTO hud_auto_discovery_inbox
      (id,discovery_key,day_id,created_at,content,priority,state)
      SELECT ?,?,?,?,?,?,'pending_review'
      WHERE (SELECT COUNT(*) FROM hud_auto_discovery_inbox WHERE day_id=?)<?
      ON CONFLICT(discovery_key) DO NOTHING RETURNING id`)
      .bind(id,value.key,day,now,value.text,value.priority,day,DAILY_AUTOMATED_LIMIT).first();
    if(!inserted){
      const duplicate=await db.prepare(`SELECT id FROM hud_auto_discovery_inbox
        WHERE discovery_key=?`).bind(value.key).first();
      if(duplicate)return {status:409,body:{state:'already_recorded',queued:false,
        model_call_started:false,owner_review_required:true}};
      return denied(429,'daily_discovery_budget_reached');
    }
    return {status:202,body:{id,state:'pending_review',queued:true,
      source:'autonomous_discovery',model_call_started:false,
      owner_review_required:true,execution_authorized:false,mac_required:false}};
  }catch{return denied(503,'discovery_store_unavailable');}
}
export async function discoveryStatus(db,now=Date.now()){
  try{
    const day=Math.floor(now/DAY);
    const count=await db.prepare(`SELECT COUNT(*) AS n FROM hud_auto_discovery_inbox
      WHERE day_id=?`).bind(day).first();
    const recent=await db.prepare(`SELECT discovery_key FROM hud_auto_discovery_inbox
      ORDER BY created_at DESC LIMIT 500`).bind().all();
    if(!Number.isSafeInteger(count?.n)||count.n<0)return denied(503,'discovery_store_unavailable');
    return {status:200,body:{source:'private_rovor_discovery',
      execution_authorized:false,mac_required:false,submitted_today:count.n,
      daily_limit:DAILY_AUTOMATED_LIMIT,
      recent_keys:(recent.results||[]).map(x=>x.discovery_key).filter(x=>KEY.test(x)).slice(0,500)}};
  }catch{return denied(503,'discovery_store_unavailable');}
}
