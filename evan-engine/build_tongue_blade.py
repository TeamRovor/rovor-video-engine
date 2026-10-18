"""Register one generated isolated tongue blade without changing the face."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from build_cartoon_heads import affine_rgba
from cartoon_head import POINTS,warp
from layered_cartoon_head import straight

def build(root=ROOT):
    path=root/'tongue-source/blade-v1.png';raw=np.asarray(Image.open(path).convert('RGBA'))
    yy,xx=np.where(raw[:,:,3]>16)
    if len(xx)<100:raise ValueError('Missing opaque tongue source')
    bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
    scale=32/(bounds[3]-bounds[1]);matrix=np.array([[scale,0,237-scale*(bounds[0]+bounds[2])/2],[0,scale,322-scale*bounds[1]]],np.float32)
    registered=affine_rgba(raw,matrix);registered[registered[:,:,3]==0,:3]=0
    folder=root/'tongue-rig';folder.mkdir(exist_ok=True);Image.fromarray(registered).save(folder/'blade.png')
    floor_path=root/'oral-rig/tongue.png';floor=np.asarray(Image.open(floor_path).convert('RGBA')).copy()
    n,labels,stats,_=cv2.connectedComponentsWithStats((floor[:,:,3]>32).astype('uint8'))
    if n<2:raise ValueError('Missing original tongue floor')
    floor[labels!=(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))]=0
    floor=straight(warp(floor,POINTS['C'],POINTS['H'],2)).astype('uint8');floor[floor[:,:,3]==0,:3]=0
    Image.fromarray(floor).save(folder/'root-floor.png')
    report=dict(version=1,sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),isolatedReferenceSha256=hashlib.sha256((root/'tongue-source/isolated-reference.png').read_bytes()).hexdigest(),contextPath='head-rig-v2/head-H.png',contextSha256=hashlib.sha256((root/'head-rig-v2/head-H.png').read_bytes()).hexdigest(),sourceBounds=bounds,matrix=matrix.tolist(),rootAnchor=[237,354],targetTop=322,animationReady=False,rootSourceSha256=hashlib.sha256(floor_path.read_bytes()).hexdigest(),construction='original floor plus generated blade; root fixed, blade compressed/retracted for non-L and lifted from existing acoustic H weight',limitations=['Stylized clear-L target, not calibrated speaker anatomy','No separate dark-L/coda or lateral-airflow geometry','Existing H viseme also serves TH/DH; no separate dental construction','Raster contour and lip construction still need artist review'])
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(build(),indent=2))
