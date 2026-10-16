'use strict';
const fs=require('fs'),path=require('path');
const sharp=require(process.env.EVAN_SHARP||'sharp');
const {render}=require('./evan_puppet.cjs');
const {renderReference}=require('./evan_reference.cjs');
const [scenePath,directory,startArg,endArg]=process.argv.slice(2);
const data=JSON.parse(fs.readFileSync(scenePath));
const start=Number(startArg||0),end=Number(endArg||Math.ceil(data.duration*24));
fs.mkdirSync(directory,{recursive:true});
(async()=>{
  const deadline=Date.now()+23000;
  let i=start;
  for(;i<end && Date.now()<deadline;i++){
    let target=path.join(directory,String(i).padStart(6,'0')+'.jpg');
    let staging=path.join(directory,String(i).padStart(6,'0')+'.writing.jpg');
    if(data.characterStyle==='reference'||data.characterStyle==='calibrated'){
      fs.writeFileSync(staging,await renderReference(i/24,data));
    }else{
      await sharp(Buffer.from(render(i/24,data))).jpeg({quality:92}).toFile(staging);
    }
    fs.renameSync(staging,target);
  }
  console.log(JSON.stringify({nextFrame:i,totalFrames:end,complete:i===end}));
})().catch(e=>{console.error(e.stack||e);process.exit(1)});
