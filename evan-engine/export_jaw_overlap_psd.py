"""Actual posed exposure layers, not blank templates or native Moho bones."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from psd_tools import PSDImage
from jaw_overlap_exposure import JawOverlapExposure
from layered_cartoon_head import straight
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--frame',type=int,default=741);a=p.parse_args();r=JawOverlapExposure();plan=json.loads(a.plan.read_text());_,expected,row=r.at(a.frame/48,plan);psd=PSDImage.frompil(Image.new('RGBA',(512,512)))
 for name,part in r.last_parts.items():psd.create_pixel_layer(Image.fromarray(np.rint(np.clip(straight(part),0,255)).astype('uint8')),name=name)
 a.output.parent.mkdir(parents=True,exist_ok=True);psd.save(a.output);opened=PSDImage.open(a.output);assert [l.name for l in opened]==list(r.last_parts)
 actual=opened.composite(force=True,ignore_preview=True).convert('RGBA');x=np.array(expected).astype(float);y=np.array(actual).astype(float)
 for part in [x,y]:part[:,:,:3]*=part[:,:,3:4]/255
 delta=float(np.abs(x-y).mean());assert delta<1
 bg=Image.new('RGBA',(512,512),'#f3eee2');bg.alpha_composite(actual);bg.convert('RGB').save(a.output.with_suffix('.png'));report=dict(layers=[l.name for l in opened],sourceFrame=a.frame,sourceTime=a.frame/48,meanPremultipliedReassemblyDifference=delta,actualPosedLayers=True,upperFace='existing art with authored ownership mask; not newly painted cheek/upper lip surfaces',jawAndLowerLipPaintCombined=True,nativeMohoBones=False,animationReady=False);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
