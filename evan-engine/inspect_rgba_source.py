"""Inspect actual source alpha before diagnosing hidden RGB as visible paint.

Source is read only. Opaque composites are safe to view in image previews that
may otherwise display RGB stored underneath zero alpha. No color key/cleanup.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from render_cartoon_head_study import font

def inspect(source,output):
 output.mkdir(parents=True,exist_ok=True);before=hashlib.sha256(source.read_bytes()).hexdigest();im=Image.open(source).convert('RGBA');raw=np.asarray(im);alpha=raw[:,:,3];ys,xs=np.where(alpha>0);box=None if not len(xs) else [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
 result=dict(source=str(source),sourceSha256=before,size=list(im.size),visibleAlphaBox=box,nonzeroAlphaPixels=int(np.count_nonzero(alpha)),opaqueAlphaPixels=int(np.count_nonzero(alpha==255)),hiddenRgbPixelsAtZeroAlpha=int(np.count_nonzero((alpha==0)&np.any(raw[:,:,:3]!=0,axis=2))),sourceModified=False,limits='Hidden RGB is not visible paint. Composites use actual alpha; source pixels and alpha are never changed.')
 sheet=Image.new('RGB',(1600,1100),'#f3eee2');d=ImageDraw.Draw(sheet)
 for x,label,color in [(15,'Actual alpha / light backdrop','#f3eee2'),(545,'Actual alpha / dark backdrop','#405563')]:
  composite=Image.new('RGBA',im.size,color);composite.alpha_composite(im);composite=composite.convert('RGB');sheet.paste(composite.resize((512,512)),(x,60));d.text((x+10,20),label,font=font(22),fill='#253c49')
  if box:
   crop=composite.crop((max(0,box[0]-6),max(0,box[1]-6),min(im.width,box[2]+6),min(im.height,box[3]+6)));crop.thumbnail((500,340));ratio=min(500/crop.width,340/crop.height);crop=crop.resize((round(crop.width*ratio),round(crop.height*ratio)),Image.Resampling.NEAREST);sheet.paste(crop,(x,650))
 mask=Image.fromarray(alpha).convert('RGB');sheet.paste(mask.resize((512,512)),(1075,60));d.text((1090,20),'Alpha only',font=font(22),fill='#253c49');d.text((20,600),'Visible part crop / nearest-pixel enlargement',font=font(25),fill='#253c49');d.text((20,1040),f'Visible alpha box: {box}; zero-alpha RGB is ignored',font=font(23),fill='#253c49');sheet.save(output/'Alpha-Preview.png')
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 (output/'Alpha-Audit.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(inspect(a.source,a.output),indent=2))
