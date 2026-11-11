// ROVOR GitHub workflow factory: only owner-PASS'd exact D1 draft receipts
// can become proposals. Model output is UNTRUSTED DATA and never shell/YAML.
import {createHash} from 'node:crypto';
const ORIGIN='https://rovor-hud-telemetry.rovordigital.workers.dev';
const MODEL='gemini-3.5-flash-lite';
const TASK_ID='cloud-walter-workflow-factory-20261110';
const ALLOWED_TESTS=new Set([
 'tests/test_hud_mobile_drawer_stability.mjs',
 'tests/test_hud_private_review_page.mjs',
 'tests/test_hud_cloud_workforce.mjs',
 'tests/test_hud_gemini_coverage_workflow.mjs',
 'tests/test_ghost_cloud_feed.mjs'
]);
const cleanId=x=>typeof x==='string'&&/^rovor-[a-z0-9](?:[a-z0-9-]{2,54}[a-z0-9])?$/.test(x);
const exactKeys=(obj,keys)=>!!obj&&typeof obj==='object'&&!Array.isArray(obj)&&
 Object.keys(obj).sort().join(',')===keys.slice().sort().join(',');
const digest=x=>createHash('sha256').update(x,'utf8').digest('hex');
const yamlString=x=>JSON.stringify(x);

export function compileReviewedWorkflow(raw,receipt){
 if(typeof raw!=='string'||raw.length>12000)throw Error('untrusted_draft_invalid');
 if(typeof receipt!=='string'||!/^[a-f0-9]{64}$/.test(receipt)||
    digest(raw)!==receipt)throw Error('private_draft_digest_mismatch');
 let data;
 try{data=JSON.parse(raw);}catch{throw Error('workflow_spec_not_json');}
 if(!exactKeys(data,['workflow_id','name','description','template','tests','schedule'])||
    !cleanId(data.workflow_id)||
    typeof data.name!=='string'||!/^ROVOR [A-Za-z0-9 -]{6,64}$/.test(data.name)||
    typeof data.description!=='string'||data.description.length<20||
    data.description.length>175||!/^[- A-Za-z0-9,.()]+$/.test(data.description)||
    data.template!=='node-test'||!['manual','daily','every-4-hours'].includes(data.schedule)||
    !Array.isArray(data.tests)||data.tests.length<1||data.tests.length>5||
    new Set(data.tests).size!==data.tests.length||
    data.tests.some(x=>!ALLOWED_TESTS.has(x)))
  throw Error('workflow_spec_not_allowlisted');
 const schedule=data.schedule==='daily'?'  schedule:\n    - cron: "17 9 * * *"\n':
  data.schedule==='every-4-hours'?'  schedule:\n    - cron: "17 */4 * * *"\n':'';
 const script=data.tests.map(p=>'          node --test '+p).join('\n');
 const yaml=[
  '# ROVOR OWNER-REVIEWED WORKFLOW PROPOSAL; NOT ACTIVE UNTIL INSTALLED.',
  '# Input is validated against a trusted fixed template; no model-provided shell.',
  '# Private D1 owner PASS, verified SHA-256: '+receipt,
  'name: '+yamlString(data.name),
  'on:',
  '  workflow_dispatch:',
  schedule.trimEnd(),
  'permissions:',
  '  contents: read',
  'jobs:',
  '  verify-rovor:',
  '    runs-on: ubuntu-latest',
  '    timeout-minutes: 8',
  '    steps:',
  '      - uses: actions/checkout@v4',
  '        with:',
  '          persist-credentials: false',
  '      - uses: actions/setup-node@v4',
  '        with:',
  '          node-version: "24"',
  '      - name: Validate approved ROVOR project tests',
  '        run: |',
  script,
  ''
 ].filter((x,i)=>i!==6||!!x).join('\n');
 if(yaml.length>4000||!/\bpermissions:\n  contents: read\n/.test(yaml))
  throw Error('workflow_template_invalid');
 return Object.freeze({id:data.workflow_id,name:data.name,description:data.description,
  schedule:data.schedule,tests:Object.freeze([...data.tests]),yaml,receipt});
}

async function getJSON(path,reader,send){
 const result=await send(ORIGIN+path,{method:'GET',redirect:'manual',cache:'no-store',
  headers:{Authorization:'Bearer '+reader,Accept:'application/json'},
  signal:AbortSignal.timeout(12000)});
 if(result.status!==200)throw Error('private_d1_http_'+result.status);
 const text=await result.text();
 if(text.length>100000)throw Error('private_d1_response_oversized');
 try{return JSON.parse(text);}catch{throw Error('private_d1_response_invalid');}
}

export async function findOwnerPassedProposals({readerToken,send=fetch}={}){
 if(typeof readerToken!=='string'||readerToken.length<32||
    readerToken.length>512||/[\r\n]/.test(readerToken))
  throw Error('private_reader_missing');
 const response=await getJSON('/api/hud/workforce/status',readerToken,send);
 if(response.source!=='existing_cloudflare_hud_gemini_workforce'||
    response.mac_required!==false||response.site_review_ledger_synced!==false||
    !Array.isArray(response.items)||response.items.length>50)
  throw Error('wrong_private_review_ledger');
 const matches=response.items.filter(row=>
  row?.task_id===TASK_ID&&row.employee==='Walter'&&
  row.state==='needs_review'&&row.human_review==='passed'&&
  row.actual_model===MODEL&&
  typeof row.output_sha256==='string'&&/^[a-f0-9]{64}$/.test(row.output_sha256)&&
  Number.isSafeInteger(row.reviewed_at)&&row.reviewed_at>0&&
  typeof row.id==='string'&&/^gc-[a-f0-9]{48}$/.test(row.id));
 const proposals=[];
 for(const row of matches.slice(0,3)){
  const verified=await getJSON('/api/hud/workforce/draft/'+row.id,readerToken,send);
  if(verified.id!==row.id||verified.state!=='needs_review'||
     verified.human_review!=='passed'||verified.output_sha256!==row.output_sha256||
     typeof verified.output!=='string')throw Error('private_review_readback_invalid');
  proposals.push({...compileReviewedWorkflow(verified.output,row.output_sha256),job_id:row.id});
 }
 return proposals;
}
