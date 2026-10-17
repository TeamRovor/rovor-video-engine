"""Experimental cartoon head anatomy interpolation from registered drawings.
Drawn lips/teeth/tongue remain source pixels; no procedural mouth replacement.
"""
from pathlib import Path
import math
import cv2
import numpy as np
from PIL import Image

SIZE=512;SYMBOLS='XABCDEFGH'
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1/head-rig'
# left/right corner xy, outer top/bottom, inner top/bottom, chin.
GEOMETRY={
 'X':(194,326,280,314,311,330,322,323,393),
 'A':(194,325,263,325,318,330,323,324,393),
 'B':(193,329,279,328,318,340,323,334,393),
 'C':(194,326,280,324,315,361,322,355,398),
 'D':(194,326,279,325,313,381,321,373,415),
 'E':(211,341,240,344,320,366,325,360,400),
 'F':(202,327,231,329,315,350,322,332,394),
 'G':(193,327,277,325,315,334,319,325,394),
 'H':(193,325,280,324,312,359,320,352,399)}

def landmarks(symbol):
    lx,ly,rx,ry,top,bottom,it,ib,chin=GEOMETRY[symbol];cx=(lx+rx)/2;r=(rx-lx)/2;pts=[]
    for inner in (False,True):
        for i in range(16):
            angle=i*math.pi/8;c=math.cos(angle);s=math.sin(angle);inset=min(9,r*.35) if inner else 0;x=cx+(r-inset)*c
            cy=(ly+ry)/2
            chord=(cy if ib-it<=2 else (it+ib)/2)+(ry-ly)/2*(1-inset/r)*c if inner else cy+(ry-ly)/2*c
            a,b=((ly+ry)/2-.5,(ly+ry)/2+.5) if inner and ib-it<=2 else (it,ib) if inner else (top,bottom)
            y=chord+(ib-it)/2*s if inner and ib-it>2 else chord+.5*s if inner else chord+(b-chord)*s if s>=0 else chord+(chord-a)*s
            pts.append((x,y))
    pts.extend([(1,1),(256,1),(510,1),(1,280),(150,280),(190,292),(225,301),(270,292),(350,280),(510,280),
                (1,350),(160,340),(181,375),(195,chin-3),(220,chin),(278,chin-22),(328,355),(380,350),(510,350),
                (1,460),(190,460),(250,475),(340,460),(510,460),(1,510),(256,510),(510,510)])
    return np.asarray(pts,np.float32)
POINTS={s:landmarks(s) for s in SYMBOLS}
# Explicit annulus correspondence avoids Delaunay diagonals that flip when
# an open oral cavity collapses to a narrow contact line.
sub=cv2.Subdiv2D((0,0,SIZE,SIZE));outside=list(range(16))+list(range(32,len(POINTS['C'])))
for i in outside:sub.insert(tuple(map(float,POINTS['C'][i])))
TRIANGLES=[]
for tri in sub.getTriangleList().reshape(-1,3,2):
    ids=[int(np.argmin(((POINTS['C']-p)**2).sum(axis=1))) for p in tri]
    if len(set(ids))==3 and cv2.pointPolygonTest(POINTS['C'][:16],tuple(map(float,tri.mean(axis=0))),False)<0:TRIANGLES.append(ids)
def area(points,ids):
    tri=points[ids];a,b=tri[1]-tri[0],tri[2]-tri[0]
    return float(a[0]*b[1]-a[1]*b[0])
for i in range(16):
    j=(i+1)%16
    choices=[[[i,j,16+j],[i,16+j,16+i]],[[i,j,16+i],[j,16+j,16+i]]]
    valid=[pair for pair in choices if all(area(p,ids)>0 for p in POINTS.values() for ids in pair)]
    if not valid:raise ValueError(f'No non-inverting annulus at {i}; recalibrate landmarks')
    TRIANGLES.extend(valid[0])
for i in range(1,15):TRIANGLES.append([16,16+i,16+i+1])

def warp(image,source,target):
    mx=np.full((SIZE,SIZE),-1,np.float32);my=mx.copy()
    for ids in TRIANGLES:
        tri=target[ids];x,y,w,h=cv2.boundingRect(tri);x=max(0,x);y=max(0,y);w=min(SIZE-x,w);h=min(SIZE-y,h)
        if w<=0 or h<=0:continue
        inv=cv2.getAffineTransform(tri,source[ids]);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32')
        mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(tri-[x,y]).astype('int32'),255)
        take=mask>0
        mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take]
        my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
    raw=image.astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
    return cv2.remap(raw,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)

class CartoonHead:
    def __init__(self,root=ROOT):
        self.images={s:np.asarray(Image.open(root/f'head-{s}.png').convert('RGBA')) for s in SYMBOLS}
        self.weight=np.asarray(Image.open(root/'lower-face-weight.png')).astype('float32')[:,:,None]/255
    def weights(self,weights):
        weights=np.asarray(weights,float);weights=weights/weights.sum();target=np.asarray(sum(POINTS[s]*w for s,w in zip(SYMBOLS,weights)),np.float32)
        mix=np.zeros((SIZE,SIZE,4),np.float32);cavity=mix.copy();open_weight=0.
        for s,w in zip(SYMBOLS,weights):
            if w<1e-5:continue
            moved=warp(self.images[s],POINTS[s],target);mix+=w*moved
            if GEOMETRY[s][7]-GEOMETRY[s][6]>4:cavity+=w*moved;open_weight+=w
        if open_weight>1e-5:
            mask=np.zeros((SIZE,SIZE),np.uint8);cv2.fillConvexPoly(mask,np.rint(target[:16]*256).astype('int32'),255,lineType=cv2.LINE_AA,shift=8)
            aperture=sum(w*(GEOMETRY[s][7]-GEOMETRY[s][6]) for s,w in zip(SYMBOLS,weights))
            strength=np.clip((aperture-1)/3,0,1)*np.clip((weights[0]+weights[1])/.1,0,1)
            mask=cv2.dilate(mask,np.ones((5,5),np.uint8))
            m=cv2.GaussianBlur(mask,(3,3),.5)[:,:,None]/255*strength
            mix=mix*(1-m)+(cavity/open_weight)*m
        mix[:,:,:3]=mix[:,:,:3]*255/np.maximum(mix[:,:,3:4],1)
        mix=self.images['X'].astype('float32')*(1-self.weight)+mix*self.weight
        return Image.fromarray(np.clip(mix,0,255).astype('uint8'))
    def at(self,t,plan):
        from speech_planner import planned_weights
        return self.weights(planned_weights(t,plan,plan['fallbackCues']))
