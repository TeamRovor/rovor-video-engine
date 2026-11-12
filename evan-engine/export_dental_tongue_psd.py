"""Separate dental construction planes; not a full or native Moho character rig."""
from pathlib import Path
import cv2,numpy as np,json,hashlib,argparse
from PIL import Image
from psd_tools import PSDImage
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
from rooted_floor_cartoon_head import RootedFloorCartoonHead
from cartoon_head import POINTS
from layered_cartoon_head import straight,over
cv2.setNumThreads(1);h=DrawnDentalCartoonHead();h.dental_fraction=1;w=np.eye(9)[8]
blade,floor=h.tongue_parts(w,POINTS['H']);teeth=RootedFloorCartoonHead.teeth_surface(h,w,POINTS['H']);alpha=teeth[:,:,3];ys=np.arange(512,dtype=np.float32)[:,None];bottom=np.max(np.where(alpha>=127.5,ys,-1000),axis=0);edge=np.clip((ys-(bottom[None,:]-1.5))/1.5,0,1)*(alpha/255);front=blade*edge[:,:,None]
parts=[('dental-tip-back',blade),('tongue-floor',floor),('upper-incisors',teeth),('dental-tip-front-contact',front)];psd=PSDImage.frompil(Image.new('RGBA',(512,512)));expected=np.zeros((512,512,4),np.float32)
for n,a in parts:
 raw=np.clip(straight(a),0,255).astype('uint8');psd.create_pixel_layer(Image.fromarray(raw),name=n);v=raw.astype(np.float32);v[:,:,:3]*=v[:,:,3:4]/255;expected=over(expected,v)
parser=argparse.ArgumentParser(description='Export four actual dental construction planes in H source space, before lip masking.');parser.add_argument('output',type=Path);args=parser.parse_args();p=args.output;p.parent.mkdir(parents=True,exist_ok=True);out=p.parent;psd.save(p);again=PSDImage.open(p);assert [a.name for a in again]==[n for n,_ in parts];im=again.composite(ignore_preview=True).convert('RGBA');im.save(p.with_suffix('.png'));actual=np.asarray(im).astype(np.float32);actual[:,:,:3]*=actual[:,:,3:4]/255;error=abs(actual-expected);local=expected[:,:,3]>0;assert error.mean()<.1
report=dict(layers=[n for n,_ in parts],geometry='H source, full dental lift, before lip/interior masks',canvas=[512,512],globalMeanPremultipliedError255=float(error.mean()),localSupportMeanPremultipliedError255=float(error[local].mean()),registeredTipSha256=hashlib.sha256(Path('evan-character/cartoon-v1/dental-tongue-v1/tip.png').read_bytes()).hexdigest(),animationReady=False,limits='Four actual construction planes; front contact derived from same dental drawing and lower tooth edge. Not a full head/character or native Moho project; runtime oral mesh/masks/voice timing remain separate.')
(p.with_suffix('.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
