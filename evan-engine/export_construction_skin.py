"""Two-plane source assemblies, not independently rigged lip/interior parts."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from psd_tools import PSDImage
from cartoon_body import ROOT
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);folder=ROOT/'construction-skin-v1';reports=[]
 for name in ['Seal','Release','Rounded']:
  skin=Image.open(folder/f'{name}-skin.png').convert('RGBA');paint=Image.open(folder/f'{name}-paint.png').convert('RGBA');expected=skin.copy();expected.alpha_composite(paint);psd=PSDImage.frompil(Image.new('RGBA',(512,512)));psd.create_pixel_layer(skin,name='Clean skin source');psd.create_pixel_layer(paint,name='REJECTED trial: combined paint with opacity noise');file=a.output/(name+'-Assembly.psd');psd.save(file);opened=PSDImage.open(file);actual=opened.composite(force=True,ignore_preview=True).convert('RGBA');x=np.array(actual).astype(float);y=np.array(expected).astype(float)
  for z in [x,y]:z[:,:,:3]*=z[:,:,3:4]/255
  error=float(abs(x-y).mean());assert error<1;reports.append(dict(pose=name,layers=[l.name for l in opened],meanPremultipliedDifference=error,independentLipsInterior=False,jawSeparated=False,nativeMoho=False,paintRejectedForRuntime=True))
  sheet=Image.new('RGB',(1600,620),'#f3eee2');d=ImageDraw.Draw(sheet)
  for xpos,label,im in [(15,'Clean skin source',skin),(545,'REJECTED extraction trial',paint),(1075,'Reconstruction, not rig',actual)]:sheet.paste(im,(xpos,65),im);d.text((xpos+10,20),label,font=font(23),fill='#253c49')
  sheet.save(a.output/(name+'-Parts.png'))
 (a.output/'Assembly-Verification.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports))
