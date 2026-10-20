'use strict';
// V3: reference-faithful raster characters, using unchanged user-supplied drawings.
// All compositing is local; nothing is transmitted to a remote service.
const fs = require('fs');
const path = require('path');
const sharp = require(process.env.EVAN_SHARP || 'sharp');
const {renderScene} = require('./scene_graphics.cjs');
const {wrapCaption} = require('./caption_utils.cjs');
const root=path.join(__dirname,'..','evan-character','v3-assets');
const clamp=(x,min,max)=>Math.min(max,Math.max(min,x));
const xml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const cache = new Map();
const poses = {
  neutral: {width:476,left:128,top:418},
  point: {width:490,left:113,top:463},
  present: {width:580,left:70,top:458}
};
function activePose(t,scene){
  const gs=scene.gestures||[];
  const seen=kind=>gs.some(g=>g.kind===kind && t>=g.start-.22&&t<g.end+.18);
  if(seen('point')||seen('pinch')) return 'point';
  if(seen('present')||seen('outro')) return 'present';
  return 'neutral';
}
function background(t,scene){
  return `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280" viewBox="0 0 720 1280" font-family="Arial,sans-serif">
    <defs><linearGradient id="paper" x1="0" y1="0" x2=".7" y2="1"><stop stop-color="#f9f6ef"/><stop offset="1" stop-color="#e1e9ed"/></linearGradient></defs>
    <rect width="720" height="1280" fill="url(#paper)"/>
    <circle cx="670" cy="865" r="288" fill="#d7e3ea" opacity=".55"/>
    <text x="46" y="55" font-size="18" font-weight="800" letter-spacing="3" fill="#334d67">ROVOR DIGITAL</text>
    ${renderScene(t,scene)}
  </svg>`;
}
function overlay(t,scene){
  const captions=scene.captions||scene.segments||[];
  let line='';
  for(let i=captions.length-1;i>=0;i--){if(t>=captions[i].start&&t<captions[i].end){line=captions[i].text;break}}
  const lines=wrapCaption(line,34,3);
  const n=Math.max(1,lines.length);
  const y=n>2?1109:1139;
  const labels=lines.map((txt,i)=>`<text x="360" y="${y+32+i*37}" text-anchor="middle" font-size="28" font-weight="800" fill="#fff">${xml(txt)}</text>`).join('');
  const progress=628*clamp(t/scene.duration,0,1);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="1280" font-family="Arial,sans-serif">
    <rect x="34" y="${y-22}" width="652" height="${n>2?143:104}" rx="21" fill="#142840" opacity=".97"/>
    ${labels}
    <rect x="46" y="1251" width="628" height="5" rx="2.5" fill="#becdd8"/>
    <rect x="46" y="1251" width="${progress}" height="5" rx="2.5" fill="#cf9f67"/>
  </svg>`;
}
async function sprite(name,mouth){
  const key=name+'_'+mouth;
  if(cache.has(key)) return cache.get(key);
  let config=poses[name]; if(!config) throw new Error('Unknown pose '+name);
  let src=path.join(root, name+'_'+mouth+'.png'); if(!fs.existsSync(src)) throw new Error('Missing V3 asset '+src);
  let bytes=await sharp(src).resize({width:config.width}).png().toBuffer();
  cache.set(key,bytes);return bytes;
}
async function renderReference(t,scene){
  const pose=activePose(t,scene), cfg=poses[pose];
  const shape=(scene.mouthCues||[]).find(c=>t>=c.start&&t<c.end)?.value || 'X';
  // Rhubarb phoneme categories are mapped to original mouth drawings.
  const mouths={X:'rest',A:'MBP',B:'AE',C:'L',D:'open',E:'O',F:'O',G:'FV',H:'UW'};
  const image=await sprite(pose,mouths[shape]||'rest');
  const bounce=Math.round(3*Math.sin(2.3*t)+2*Math.sin(4*t));
  const drift=Math.round(3*Math.sin(1.2*t));
  return sharp(Buffer.from(background(t,scene)))
    .composite([
      {input:image,left:cfg.left+drift,top:cfg.top+bounce},
      {input:Buffer.from(overlay(t,scene)),left:0,top:0}
    ])
    .jpeg({quality:92})
    .toBuffer();
}
module.exports={renderReference,activePose,background,overlay};
