"""Register generated alpha source plate to existing H-space tongue-root anchor.

No repaint, background removal or re-alpha. Preserve generated alpha and sample
premultiplied colors to avoid dark fringes. This produces a separate component.
"""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from layered_cartoon_head import straight

def register(source,destination,width=36,height=34):
 cv2.setNumThreads(1);raw=np.asarray(Image.open(source).convert('RGBA'));alpha=raw[:,:,3];ys,xs=np.where(alpha>=127)
 if not len(xs):raise ValueError('No opaque source component')
 x0,y0,x1,y1=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)
 # Bottom8% silhouette median supplies the short root center, not tip center.
 root_y=y1-1;root_x=float(np.median(xs[ys>=y1-max(2,round((y1-y0)*.08))]))
 sx=width/(x1-x0);sy=height/(y1-y0)
 scaled_size=(round(raw.shape[1]*sx),round(raw.shape[0]*sy))
 sx=scaled_size[0]/raw.shape[1];sy=scaled_size[1]/raw.shape[0]
 offset_x=237-((root_x+.5)*sx-.5);offset_y=354-((root_y+.5)*sy-.5)
 matrix=np.array([[sx,0,offset_x+(sx-1)/2],[0,sy,offset_y+(sy-1)/2]],np.float32)
 premul=raw.astype(np.float32);premul[:,:,:3]*=premul[:,:,3:4]/255
 small=cv2.resize(premul,scaled_size,interpolation=cv2.INTER_AREA)
 art=cv2.warpAffine(small,np.array([[1,0,offset_x],[0,1,offset_y]],np.float32),(512,512),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 Image.fromarray(np.clip(straight(art),0,255).astype('uint8')).save(destination)
 report=dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceBounds=[x0,y0,x1,y1],sourceRoot=[root_x,root_y],rootAnchor=[237,354],targetExtent=[width,height],matrix=matrix.tolist(),sampling='Premultiplied AREA resize then LINEAR subpixel translation; matrix expresses source-pixel-center correspondence.',registeredSha256=hashlib.sha256(destination.read_bytes()).hexdigest(),alphaPolicy='Original alpha retained; premultiplied affine registration only.',animationReady=False,limits='Generated source art separately registered; not a full mouth, anatomical calibration or native Moho rig.')
 destination.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();print(json.dumps(register(a.source,a.destination),indent=2))
