// Independent ROVOR GitHub App. Fixed repository, fixed HTTPS origin,
// least-privilege installation token; never send credentials to a model.
const REPO='TeamRovor/rovor-video-engine';
const API='https://api.github.com';
const numeric=v=>typeof v==='string'&&/^[1-9][0-9]{0,17}$/.test(v);
const enc=new TextEncoder();
const b64url=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
const jwtPart=v=>b64url(enc.encode(JSON.stringify(v)));
// Diagnose only the credential category, never its value or exact length.
export function githubAppCredentialIssue(env){
 const id=env?.ROVOR_GITHUB_APP_ID,installation=env?.ROVOR_GITHUB_INSTALLATION_ID,
  key=env?.ROVOR_GITHUB_APP_PRIVATE_KEY;
 if(typeof id!=='string'||!id.trim())return 'github_app_id_missing';
 if(!numeric(id.trim()))return 'github_app_id_must_be_numeric_not_client_id';
 if(typeof installation!=='string'||!installation.trim())return 'github_installation_id_missing';
 if(!numeric(installation.trim()))return 'github_installation_id_must_be_numeric';
 if(typeof key!=='string'||!key.trim())return 'github_private_key_missing';
 const pem=key.trim();
 if(/^SHA256:/i.test(pem)||/^([a-f0-9]{2}:){15,}[a-f0-9]{2}$/i.test(pem))return 'github_private_key_is_fingerprint_not_pem';
 if(pem.length<500||pem.length>10000||
    !/^-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----\s+[A-Za-z0-9+/=\r\n]+\s+-----END \1-----$/.test(pem))
  return 'github_private_key_requires_complete_pem';
 return null;
}
export function githubAppConfigured(env){return githubAppCredentialIssue(env)===null;}
function derLength(n){
 if(n<128)return [n];
 const out=[];while(n){out.unshift(n&255);n>>>=8;}
 return [128|out.length,...out];
}
function pkcs8(pem){
 // GitHub downloads PKCS#1 RSA PEM. WebCrypto accepts PKCS#8; wrap the
 // existing DER key without writing it to disk or requiring Node crypto.
 const m=/^-----BEGIN (RSA PRIVATE KEY|PRIVATE KEY)-----\s+([A-Za-z0-9+/=\r\n]+)\s+-----END \1-----$/.exec(pem.trim());
 if(!m)throw Error('github_app_key_invalid');
 const raw=Uint8Array.from(atob(m[2].replace(/\s/g,'')),c=>c.charCodeAt(0));
 if(raw.length<256||raw.length>7000)throw Error('github_app_key_invalid');
 if(m[1]==='PRIVATE KEY')return raw;
 const body=[2,1,0,48,13,6,9,42,134,72,134,247,13,1,1,1,5,0,4,...derLength(raw.length),...raw];
 return Uint8Array.from([48,...derLength(body.length),...body]);
}
async function appJwt(env,now){
 if(!githubAppConfigured(env))throw Error('github_app_not_configured');
 const key=await crypto.subtle.importKey('pkcs8',pkcs8(env.ROVOR_GITHUB_APP_PRIVATE_KEY),
  {name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['sign']);
 const iat=Math.floor(now/1000)-30;
 const payload=jwtPart({alg:'RS256',typ:'JWT'})+'.'+jwtPart({iat,exp:iat+540,iss:env.ROVOR_GITHUB_APP_ID.trim()});
 return payload+'.'+b64url(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',key,enc.encode(payload)));
}
async function boundedJson(response,max=400000){
 if(!response.body)throw Error('github_response_unavailable');
 const reader=response.body.getReader();let n=0;const chunks=[];
 try{for(;;){const r=await reader.read();if(r.done)break;n+=r.value.byteLength;
  if(n>max)throw Error('github_response_too_large');chunks.push(r.value);}}
 finally{await reader.cancel().catch(()=>{});}
 const all=new Uint8Array(n);let at=0;for(const c of chunks){all.set(c,at);at+=c.length;}
 return JSON.parse(new TextDecoder().decode(all));
}
function headers(token){
 return {Authorization:'Bearer '+token,Accept:'application/vnd.github+json',
  'X-GitHub-Api-Version':'2022-11-28','User-Agent':'ROVOR-Cloud-Executor'};
}
async function mintInstallationToken(env,permissions,now,send){
 const jwt=await appJwt(env,now);
 const res=await send(API+'/app/installations/'+env.ROVOR_GITHUB_INSTALLATION_ID.trim()+'/access_tokens',{
  method:'POST',redirect:'manual',headers:{...headers(jwt),'Content-Type':'application/json'},
  body:JSON.stringify({repositories:['rovor-video-engine'],permissions}),
  signal:AbortSignal.timeout(10000)});
 if(res.status!==201){await res.body?.cancel();throw Error('github_installation_token_denied');}
 const data=await boundedJson(res,30000);
 if(typeof data.token!=='string'||data.token.length<20||data.token.length>1024||
    !Number.isFinite(Date.parse(data.expires_at))||Date.parse(data.expires_at)<=now||
    Date.parse(data.expires_at)>now+3700000||
    !data.permissions||Object.entries(permissions).some(([k,v])=>data.permissions[k]!==v)||
    Object.entries(data.permissions).some(([k,v])=>k==='metadata'?v!=='read':permissions[k]!==v)||
    (data.repositories!==undefined&&(!Array.isArray(data.repositories)||data.repositories.length!==1||data.repositories[0]?.full_name!==REPO)))
  throw Error('github_installation_token_scope_invalid');
 return data.token;
}
export const mintGithubReadToken=(env,now=Date.now(),send=fetch)=>mintInstallationToken(env,
 {contents:'read',issues:'read',pull_requests:'read',actions:'read'},now,send);
export const mintGithubPatchToken=(env,now=Date.now(),send=fetch)=>mintInstallationToken(env,
 {contents:'write',pull_requests:'write'},now,send);
const routes=Object.freeze({runs:'/actions/runs?branch=main&status=failure&per_page=8',successes:'/actions/runs?branch=main&event=push&status=success&per_page=8',issues:'/issues?state=open&per_page=8',pulls:'/pulls?state=open&per_page=8'});
export async function readGithubDiscovery(token,send=fetch){
 if(typeof token!=='string'||token.length<20)throw Error('github_installation_token_denied');
 const result=await Promise.all(Object.entries(routes).map(async ([key,path])=>{
  const res=await send(API+'/repos/'+REPO+path,{method:'GET',redirect:'manual',headers:headers(token),signal:AbortSignal.timeout(12000)});
  if(res.status!==200){await res.body?.cancel();throw Error('github_discovery_read_denied');}
  const data=await boundedJson(res);
  const rows=key==='runs'||key==='successes'?data?.workflow_runs:data;
  if(!Array.isArray(rows)||rows.length>8)throw Error('github_discovery_response_invalid');
  return [key,rows];
 }));
 return Object.fromEntries(result);
}

// Fixed, read-only current metadata for an already recorded review job.
const validEvidenceId=n=>Number.isSafeInteger(n)&&n>0;
const evidenceKey=/^(run|issue|pr)-([1-9][0-9]{0,11})$/;
const titleOf=v=>typeof v==='string'?v.replace(/[\u0000-\u001f\u007f]/g,' ').trim().slice(0,140):'';
async function getEvidenceJSON(token,route,send){
 const res=await send(API+'/repos/'+REPO+route,{method:'GET',redirect:'manual',
  headers:headers(token),signal:AbortSignal.timeout(10000)});
 if(res.status!==200){await res.body?.cancel();throw Error('github_evidence_unavailable');}
 return boundedJson(res);
}
export async function readGithubReviewEvidence(token,key,send=fetch){
 const parsed=evidenceKey.exec(key||'');
 if(!parsed||typeof token!=='string'||token.length<20)throw Error('github_evidence_invalid');
 const [,kind,num]=parsed,id=Number(num);
 if(kind==='run'){
  const run=await getEvidenceJSON(token,'/actions/runs/'+num,send);
  if(run?.id!==id||run.head_branch!=='main'||!['push','workflow_dispatch'].includes(run.event))
   throw Error('github_evidence_invalid');
  const title=titleOf(run.name);
  if(run.conclusion==='success')return {state:'check_passed_now',title,related_id:null};
  if(run.status!=='completed')return {state:'check_in_progress',title,related_id:null};
  if(run.conclusion!=='failure')return {state:'check_other_outcome',title,related_id:null};
  // Manual dispatches may have different inputs; only compare auto pushes.
  if(run.event==='push'&&validEvidenceId(run.workflow_id)&&Number.isFinite(Date.parse(run.created_at))){
   const list=await getEvidenceJSON(token,'/actions/workflows/'+run.workflow_id+'/runs?branch=main&event=push&status=completed&per_page=8',send);
   if(!Array.isArray(list?.workflow_runs)||list.workflow_runs.length>8)throw Error('github_evidence_invalid');
   const next=list.workflow_runs.filter(x=>validEvidenceId(x.id)&&x.id!==id&&x.workflow_id===run.workflow_id&&
    x.head_branch==='main'&&x.event==='push'&&x.status==='completed'&&
    Number.isFinite(Date.parse(x.created_at))&&Date.parse(x.created_at)>Date.parse(run.created_at))
    .sort((a,b)=>Date.parse(b.created_at)-Date.parse(a.created_at)||b.id-a.id)[0];
   if(next?.conclusion==='success')return {state:'newer_check_passed',title,related_id:next.id};
   if(next?.conclusion==='failure')return {state:'newer_check_failed',title,related_id:next.id};
  }
  return {state:'check_failed',title,related_id:null};
 }
 const row=await getEvidenceJSON(token,(kind==='issue'?'/issues/':'/pulls/')+num,send);
 if(row?.number!==id||!['open','closed'].includes(row.state)||(kind==='issue'&&row.pull_request))
  throw Error('github_evidence_invalid');
 const title=titleOf(row.title);
 if(kind==='issue')return {state:row.state==='closed'?'issue_closed':
  Array.isArray(row.assignees)&&row.assignees.length?'issue_assigned':'issue_open',title,related_id:null};
 return {state:row.merged===true?'pull_merged':row.state==='closed'?'pull_closed':'pull_open',title,related_id:null};
}
