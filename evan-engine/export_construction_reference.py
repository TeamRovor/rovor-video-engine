"""Editable full-head source references, explicitly not a layered facial rig."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from psd_tools import PSDImage
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('construction',type=Path);p.add_argument('reference',type=Path);p.add_argument('output',type=Path);a=p.parse_args();psd=PSDImage.frompil(Image.new('RGBA',(512,512)));images=[('Working reference',Image.open(a.reference).convert('RGBA'))]+[(name+' SOURCE ONLY',Image.open(a.construction/f'{name}-Aligned.png').convert('RGBA')) for name in ['Seal','Release','Rounded']]
 for name,image in images:
  layer=psd.create_pixel_layer(image,name=name);layer.visible=name=='Seal SOURCE ONLY'
 a.output.parent.mkdir(parents=True,exist_ok=True);psd.save(a.output);opened=PSDImage.open(a.output);actual=opened.composite(force=True,ignore_preview=True).convert('RGBA');expected=images[1][1];x=np.asarray(actual).astype(float);y=np.asarray(expected).astype(float)
 for z in [x,y]:z[:,:,:3]*=z[:,:,3:4]/255
 error=float(np.abs(x-y).mean());assert error<1;bg=Image.new('RGBA',(512,512),'#f3eee2');bg.alpha_composite(actual);bg.convert('RGB').save(a.output.with_suffix('.jpg'),quality=96);report=dict(layers=[l.name for l in opened],visible=[l.name for l in opened if l.visible],meanPremultipliedDifference=error,layerType='four full-head construction references, NOT separated mouth/jaw parts',animationReady=False,nativeMoho=False);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
