// Owner-private, outbound-only OmniRoute chat relay.
// Browser token submits bounded prompts; the Mac's separate writer token claims them.
// All prompts/replies live temporarily in private D1, never in GitHub or public Pages.
import {parseChatRequest} from '../../tools/hud_chat.mjs';

export const RELAY = Object.freeze({
  heartbeatMs: 45000, queuedMs: 90000, runningMs: 120000,
  retainMs: 10 * 60000, maxModels: 100, maxReplyChars: 16000,
});
const MODEL = /^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,199}$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const query = (db, sql, ...args) => db.prepare(sql).bind(...args).first();
const write = (db, sql, ...args) => db.prepare(sql).bind(...args).run();

export function cleanCatalog(value) {
  if (!Array.isArray(value?.models) || value.models.length > RELAY.maxModels ||
      value.models.some(v => typeof v !== 'string' || !MODEL.test(v)))
    throw Error('invalid_chat_catalog');
  return [...new Set(value.models)];
}
export function cleanReply(value) {
  if (value?.state === 'failed' && ['chat_upstream_failed','chat_upstream_unavailable',
      'chat_rate_limited','model_not_available','response_too_large'].includes(value.error))
    return {state:'failed', output:null, error:value.error};
  if (value?.state !== 'complete' || typeof value.output !== 'string' ||
      !value.output.trim() || value.output.length > RELAY.maxReplyChars)
    throw Error('invalid_chat_result');
  return {state:'complete', output:value.output, error:null};
}
export async function catalog(db, now) {
  const found = await query(db, 'SELECT updated_at, models FROM hud_chat_bridge WHERE id = 1');
  if (!found || found.updated_at > now + 5000 || now - found.updated_at > RELAY.heartbeatMs)
    return {online:false, models:[], last_seen_at:found?.updated_at ?? null};
  try {
    return {online:true, models:cleanCatalog({models:JSON.parse(found.models)}), last_seen_at:found.updated_at};
  } catch {
    return {online:false, models:[], last_seen_at:found.updated_at};
  }
}
export async function publishCatalog(db, value, now) {
  const models = cleanCatalog(value);
  await write(db, 'INSERT INTO hud_chat_bridge (id,updated_at,models) VALUES (1,?,?) ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at, models=excluded.models',
    now, JSON.stringify(models));
  return {accepted:true, count:models.length};
}
export async function enqueue(db, value, now, newId = () => crypto.randomUUID()) {
  const available = await catalog(db, now);
  if (!available.online || !available.models.length) return {status:503, error:'omniroute_offline'};
  let request;
  try { request = parseChatRequest(JSON.stringify(value), available.models); }
  catch (e) { return {status:400, error:e.message === 'model_not_available' ? 'model_not_available' : 'invalid_chat'}; }
  const load = await query(db, "SELECT COUNT(*) AS n FROM hud_chat_jobs WHERE state IN ('queued','running') AND created_at >= ?", now - RELAY.runningMs);
  if ((load?.n || 0) >= 3) return {status:429, error:'chat_busy'};
  const recent = await query(db, 'SELECT COUNT(*) AS n FROM hud_chat_jobs WHERE created_at >= ?', now - 60000);
  if ((recent?.n || 0) >= 12) return {status:429, error:'chat_rate_limited'};
  const id = newId();
  if (!UUID.test(id)) throw Error('invalid_chat_job_id');
  await write(db, "INSERT INTO hud_chat_jobs(id,state,model,request_body,created_at) VALUES (?,'queued',?,?,?)",
    id, request.model, JSON.stringify(request), now);
  return {status:202, job_id:id, state:'queued', requested_model:request.model};
}
export async function claim(db, now) {
  await write(db, "UPDATE hud_chat_jobs SET state='failed',error='relay_timeout',request_body=NULL,finished_at=? WHERE (state='queued' AND created_at < ?) OR (state='running' AND started_at < ?)",
    now, now-RELAY.queuedMs, now-RELAY.runningMs);
  await write(db, 'DELETE FROM hud_chat_jobs WHERE finished_at IS NOT NULL AND finished_at < ?', now-RELAY.retainMs);
  const found = await query(db, "UPDATE hud_chat_jobs SET state='running',started_at=? WHERE id=(SELECT id FROM hud_chat_jobs WHERE state='queued' AND created_at >= ? ORDER BY created_at LIMIT 1) AND state='queued' RETURNING id,model,request_body",
    now, now-RELAY.queuedMs);
  if (!found) return {job:null};
  const request=JSON.parse(found.request_body);
  return {job:{id:found.id,model:found.model,request}};
}
export async function finish(db, id, value, now) {
  if (!UUID.test(id)) return {status:400, error:'invalid_job_id'};
  let result;
  try { result=cleanReply(value); } catch { return {status:400, error:'invalid_chat_result'}; }
  const saved=await write(db, "UPDATE hud_chat_jobs SET state=?,output=?,error=?,finished_at=?,request_body=NULL WHERE id=? AND state='running' AND started_at >= ?",
    result.state,result.output,result.error,now,id,now-RELAY.runningMs);
  return saved?.meta?.changes===1 ? {status:200, accepted:true} : {status:409,error:'claim_expired'};
}
export async function status(db,id,now) {
  if (!UUID.test(id)) return {status:400,error:'invalid_job_id'};
  const found=await query(db,'SELECT state,model,output,error,created_at,started_at FROM hud_chat_jobs WHERE id=?',id);
  if (!found) return {status:404,error:'job_not_found'};
  const expired=(found.state==='queued'&&now-found.created_at>RELAY.queuedMs)||
    (found.state==='running'&&now-found.started_at>RELAY.runningMs);
  return {status:200,state:expired?'failed':found.state,requested_model:found.model,
    output:!expired&&found.state==='complete'?found.output:null,
    error:expired?'relay_timeout':found.error||null,model_attribution:'requested_model_only'};
}
