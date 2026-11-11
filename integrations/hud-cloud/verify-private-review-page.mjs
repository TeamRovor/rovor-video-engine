#!/usr/bin/env node
// Post-deploy private review desk verification. Zero model calls, STOP
// changes, review decisions or client-data disclosure to the GitHub log.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const REQUIRED_ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
export async function verifyPrivateReviewPage({
 origin=REQUIRED_ORIGIN,readerToken,send=fetch,
 expectedHtml,expectedScript
}={}){
 if(origin!==REQUIRED_ORIGIN||typeof readerToken!=='string'||
    readerToken.length<32||readerToken.length>500||/[\r\n]/.test(readerToken))
  throw Error('private_review_deploy_credentials_invalid');
 const get=(pathname,authenticated)=>send(origin+pathname,{
  method:'GET',redirect:'manual',cache:'no-store',
  headers:authenticated?{Authorization:'Bearer '+readerToken}:{},
  signal:AbortSignal.timeout(12000)
 });
 const anonPage=await get('/workforce-review.html',false);
 if(anonPage.status!==303||
    anonPage.headers.get('location')!==origin+'/login?next=%2Fworkforce-review.html')
  throw Error('anonymous_review_redirect_missing');
 const anonScript=await get('/workforce-review.js',false);
 if(anonScript.status!==401)throw Error('anonymous_review_script_exposed');
 const page=await get('/workforce-review.html',true);
 if(page.status!==200)throw Error('review_page_live_http_'+page.status);
 if(page.headers.get('cache-control')!=='no-store')
  throw Error('review_page_no_store_header_missing');
 if(!page.headers.get('content-security-policy')?.includes("script-src 'self'"))
  throw Error('review_page_csp_missing');
 const html=await page.text();
 if(html!==expectedHtml||html.includes('window.ROVOR_START_OMNIROUTE'))
  throw Error('review_page_source_mismatch');
 const script=await get('/workforce-review.js',true);
 if(script.status!==200)throw Error('review_script_private_unavailable');
 const js=await script.text();
 if(js!==expectedScript)throw Error('review_script_source_mismatch');
 return {private_auth_verified:true,anonymous_review_denied:true,
  deployed_html_matches_checkout:true,deployed_review_logic_matches_checkout:true,
  model_calls:0,review_decisions:0};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 verifyPrivateReviewPage({
  readerToken:process.env.ROVOR_HUD_READER_TOKEN,
  expectedHtml:readFileSync(new URL('../../dashboard/command-center/native-v8-9/workforce-review.html',import.meta.url),'utf8'),
  expectedScript:readFileSync(new URL('../../dashboard/command-center/native-v8-9/workforce-review.js',import.meta.url),'utf8')
 }).then(result=>console.log(JSON.stringify(result))).catch(error=>{
  const message=String(error?.message||'private_review_verification_failed');
  console.error('Private review page verification FAILED: '+
    (/^[a-z0-9_]{5,120}$/.test(message)?message:'private_review_verification_failed'));
  process.exitCode=1;
 });
}
