"""Export actual posed body planes before body roll; not native bones/face rig."""
import argparse,json
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from relaxed_cartoon_scene import RelaxedCartoonSceneBody
if __name__=='__main__':
 import cv2
 from pathlib import Path
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--time',type=float,default=748/48);a=p.parse_args();body=RelaxedCartoonSceneBody();plan=json.loads(a.plan.read_text());layers=body.layers(a.time,plan);psd=PSDImage.frompil(Image.new('RGBA',(1464,1536)));expected=Image.new('RGBA',psd.size)
 for name,image in layers.items():psd.create_pixel_layer(image,name=name);expected.alpha_composite(image)
 a.output.parent.mkdir(parents=True,exist_ok=True);psd.save(a.output);opened=PSDImage.open(a.output);assert [l.name for l in opened]==list(layers);actual=opened.composite(force=True,ignore_preview=True).convert('RGBA');bg=Image.new('RGBA',actual.size,'#f3eee2');bg.alpha_composite(actual);bg.convert('RGB').save(a.output.with_suffix('.jpg'),quality=96);x=np.asarray(expected).astype(float);y=np.asarray(actual).astype(float)
 for z in [x,y]:z[:,:,:3]*=z[:,:,3:4]/255
 delta=float(np.abs(x-y).mean());assert delta<1;report=dict(layers=list(layers),meanPremultipliedDifference=delta,sourceTime=a.time,bodyRollApplied=False,head='posed composite only; runtime face components not expanded here',rightHand='part of continuous arm skin; shoulder/elbow/wrist hierarchy in runtime, not PSD bones',nativeMoho=False,animationReady=False);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
