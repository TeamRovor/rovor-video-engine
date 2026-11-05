"""Register generated jaw/neck source canvases without alpha cleanup.

Run from repository root. Original source files remain unmodified; normalized
native files are review-only derived parts, not approved runtime assets.
"""
import argparse,json,hashlib,cv2,numpy as np
from pathlib import Path
from PIL import Image
cv2.setNumThreads(1);parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('root',type=Path);args=parser.parse_args();root=args.root;rows=[]
for source,name,window in [('jaw-flat-v1.png','Jaw', [128,288,384,448]),('neck-back-v1.png','Neck',[176,320,352,488])]:
 p=root/'source'/source;raw=np.array(Image.open(p).convert('RGBA'));h,w=raw.shape[:2];x0,y0,x1,y1=window;matrix=np.array([[(x1-x0)/w,0,x0],[0,(y1-y0)/h,y0]],np.float32);pm=raw.astype('float32');pm[:,:,:3]*=pm[:,:,3:4]/255
 part=cv2.resize(cv2.warpAffine(pm,matrix*3,(1536,1536),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA);part[:,:,:3]*=255/np.maximum(part[:,:,3:4],1);Image.fromarray(np.rint(np.clip(part,0,255)).astype('uint8')).save(root/(name+'.png'))
 rows.append(dict(source=source,sourceSha256=hashlib.sha256(p.read_bytes()).hexdigest(),sourceSize=[w,h],window=window,matrix=matrix.tolist(),sourceAlphaModified=False))
(root/'registration.json').write_text(json.dumps(dict(parts=rows,registration='fixed canvas normalization, no fit to alpha or source cleanup',animationReady=False),indent=2)+'\n')
