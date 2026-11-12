// Isolate the four existing Cloudflare cron lanes without adding a clock,
// changing STOP, creating work, or granting any new model/GitHub authority.
// Discovery still completes before its workforce tick; independent patch and
// catalog work no longer wait for a model call (or vanish if it throws).
const fail=async(fn,code)=>{
 try {await fn();return null;}
 catch{return code;}
};
const safeFailure={
 chat:'scheduled_chat_maintenance_failed',
 discovery:'scheduled_native_discovery_failed',
 workforce:'scheduled_workforce_tick_failed',
 receipt:'scheduled_workforce_receipt_failed',
 patch:'scheduled_github_patch_failed'
};
export async function runCloudScheduledLanes({maintain,discover,workforce,record,refreshCatalogs,patch,clock=Date.now}={}){
 if([maintain,discover,workforce,record,refreshCatalogs,patch,clock].some(fn=>typeof fn!=='function'))
  throw Error('scheduled_lanes_not_configured');
 const work=async()=>{
  const discoveryFailure=await fail(discover,safeFailure.discovery);
  const startedAt=clock();
  let result={status:503,body:{error:'scheduled_workforce_tick_failed',dispatched:0,inference_completed:false}};
  const workforceFailure=await fail(async()=>{result=await workforce(startedAt);},safeFailure.workforce);
  // An interrupted/failed tick is a scheduled wakeup, NOT a model execution.
  // Even on inference failure, persist an honest failed wakeup if possible.
  const receiptFailure=await fail(()=>record(startedAt,Math.max(startedAt,clock()),result),safeFailure.receipt);
  return workforceFailure||receiptFailure||discoveryFailure;
 };
 const outcomes=await Promise.all([
  fail(maintain,safeFailure.chat),
  work(),
  // Provider catalogs are optional GET-only telemetry; failure must not
  // suppress inference or GitHub patch work, as in the prior implementation.
  fail(refreshCatalogs,null),
  fail(patch,safeFailure.patch)
 ]);
 const problem=outcomes.find(code=>code!==null);
 if(problem)throw Error(problem); // Fixed codes only: no secrets/error bodies.
 return {status:'completed'};
}
