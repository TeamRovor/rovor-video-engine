/** Evidence-gated, read-only OmniRoute provider quota reducer.
 * GET /api/usage/provider-limits is a local cache of provider responses, NOT
 * a guarantee that a provider will accept the next model request. In
 * particular, "used/total" may be credits, not API requests or tokens.
 * Never infer individual-model quota from aggregate request analytics.
 */
const ID=/^[a-zA-Z0-9][a-zA-Z0-9._:/+@-]{0,199}$/;
const safe=x=>typeof x==='string'&&ID.test(x)?x:null;
const amount=x=>Number.isFinite(x)&&x>=0&&x<=1e15?x:null;
function safeTime(x){
  if(typeof x!=='string'&&typeof x!=='number')return null;
  const t=typeof x==='number'?(x<1e11?x*1000:x):Date.parse(x);
  return Number.isFinite(t)&&t>0&&t<Date.UTC(2100,0,1)?t:null;
}
function safeUnit(x){return ['requests','tokens','credits','units','percent'].includes(x)?x:'provider units';}
export function reduceProviderQuota(providers,document,{now=Date.now(),maxAgeMs=90*60000}={}){
  const connections=Array.isArray(providers?.connections)?providers.connections:[];
  const cache=document?.caches;
  const result={source:'omniroute_provider_limits_cache',freshness:'unavailable',
    records:[],counts:{with_limits:0,configured:connections.length},checked_at:new Date(now).toISOString()};
  if(!cache||typeof cache!=='object'||Array.isArray(cache))return result;
  const perProvider=new Map();
  for(const conn of connections){
    const provider=safe(conn?.provider),id=safe(conn?.id);
    if(!provider||!id)continue;
    const slot=(perProvider.get(provider)||0)+1;perProvider.set(provider,slot);
    if(conn.isActive===false)continue;
    const entry=cache[id];
    const at=safeTime(entry?.fetchedAt);
    if(!at||at>now+300000||now-at>maxAgeMs)continue;
    if(!entry?.quotas||typeof entry.quotas!=='object'||Array.isArray(entry.quotas))continue;
    let count=0;
    for(const [model,raw] of Object.entries(entry.quotas)){
      if(count>=120)break;
      const model_id=safe(model);
      if(!model_id||!raw||typeof raw!=='object'||Array.isArray(raw))continue;
      const total=amount(raw.total);
      const used=amount(raw.used);
      if(total===null||total<=0||used===null||used>total)continue;
      const reset=safeTime(raw.resetAt??raw.resetsAt??raw.reset_at);
      // A period that has ended cannot certify today's remaining allowance.
      // Wait for a new cache observation rather than carrying forward stale %.
      if(reset!==null&&reset>=at&&reset<=now)continue;
      result.records.push({provider,account_slot:slot,model_id,used,total,
        remaining:Math.max(0,total-used),used_percent:Math.min(100,100*used/total),
        unit:safeUnit(raw.unit),fetched_at:new Date(at).toISOString(),
        reset_at:reset&&reset>=at?new Date(reset).toISOString():null,
        evidence:'recent_authenticated_local_provider_cache',scope:'model_on_provider_account'});
      count++;
    }
    if(count)result.counts.with_limits++;
  }
  result.freshness=result.records.length?'recent_provider_cache':'no_fresh_supported_limits';
  return result;
}
