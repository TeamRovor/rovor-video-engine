"""Export real body pixel layers; joint controls live in the runtime/manifest."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image
from psd_tools import PSDImage
from cartoon_body import CartoonBody

def export(plan,output,gesture=False,time=0,sockets=False,neck=False):
    if gesture or sockets or neck:
        from cartoon_gesture_body import CartoonGestureBody,CartoonSocketBody,CartoonNeckBody,pointing_acting
        body=CartoonNeckBody() if neck else CartoonSocketBody() if sockets else CartoonGestureBody();layers=body.layers(time,plan,pointing_acting(time))
    else:
        body=CartoonBody();layers=body.layers(time,plan,{})
    psd=PSDImage.frompil(Image.new('RGBA',(1464,1536)))
    expected=Image.new('RGBA',psd.size)
    for name,im in layers.items():psd.create_pixel_layer(im,name=name);expected.alpha_composite(im)
    output.parent.mkdir(parents=True,exist_ok=True);psd.save(output)
    opened=PSDImage.open(output)
    if [l.name for l in opened]!=list(layers):raise RuntimeError('PSD layer names changed')
    actual=opened.composite(force=True,ignore_preview=True).convert('RGBA');actual.save(output.with_suffix('.png'))
    # Explicit backdrop prevents hidden RGB under zero alpha misleading review.
    preview=Image.new('RGBA',actual.size,'#e6ede8');preview.alpha_composite(actual);preview.convert('RGB').save(output.with_suffix('.jpg'),quality=96)
    ea=np.asarray(expected).astype(float);aa=np.asarray(actual).astype(float)
    ea[:,:,:3]*=ea[:,:,3:4]/255;aa[:,:,:3]*=aa[:,:,3:4]/255
    delta=np.abs(ea-aa)
    if delta.mean()>1:raise RuntimeError('PSD reassembly differs from runtime')
    return dict(layers=list(layers),meanPixelDifference=float(delta.mean()),nativeMoho=False)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--gesture',action='store_true');p.add_argument('--time',type=float,default=0);p.add_argument('--sockets',action='store_true');p.add_argument('--neck',action='store_true');a=p.parse_args();print(json.dumps(export(json.loads(a.plan.read_text()),a.output,a.gesture,a.time,a.sockets,a.neck)))
