'use strict';
// Exact official Rovor rover-shaped R mark, preserved from the user's source.
// Rendered as PNG sprites in Sharp; no placeholder R glyphs or remote images.
const fs=require('fs');
const path=require('path');
const sharp=require(process.env.EVAN_SHARP||'sharp');
const ROOT=path.join(__dirname,'..','evan-character','brand');
const cache=new Map();
const clamp=(x,a,b)=>Math.min(b,Math.max(a,x));

async function icon(size,tone='black',opacity=1){
  const a=clamp(Math.round(opacity*10)/10,0,1);
  const key=`${tone}:${size}:${a}`;
  if(cache.has(key)) return cache.get(key);
  const filename=path.join(ROOT,`rovor-mark-${tone}.png`);
  if(!fs.existsSync(filename)) throw new Error('Missing official brand mark: '+filename);
  let buff=await sharp(filename).resize(size,size,{fit:'contain'}).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  const rgba=Buffer.from(buff.data);
  if(a!==1){for(let j=3;j<rgba.length;j+=4)rgba[j]=Math.round(rgba[j]*a);}
  const rendered=await sharp(rgba,{raw:{width:buff.info.width,height:buff.info.height,channels:4}}).png().toBuffer();
  cache.set(key,rendered);
  return rendered;
}
function placements(t,scene){
  // Screen coordinates (720x1280); scene artwork begins at (48,152).
  const output=[{x:43,y:22,size:41,tone:'black',opacity:1}];
  const plan=(scene.scenePlan&&scene.scenePlan.length)?scene.scenePlan:[];
  for(const s of plan){
    if(t<s.start-.24||t>s.end+.24)continue;
    const arriving=clamp((t-s.start+.20)/.40,0,1);
    const leaving=clamp((s.end-t+.20)/.40,0,1);
    const a=Math.min(arriving,leaving);
    if(a<.02)continue;
    const dy=Math.round((1-arriving)*12);
    if(s.kind==='favicon')output.push({x:474,y:239+dy,size:69,tone:'white',opacity:a});
    if(s.kind==='brand')output.push({x:185,y:226+dy,size:56,tone:'black',opacity:a});
    if(s.kind==='endcard')output.push({x:333,y:227+dy,size:60,tone:'white',opacity:a});
  }
  return output;
}
async function putLogos(plate,t,scene){
  const layers=await Promise.all(placements(t,scene).map(async p=>({
    input:await icon(p.size,p.tone,p.opacity),left:p.x,top:p.y
  })));
  return sharp(plate).composite(layers).png().toBuffer();
}
module.exports={icon,placements,putLogos};
