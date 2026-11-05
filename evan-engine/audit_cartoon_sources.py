"""Report source geometry/mattes without pretending source art is a working rig."""
import argparse,json
from pathlib import Path
import numpy as np
from PIL import Image

SYMBOLS='XABCDEFGH'
def audit_setup(path):
    im=Image.open(path).convert('RGBA');a=np.asarray(im)[:,:,3]
    yy,xx=np.where(a>=128)
    if not len(xx):raise ValueError('Setup has no visible character')
    box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
    border=np.concatenate((a[0],a[-1],a[:,0],a[:,-1]))
    return dict(file=path.name,size=list(im.size),silhouetteBox=box,
                visibleFraction=round(float((a>=128).mean()),5),
                translucentEdgeFraction=round(float(((a>0)&(a<128)).mean()),5),
                borderMaxAlpha=int(border.max()),
                clearFrame=bool(border.max()<128),stage='source-study',animationReady=False)

def audit_atlas(path):
    im=Image.open(path).convert('RGB');a=np.asarray(im)
    # Only measure the source, do not alter color or replace artist mouth pixels.
    background=(a[:,:,0]>180)&(a[:,:,1]<100)&(a[:,:,2]>160)
    import cv2
    h,w=background.shape;cells=[]
    count,labels,stats,centers=cv2.connectedComponentsWithStats((~background).astype('uint8'),8)
    parts=[(stats[i],centers[i]) for i in range(1,count) if stats[i,4]>2000]
    parts.sort(key=lambda item:(int(item[1][1]//(h/3)),item[1][0]))
    if len(parts)!=9:raise ValueError(f'Expected nine isolated head drawings, found {len(parts)}')
    for i,symbol in enumerate(SYMBOLS):
        box,center=parts[i];x,y,bw,bh,area=map(int,box)
        cells.append(dict(symbol=symbol,foregroundBox=[x,y,x+bw,y+bh],
                          center=[round(float(v),2) for v in center],area=area))
    return dict(file=path.name,size=list(im.size),background='magenta key source',cells=cells,
                stage='unregistered-source',animationReady=False,
                requiredReview=['upper-face registration','jaw/lip landmarks','FV lower-lip contact','L tongue placement','head silhouette drift'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('setup',type=Path);p.add_argument('output',type=Path);p.add_argument('--atlas',type=Path);a=p.parse_args()
    report={'setup':audit_setup(a.setup)}
    if a.atlas:report['atlas']=audit_atlas(a.atlas)
    a.output.write_text(json.dumps(report,indent=2))
