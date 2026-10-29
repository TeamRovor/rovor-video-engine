"""Register two disconnected generated seal marks as separate working layers.

AREA minification of premultiplied pixels; no repaint/background/alpha cleanup.
"""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from layered_cartoon_head import straight

def register(source,folder):
 cv2.setNumThreads(1);raw=np.asarray(Image.open(source).convert('RGBA'));alpha=raw[:,:,3];_,labels,stats,_=cv2.connectedComponentsWithStats((alpha>127).astype('uint8'));parts=sorted([r for r in stats[1:] if r[4]>20],key=lambda r:r[1]);assert len(parts)==2,'Expected separate seam and lower shadow'
 main,shadow=parts;split=int((main[1]+main[3]+shadow[1])/2);seam=raw.copy();seam[split:,:,3]=0;lower=raw.copy();lower[:split,:,3]=0
 xs=np.where(np.any(seam[:,:,3]>127,axis=0))[0];left,right=int(xs.min()),int(xs.max());ly=float(np.median(np.where(seam[:,left:left+2,3]>127)[0]));ry=float(np.median(np.where(seam[:,right-1:right+1,3]>127)[0]));source_corners=np.array([[left,ly],[right,ry]],np.float32);dest=np.array([[194,326],[280,314]],np.float32)
 scale=float(np.linalg.norm(dest[1]-dest[0])/np.linalg.norm(source_corners[1]-source_corners[0]));small_size=(round(raw.shape[1]*scale*2),round(raw.shape[0]*scale*2));sxy=np.array(small_size)/np.array([raw.shape[1],raw.shape[0]]);sc=(source_corners+.5)*sxy-.5
 def transform(corners,target):
  v=corners[1]-corners[0];perp=np.array([-v[1],v[0]])/np.linalg.norm(v);dv=target[1]-target[0];dp=np.array([-dv[1],dv[0]])/np.linalg.norm(dv);return cv2.getAffineTransform(np.array([*corners,corners.mean(axis=0)+perp*20],np.float32),np.array([*target,target.mean(axis=0)+dp*(20*np.linalg.norm(dv)/np.linalg.norm(v))],np.float32))
 matrix=transform(sc,dest*2+.5);folder.mkdir(parents=True,exist_ok=True);reports={}
 yy,xx=np.indices(alpha.shape);a=lower[:,:,3].astype(float);center=np.array([(xx*a).sum()/a.sum(),(yy*a).sum()/a.sum()]);maina=seam[:,:,3].astype(float);maincenter=np.array([(xx*maina).sum()/maina.sum(),(yy*maina).sum()/maina.sum()]);targetcenter=(matrix@np.r_[(maincenter+.5)*sxy-.5,1]+.5)/2-.5;dp=np.array([12,86],float)/np.linalg.norm([12,86]);desired=targetcenter+dp*3
 for name,art in [('seam',seam),('lower-shadow',lower)]:
  premul=art.astype(np.float32);premul[:,:,:3]*=premul[:,:,3:4]/255;small=cv2.resize(premul,small_size,interpolation=cv2.INTER_AREA);m=matrix.copy()
  if name=='lower-shadow':
   old=(m@np.r_[(center+.5)*sxy-.5,1]+.5)/2-.5;m[:,2]+=(desired-old)*2
  posed=cv2.warpAffine(small,m,(1024,1024),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);posed=cv2.resize(posed,(512,512),interpolation=cv2.INTER_AREA);path=folder/(name+'.png');Image.fromarray(np.clip(straight(posed),0,255).astype('uint8')).save(path);reports[name]=dict(placementAt2x=m.tolist(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 report=dict(sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceCorners=source_corners.tolist(),workingCorners=dest.tolist(),sourceHorizontalSplit=split,sourceResize=small_size,workingCanvas=[512,512],shadowOffsetNativePixels=3,parts=reports,animationReady=False,limits='Separate marks from generated source, not a full mouth/jaw rig. Palette/alpha retained; independent shadow placement. No source repaint.')
 (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('folder',type=Path);a=p.parse_args();print(json.dumps(register(a.source,a.folder),indent=2))
