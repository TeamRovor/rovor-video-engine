// Additive orchestration for the EXISTING ROVOR private-Site executor.
// This does not register a cron trigger, enable any model, or mint work packets.
// Hosting owner must invoke runScheduledShift() from exactly one approved trigger.
const OPT_IN = 'owner-approved-ghost-cron-v1';
const DAY = 86400000;
const validCount = (n, max) => Number.isSafeInteger(n) && n >= 0 && n <= max;
const statement = (db, sql, ...args) => db.prepare(sql).bind(...args);

/** Execute one bounded existing cloud work shift, retaining factual receipts. */
export async function runScheduledShift(env, {replenish, tick, clock = Date.now, newId = () => crypto.randomUUID()} = {}) {
  // No DB writes, task assignment, or provider requests without explicit owner opt-in.
  if (env?.GHOST_CRON_OPT_IN !== OPT_IN) return {status: 'not_opted_in', queued: 0, dispatched: 0};
  if (!env.DB || typeof replenish !== 'function' || typeof tick !== 'function') throw Error('shift_not_configured');
  const startedAt = clock();
  if (!Number.isSafeInteger(startedAt) || startedAt < 0) throw Error('invalid_clock');
  const id = newId();
  if (typeof id !== 'string' || !/^[a-z0-9-]{16,64}$/.test(id)) throw Error('invalid_shift_id');
  const db = env.DB;
  await statement(db, "INSERT INTO ghost_cloud_shift_runs(id,started_at,status,queued,duplicates,dispatched) VALUES(? ,?,'running',0,0,0)", id, startedAt).run();
  let queued = 0, duplicates = 0, dispatched = 0, status = 'idle', reason = null;
  try {
    const enabled = await statement(db, 'SELECT enabled FROM ghost_cloud_control WHERE id=1').first();
    if (enabled?.enabled !== 1) {
      status = 'stopped';
    } else {
      // Existing approved packets only. Replayed IDs are deduplicated by the canonical ledger.
      const feed = await replenish(env);
      if (feed?.status === 'stopped') {
        status = 'stopped';
      } else {
        if (!validCount(feed?.queued, 9) || !validCount(feed?.duplicates, 9) || feed.queued + feed.duplicates > 9) throw Error('invalid_feed_receipt');
        queued = feed.queued; duplicates = feed.duplicates;
        // Respect STOP changes between replenishment and model invocation.
        const again = await statement(db, 'SELECT enabled FROM ghost_cloud_control WHERE id=1').first();
        if (again?.enabled !== 1) status = 'stopped';
        else {
          const result = await tick(env);
          if (!validCount(result?.dispatched, 9) || typeof result?.enabled !== 'boolean') throw Error('invalid_tick_receipt');
          dispatched = result.dispatched;
          status = result.enabled ? (dispatched ? 'dispatched' : 'idle') : 'stopped';
          if(status==='idle'){
            // A scheduled wakeup with zero dispatch is not productive work.
            // Diagnose against the durable ledger, not guessed model status.
            const pending=await statement(db,`SELECT COUNT(*) AS n FROM ghost_cloud_jobs j
              WHERE NOT EXISTS(SELECT 1 FROM ghost_cloud_attempts a WHERE a.job_id=j.id)`).first();
            if(!Number.isSafeInteger(pending?.n)||pending.n<0)throw Error('invalid_workload_state');
            const denied=result.denied;
            const allDenied=denied&&typeof denied==='object'&&!Array.isArray(denied)&&
              Object.keys(denied).length===9&&Object.values(denied).every(x=>typeof x==='string'&&x.length>0);
            // The private tick can supply a read-only gate from its actual
            // atomic claim checks. Persist only fixed, public-safe reason
            // codes, never raw config, quotas, prompts or exception strings.
            const safeProviders=new Set(['groq','gemini','cloudflare-ai','mistral','nvidia','openrouter','sambanova','cohere','huggingface']);
            const safeReasons=new Set(['no_matching_unattempted_job','global_daily_safety_cap',
              'account_request_cap','account_reserved_token_cap','account_inflight_claim',
              'account_minimum_interval','account_retry_after',
              'failure_circuit_requires_review','claim_contention_or_unclassified_gate']);
            const reports=result.blocked&&typeof result.blocked==='object'&&!Array.isArray(result.blocked)?
              Object.entries(result.blocked):[];
            let verifiedGate=null;
            if(reports.length===1){
              const [provider,record]=reports[0];
              if(safeProviders.has(provider)&&record&&safeReasons.has(record.reason))
                verifiedGate='claim_'+provider+'_'+record.reason;
            }
            reason=pending.n===0?'no_unattempted_jobs':
              allDenied?'no_eligible_providers':
              verifiedGate||'unattempted_jobs_not_dispatched';
          }
        }
      }
    }
  } catch (error) {
    status = 'failed';
    // Never store exception strings; they may include model output or secrets.
    reason = error?.message === 'invalid_feed_receipt' ? 'invalid_feed_receipt' :
      error?.message === 'invalid_tick_receipt' ? 'invalid_tick_receipt' : 'shift_operation_failed';
  }
  const finishedAt = clock();
  if (!Number.isSafeInteger(finishedAt) || finishedAt < startedAt) throw Error('invalid_clock');
  await statement(db,
    'UPDATE ghost_cloud_shift_runs SET finished_at=?,status=?,queued=?,duplicates=?,dispatched=?,reason=? WHERE id=?',
    finishedAt, status, queued, duplicates, dispatched, reason, id).run();
  // Retain 7 days; historical model attempts live in the separate immutable ledger.
  await statement(db, 'DELETE FROM ghost_cloud_shift_runs WHERE started_at<?', startedAt - 7 * DAY).run();
  return {id, status, started_at: startedAt, finished_at: finishedAt, queued, duplicates, dispatched, reason};
}

/** Bounded, read-only factual scheduler evidence for the existing private HUD. */
export async function readScheduledShifts(env, limit = 20) {
  if (!env?.DB || !validCount(limit, 50) || limit === 0) throw Error('invalid_shift_read');
  const rows = await statement(env.DB,
    'SELECT id,started_at,finished_at,status,queued,duplicates,dispatched,reason FROM ghost_cloud_shift_runs ORDER BY started_at DESC,id DESC LIMIT ?', limit).all();
  return {source: 'cloud_schedule_receipts', observed_at: Date.now(), runs: rows.results};
}
