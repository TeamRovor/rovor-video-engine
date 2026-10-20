'use strict';
const fs=require('fs'),path=require('path');
const sharp=require(process.env.EVAN_SHARP||'sharp');
const {render}=require('./evan_puppet.cjs');
const {renderReference}=require('./evan_reference.cjs');
const [scenePath,directory,startArg,endArg]=process.argv.slice(2);
const data=JSON.parse(fs.readFileSync(scenePath));
const totalFrames=Math.ceil(Number(data.duration)*24);
const start=startArg===undefined?0:Number(startArg);
const end=endArg===undefined?totalFrames:Number(endArg);
if(!Number.isFinite(totalFrames)||totalFrames<1||!Number.isInteger(start)||!Number.isInteger(end)||start<0||start>end||end>totalFrames){
  throw new Error('Invalid frame range or scene duration');
}
fs.mkdirSync(directory,{recursive:true});
(async()=>{
  const deadline=Date.now()+23000;
  let i=start;
  for(;i<end && Date.now()<deadline;i++){
    let target=path.join(directory,String(i).padStart(6,'0')+'.jpg');
    let staging=path.join(directory,String(i).padStart(6,'0')+'.writing.jpg');
    if(data.characterStyle==='reference'){
      fs.writeFileSync(staging,await renderReference(i/24,data));
    }else{
      await sharp(Buffer.from(render(i/24,data))).jpeg({quality:92}).toFile(staging);
    }
    fs.renameSync(staging,target);
  }
  console.log(JSON.stringify({nextFrame:i,totalFrames:end,complete:i===end}));
})().catch(e=>{console.error(e.stack||e);process.exit(1)});

