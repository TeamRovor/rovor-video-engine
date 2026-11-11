// Independent ROVOR GitHub App. Fixed repository, fixed HTTPS origin,
// least-privilege installation token; never send credentials to a model.
const REPO='TeamRovor/rovor-video-engine';
const API='https://api.github.com';
const numeric=v=>typeof v==='string'&&/^[1-9][0-9]{0,17}$/.test(v);
const enc=new TextEncoder();
const b64url=bytes=>btoa(String.fromCharCode(...new Uint8Array(bytes))).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
const jwtPart=v=>b64url(enc.encode(JSON.stringify(v)));
export function githubAppConfigured(env){
 return numeric(env?.ROVOR_GITHUB_APP_ID)&&numeric(env?.ROVOR_GITHUB_INSTALLATION_ID)&&
   typeof env?.ROVOR_GITHUB_APP_PRIVATE_KEY==='string'&&
   env.ROVOR_GITHUB_APP_PRIVATE_KEY.length>=500&&env.ROVOR_GITHUB_APP_PRIVATE_KEY.length<=10000;
}
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
 const payload=jwtPart({alg:'RS256',typ:'JWT'})+'.'+jwtPart({iat,exp:iat+540,iss:env.ROVOR_GITHUB_APP_ID});
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
export async function mintGithubReadToken(env,now=Date.now(),send=fetch){
 const jwt=await appJwt(env,now);
 const res=await send(API+'/app/installations/'+env.ROVOR_GITHUB_INSTALLATION_ID+'/access_tokens',{
  method:'POST',redirect:'manual',headers:{...headers(jwt),'Content-Type':'application/json'},
  body:JSON.stringify({repositories:['rovor-video-engine'],permissions:{contents:'read',issues:'read',pull_requests:'read',actions:'read'}}),
  signal:AbortSignal.timeout(10000)});
 if(res.status!==201){await res.body?.cancel();throw Error('github_installation_token_denied');}
 const data=await boundedJson(res,30000);
 if(typeof data.token!=='string'||data.token.length<20||data.token.length>1024||
    !Number.isFinite(Date.parse(data.expires_at))||Date.parse(data.expires_at)<=now||
    Date.parse(data.expires_at)>now+3700000||
    !data.permissions||['contents','issues','pull_requests','actions'].some(k=>data.permissions[k]!=='read')||
    Object.values(data.permissions).some(v=>v!=='read')||
    (data.repositories!==undefined&&(!Array.isArray(data.repositories)||data.repositories.length!==1||data.repositories[0]?.full_name!==REPO)))
  throw Error('github_installation_token_scope_invalid');
 return data.token;
}
const routes=Object.freeze({runs:'/actions/runs?status=failure&per_page=8',issues:'/issues?state=open&per_page=8',pulls:'/pulls?state=open&per_page=8'});
export async function readGithubDiscovery(token,send=fetch){
 if(typeof token!=='string'||token.length<20)throw Error('github_installation_token_denied');
 const result=await Promise.all(Object.entries(routes).map(async ([key,path])=>{
  const res=await send(API+'/repos/'+REPO+path,{method:'GET',redirect:'manual',headers:headers(token),signal:AbortSignal.timeout(12000)});
  if(res.status!==200){await res.body?.cancel();throw Error('github_discovery_read_denied');}
  const data=await boundedJson(res);
  const rows=key==='runs'?data?.workflow_runs:data;
  if(!Array.isArray(rows)||rows.length>8)throw Error('github_discovery_response_invalid');
  return [key,rows];
 }));
 return Object.fromEntries(result);
}
