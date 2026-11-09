'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=p=>fs.readFileSync(path.join(root,'native-v8-9',p),'utf8');
const html=read('index.html'),source=read('workload-popup.js'),css=read('workload-popup.css');

function runtime() {
  const nodes=[];
  const document={createElement(){
    const node={innerHTML:'',className:'',id:'',handlers:{},isConnected:true,
      contains(){return true},addEventListener(event,handler){this.handlers[event]=handler},
      querySelector(){return null}};
    nodes.push(node);return node;
  }};
  const calls={startCloud:0};
  const context={document,window:{ROVOR_QUOTA_BOARD:{startCloud(){calls.startCloud++}}},
    Number,Array,Object,String,Math};
  vm.runInNewContext(source,context);
  const host={child:null,replaceChildren(){this.child=null},append(node){this.child=node}};
  return {context,host,nodes,calls};
}
function click(root,attrs){
  const attrsObj=attrs;
  root.handlers.click({target:{closest(){return{
    hasAttribute:k=>Object.hasOwn(attrsObj,k),
    getAttribute:k=>attrsObj[k],
  }}}});
}
test('single existing original HUD, bundled reviewed cloud-only Workload sources',()=>{
  assert.match(html,/AI MODELS &amp; QUOTAS<button[^>]*data-view="workload"/);
  assert.match(html,/ROVOR_WORKLOAD\.mount\(host\)/);
  assert.match(html,/ROVOR_WORKLOAD\.mountPreview\(w,/);
  assert.ok(html.includes(source.trim()));
  assert.ok(html.includes(css.trim()));
  assert.doesNotMatch(html,/Paste the private bridge link printed on your Mac/);
  assert.doesNotMatch(html,/LAST MAC REPORT \/ 31 JOB CLAIMS/);
  assert.doesNotMatch(html,/LAST REPORT · HISTORICAL/);
  assert.doesNotMatch(html,/31 PAST CLAIMS/);
  assert.doesNotMatch(html,/sessionStorage\.setItem\(KEY,JSON\.stringify\(\{origin:url\.origin,token:/);
});
test('cloud-first source does not simulate usage, invent worker receipts or poll a local device',()=>{
  assert.doesNotThrow(()=>new vm.Script(source));
  assert.match(source,/CLOUD READBACK/);
  assert.match(source,/No activity will be assumed/);
  assert.match(source,/setCloudSummary/);
  assert.match(source,/PROVIDERS=\[/);
  assert.match(source,/EMPLOYEES=\[/);
  assert.match(css,/#workloadPanel \.wl-compact-row/);
  assert.doesNotMatch(source,/(fetch\(|XMLHttpRequest|localStorage|sessionStorage|Authorization|Bearer|simulatedCounts|VIEW SAMPLE LAYOUT|Mac|pair\/external)/i);
});
test('preview exposes cloud families and eight workers without presenting unavailable quotas as zero',()=>{
  const {context,host}=runtime();
  let opened=0;
  context.window.ROVOR_WORKLOAD.mountPreview(host,()=>opened++);
  assert.match(host.child.innerHTML,/PROVIDERS <small>09/);
  assert.match(host.child.innerHTML,/CLOUD READBACK · CHECKING/);
  assert.match(host.child.innerHTML,/Not verified/);
  assert.doesNotMatch(host.child.innerHTML,/LAST REPORT|31 PAST CLAIMS|100\.0%/);
  assert.equal((host.child.innerHTML.match(/data-cloud-row=/g)||[]).length,4);
  click(host.child,{'data-cloud-tab':'employees'});
  assert.match(host.child.innerHTML,/EMPLOYEES <small>08/);
  assert.match(host.child.innerHTML,/Walter/);
  assert.match(host.child.innerHTML,/Mike/);
  click(host.child,{'data-cloud-row':'0'});assert.equal(opened,1);
  click(host.child,{'data-cloud-open':''});assert.equal(opened,2);
});
test('receipt-derived compact labels remain distinct from a catalog listing',()=>{
  const {context,host}=runtime();
  context.window.ROVOR_WORKLOAD.mountPreview(host,()=>{});
  context.window.ROVOR_WORKLOAD.setCloudSummary({geminiModels:8,geminiVerified:1,
    groqReady:true,privateCloudFresh:false});
  assert.match(host.child.innerHTML,/PRIVATE CLOUD READBACK · NOT VERIFIED/);
  click(host.child,{'data-cloud-tab':'providers'});
  assert.match(host.child.innerHTML,/8 listed · 1 verified/);
  assert.match(host.child.innerHTML,/Cloud configured · receipt required/);
  context.window.ROVOR_WORKLOAD.setCloudSummary({geminiModels:8,geminiVerified:0,
    privateCloudFresh:true});
  assert.match(host.child.innerHTML,/8 listed · 0 verified/);
  assert.match(host.child.innerHTML,/PRIVATE CLOUD READBACK · RECEIVED/);
});
test('full drawer mounts cloud-only loading shell and invokes quota board without any bridge',()=>{
  const {context,host,calls}=runtime();
  context.window.ROVOR_WORKLOAD.mount(host);
  assert.match(host.child.innerHTML,/data-rovor-cloud-placeholder="true"/);
  assert.match(host.child.innerHTML,/Workload Distribution/);
  assert.match(host.child.innerHTML,/Loading authenticated cloud provider/);
  assert.equal(calls.startCloud,1);
  assert.doesNotMatch(host.child.innerHTML,/Mac|OmniRoute|sample|fake|LaunchAgent/);
  context.window.ROVOR_WORKLOAD.resetPopup();
  assert.equal(calls.startCloud,1);
});
