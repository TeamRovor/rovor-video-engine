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
  assert.match(html,/WORKLOAD DISTRIBUTION<button[^>]*data-view="workload"/);
  assert.match(html,/function renderDrawer\(view\)\{/);
  assert.match(html,/if\(view==='workload'\)\{/);
  assert.match(html,/ROVOR_WORKLOAD\.mount\(host\)/);
  assert.match(html,/ROVOR_WORKLOAD\.mountPreview\(w,/);
  assert.match(html,/if\(!w\.querySelector\('\.wl-compact'\)\)/);
  assert.doesNotMatch(html,/const w=\$\('workloadPanel'\);w\.replaceChildren\(\);if\(ok\)/);
  assert.match(html,/class="nav" aria-label="Main navigation"/);
  assert.match(html,/R O V O R &nbsp; D I G I T A L/);
  assert.doesNotMatch(html,/data-view="workload"[^>]*class="nav-item"/);
});

test('Bundled native script and CSS match reviewable workload sources',()=>{
  assert.ok(html.includes(popup.trim()),'Runtime bundle must contain exact Workload module code');
  // Native HUD retains its own stylesheet; check reviewed scoped selector rules,
  // not a single contiguous CSS blob that may be separated by legacy styles.
  for(const rule of [
    '#rovor-workload-popup{display:flex',
    '#rovor-workload-popup .wl-matrix-scroll',
    '#workloadPanel .wl-compact-row',
    '/* Refine mobile density without altering the original panel size or grid. */'
  ]){
    assert.ok(css.includes(rule),'Reviewable CSS missing '+rule);
    assert.ok(html.includes(rule),'Runtime HUD CSS missing '+rule);
  }
  assert.ok(css.includes('#workloadPanel .wl-compact'));
  assert.ok(css.includes('#rovor-workload-popup .wl-cell'));
});

test('Popup JavaScript and existing inline HUD script compile',()=>{
  assert.doesNotThrow(()=>new vm.Script(popup,{filename:'workload-popup.js'}));
  const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
  assert.ok(scripts.length>=1,'native inline script exists');
  for(const m of scripts) assert.doesNotThrow(()=>new vm.Script(m[1]));
});

test('Popup defaults to unverified without network, keys or made-up model names',()=>{
  assert.ok(!html.includes('src="./workload-popup.js"'));
  assert.ok(!html.includes('href="./workload-popup.css"'));
  assert.match(popup,/NO VERIFIED LIVE MODEL TELEMETRY/);
  assert.match(popup,/demo:false,employee:/);
  assert.match(popup,/Array\.from\(\{length:9\}/);
  assert.match(popup,/EMPLOYEES\.map/);
  assert.match(popup,/VIEW SAMPLE LAYOUT/);
  assert.match(popup,/function mountPreview\(container,openDetails\)/);
  assert.match(popup,/TELEMETRY UNVERIFIED/);
  assert.match(popup,/— UNKNOWN · NOT ZERO/);
  assert.match(css,/#workloadPanel \.wl-compact-row/);
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

test('Compact preview contains nine models, eight named employees, no invented values',()=>{
  const nodes=[];
  const sandbox={window:{},document:{createElement(){const n={
    innerHTML:'',handlers:{},contains(){return true},
    addEventListener(type,fn){this.handlers[type]=fn}
  };nodes.push(n);return n;}},Number,Math,Array,Object,String};
  vm.runInNewContext(popup,sandbox);
  let opened=0;
  const host={replaceChildren(){},append(node){this.child=node}};
  sandbox.window.ROVOR_WORKLOAD.mountPreview(host,()=>opened++);
  assert.equal((host.child.innerHTML.match(/data-wl-compact-row="/g)||[]).length,9);
  assert.match(host.child.innerHTML,/AI MODELS/);
  assert.match(host.child.innerHTML,/TELEMETRY UNVERIFIED/);
  const click=dataset=>host.child.handlers.click({target:{closest(){return{
    dataset,hasAttribute(attr){
      if(attr==='data-wl-compact-tab')return dataset.wlCompactTab!==undefined;
      if(attr==='data-wl-compact-row')return dataset.wlCompactRow!==undefined;
      return false;
    }
  }}}});
  click({wlCompactTab:'employees'});
  assert.equal((host.child.innerHTML.match(/data-wl-compact-row="/g)||[]).length,8);
  assert.match(host.child.innerHTML,/Walter/);
  assert.match(host.child.innerHTML,/Hank/);
  click({wlCompactRow:'2'});
  assert.equal(opened,1);
  sandbox.window.ROVOR_WORKLOAD.mount(host);
  assert.match(host.child.innerHTML,/JANE × MODEL 01/);
});

test('Workload selection survives unrelated refresh remount, resets after popup close',()=>{
  const context={window:{},document:{createElement(){return{
    innerHTML:'',handlers:{},contains(){return true},querySelector(){return null},
    addEventListener(type,fn){this.handlers[type]=fn}
  }}},Number,Math,Array,Object,String};
  vm.runInNewContext(popup,context);
  const host={child:null,replaceChildren(){},append(node){this.child=node},querySelector(){return null}};
  context.window.ROVOR_WORKLOAD.mount(host);
  const click=dataset=>host.child.handlers.click({target:{closest(){return{
    dataset,hasAttribute(attr){
      if(attr==='data-wl-tab')return Object.hasOwn(dataset,'wlTab');
      if(attr==='data-wl-demo')return Object.hasOwn(dataset,'wlDemo');
      return false;
    }
  }}}});
  click({wlTab:'models'});
  assert.equal((host.child.innerHTML.match(/wl-model-entry/g)||[]).length>0,true);
  click({wlDemo:''});
  assert.match(host.child.innerHTML,/DEMONSTRATION — SYNTHETIC NUMBERS/);
  context.window.ROVOR_WORKLOAD.mount(host);
  assert.match(host.child.innerHTML,/ALL NINE MODEL SLOTS/);
  assert.match(host.child.innerHTML,/DEMONSTRATION — SYNTHETIC NUMBERS/);
  context.window.ROVOR_WORKLOAD.resetPopup();
  context.window.ROVOR_WORKLOAD.mount(host);
  assert.match(host.child.innerHTML,/NO VERIFIED LIVE MODEL TELEMETRY/);
  assert.match(host.child.innerHTML,/EMPLOYEE × AI MODEL/);
});
