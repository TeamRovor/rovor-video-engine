'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const html=fs.readFileSync(path.join(root,'native-v8-9','index.html'),'utf8');
const popup=fs.readFileSync(path.join(root,'native-v8-9','workload-popup.js'),'utf8');
const css=fs.readFileSync(path.join(root,'native-v8-9','workload-popup.css'),'utf8');

test('Workload Distribution opens only existing native focus popup, never a new HUD',()=>{
  assert.match(html,/class="workload-open-title" data-view="workload" aria-label="Open Workload Distribution details">WORKLOAD DISTRIBUTION<\/button>/);
  assert.match(html,/class="panel-expand" data-view="workload" title="Expand workload distribution"/);
  assert.match(html,/function renderDrawer\(view\)\{/);
  assert.match(html,/if\(view==='workload'\)\{/);
  assert.match(html,/ROVOR_WORKLOAD\.mount\(host\)/);
  assert.match(html,/d\.addEventListener\('click',\(\)=>open\('workload'\)\)/);
  assert.match(html,/item\.addEventListener\('click',\(\)=>open\('workload'\)\)/);
  assert.match(html,/class="nav" aria-label="Main navigation"/);
  assert.match(html,/R O V O R &nbsp; D I G I T A L/);
  assert.doesNotMatch(html,/data-view="workload"[^>]*class="nav-item"/);
});

test('Popup JavaScript and existing inline HUD script compile',()=>{
  assert.doesNotThrow(()=>new vm.Script(popup,{filename:'workload-popup.js'}));
  const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert.ok(scripts.length>=1,'native inline script exists');
  for(const m of scripts) assert.doesNotThrow(()=>new vm.Script(m[1]));
});

test('Popup defaults to unverified without network, keys or made-up model names',()=>{
  assert.match(html,/src="\.\/workload-popup\.js"/);
  assert.match(html,/href="\.\/workload-popup\.css"/);
  assert.match(popup,/NO VERIFIED LIVE MODEL TELEMETRY/);
  assert.match(popup,/const state=\{view:'matrix',period:'24H',demo:false/);
  assert.match(popup,/Array\.from\(\{length:9\}/);
  assert.match(popup,/EMPLOYEES\.map/);
  assert.match(popup,/VIEW SAMPLE LAYOUT/);
  assert.doesNotMatch(popup,/(fetch\(|XMLHttpRequest|localStorage|sessionStorage|Authorization|Bearer|http:\/\/|https:\/\/)/);
  assert.match(css,/#rovor-workload-popup/);
  assert.doesNotMatch(css,/(^|\n)\s*(html|body|\.hud|\.nav)\s*\{/);
});

test('Popup interaction switches between heatmap, model list, routing and sample mode',()=>{
  let root;
  const context={
    window:{},
    document:{createElement(){root={
      id:'',innerHTML:'',handlers:{},contains(){return true},
      addEventListener(name,fn){this.handlers[name]=fn}
    };return root}},
    Number,Math,Array,Object,String
  };
  vm.runInNewContext(popup,context,{filename:'workload-popup.js'});
  const host={replaceChildren(){},append(node){this.child=node}};
  context.window.ROVOR_WORKLOAD.mount(host);
  assert.match(host.child.innerHTML,/NO VERIFIED LIVE MODEL TELEMETRY/);
  assert.match(host.child.innerHTML,/data-wl-cell="7-8"/);
  const click=host.child.handlers.click;
  const interact=(dataset)=>click({target:{closest(){return{
      dataset,hasAttribute(attr){
        const names={'data-wl-demo':'wlDemo','data-wl-tab':'wlTab','data-wl-period':'wlPeriod','data-wl-employee':'wlEmployee','data-wl-model':'wlModel','data-wl-cell':'wlCell'};
        return Object.prototype.hasOwnProperty.call(dataset,names[attr]);
      }
    }}}});
  interact({wlTab:'models'});
  assert.match(host.child.innerHTML,/ALL NINE MODEL SLOTS/);
  interact({wlDemo:''});
  assert.match(host.child.innerHTML,/DEMONSTRATION — SYNTHETIC NUMBERS/);
  interact({wlTab:'routing'});
  assert.match(host.child.innerHTML,/Conceptual routing diagram/);
  interact({wlDemo:''});
  assert.match(host.child.innerHTML,/NO VERIFIED LIVE MODEL TELEMETRY/);
});

test('An open popup is not reset by unrelated GitHub status refreshes',()=>{
  assert.match(html,/if\(host\.firstElementChild\?\.id !== 'rovor-workload-popup'\)\{/);
  assert.match(popup,/priorLeft=root\.querySelector\?\.\('\.wl-matrix-scroll'\)\?\.scrollLeft/);
  assert.match(popup,/next\.focus\(\{preventScroll:true\}\)/);
  assert.match(css,/\.panel-header \.workload-open-title/);
});
