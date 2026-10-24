"""Artist-landmark correspondence for whole painted lower-face drawings.

No mouth is procedurally drawn. The mesh moves each drawing's actual lips,
cheeks and chin into corresponding intermediate positions before compositing.
This avoids the doubled lip edges seen in the optical-flow prototype.
"""
import math
import cv2
import numpy as np
# left corner x/y, right corner x/y, outer top/bottom, inner top/bottom, chin.
# Coordinates belong to REGISTERED 418px head plates, not the generated atlas.
GEOMETRY={
 'X':(168,236,228,239,219,248,232,233,302),
 'A':(170,233,226,237,218,243,230,231,302),
 'B':(167,235,231,241,219,256,228,245,304),
 'C':(166,241,232,245,221,267,231,256,308),
 'D':(166,243,234,248,221,279,230,267,314),
 'E':(174,242,217,242,222,260,235,248,307),
 'F':(177,236,214,239,218,255,232,241,304),
 'G':(166,236,229,239,219,245,232,237,303),
 'H':(166,240,231,243,220,262,231,252,307)}

def landmarks(symbol):
    lx,ly,rx,ry,top,bottom,it,ib,chin=GEOMETRY[symbol]
    cx=(lx+rx)/2;radius=(rx-lx)/2
    points=[]
    for inner in (False,True):
        for i in range(16):
            a=i*2*math.pi/16;x=cx+(radius-(4 if inner else 0))*math.cos(a)
            chord=ly+(ry-ly)*(x-lx)/(rx-lx)
            t,b=(it,ib) if inner else (top,bottom)
            # Inner left/right corners lie within a finite one-pixel closed gap.
            if inner:chord=(it+ib)/2+(ry-ly)*.30*math.cos(a)
            y=chord+(b-chord)*math.sin(a) if math.sin(a)>=0 else chord+(chord-t)*math.sin(a)
            points.append((x,y))
    # Outer face boundary and nose stay registered. Chin responds to the pose.
    points.extend([(1,1),(208,1),(416,1),(1,195),(125,195),(165,200),(208,208),(252,202),(300,195),(416,195),
                   (1,260),(135,260),(152,285),(175,chin-7),(205,chin),(246,chin-9),(280,280),(310,260),(416,260),
                   (1,340),(130,340),(200,360),(300,340),(416,340),(1,416),(208,416),(416,416)])
    return np.array(points,dtype='float32')

POINTS={s:landmarks(s) for s in GEOMETRY}
sub=cv2.Subdiv2D((0,0,418,418))
for p in POINTS['X']:sub.insert(tuple(map(float,p)))
TRIANGLES=[]
for tri in sub.getTriangleList().reshape(-1,3,2):
    ids=[int(np.argmin(np.sum((POINTS['X']-p)**2,axis=1))) for p in tri]
    if len(set(ids))==3:TRIANGLES.append(ids)

def triangle_areas(points):
    p=points[np.array(TRIANGLES)];a=p[:,1]-p[:,0];b=p[:,2]-p[:,0]
    return a[:,0]*b[:,1]-a[:,1]*b[:,0]

def warp_painted(image,source,destination):
    mx=np.full((418,418),-1,np.float32);my=mx.copy()
    for ids in TRIANGLES:
        tri=destination[ids];src=source[ids]
        x,y,w,h=cv2.boundingRect(tri);x=max(0,x);y=max(0,y);w=min(418-x,w);h=min(418-y,h)
        if w<=0 or h<=0:continue
        inv=cv2.getAffineTransform(tri,src);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32')
        mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(tri-[x,y]).astype('int32'),255)
        a=mask>0;u=inv[0,0]*xx+inv[0,1]*yy+inv[0,2];v=inv[1,0]*xx+inv[1,1]*yy+inv[1,2]
        mx[y:y+h,x:x+w][a]=u[a];my[y:y+h,x:x+w][a]=v[a]
    raw=image.astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
    return cv2.remap(raw,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)

def interpolate(images,a,b,w):
    target=POINTS[a]*(1-w)+POINTS[b]*w
    first=warp_painted(images[a],POINTS[a],target);second=warp_painted(images[b],POINTS[b],target)
    mix=first*(1-w)+second*w
    # When a closed pose has no oral cavity, its stretched lip texture must not
    # dissolve over an opening. Reveal the PAINTED open cavity inside the same
    # interpolated inner ring; surrounding lips/cheeks still use both drawings.
    da=GEOMETRY[a][7]-GEOMETRY[a][6];db=GEOMETRY[b][7]-GEOMETRY[b][6]
    if min(da,db)<=2 and max(da,db)>4:
        mask=np.zeros((418,418),np.uint8);cv2.fillConvexPoly(mask,np.rint(target[16:32]).astype('int32'),255)
        # Feather one pixel only: no rectangular lip patches or skin painting.
        m=cv2.GaussianBlur(mask,(3,3),.5).astype('float32')[:,:,None]/255
        cavity=first if da>db else second
        mix=mix*(1-m)+cavity*m
    mix[:,:,:3]=np.clip(mix[:,:,:3]*255/np.maximum(mix[:,:,3:4],1),0,255)
    return mix


def blend_drawings(images,weights):
    """Move active drawings to ONE shared anatomy before blending textures."""
    symbols=list(GEOMETRY);weights=np.asarray(weights,dtype='float32')
    if float(weights.max())>1-1e-7:
        return images[symbols[int(weights.argmax())]].astype('float32')
    target=sum(POINTS[s]*float(w) for s,w in zip(symbols,weights))
    mix=np.zeros((418,418,4),np.float32)
    cavity=np.zeros_like(mix);cavity_weight=0.
    for symbol,weight in zip(symbols,weights):
        if weight<1e-5:continue
        warped=warp_painted(images[symbol],POINTS[symbol],target)
        mix+=float(weight)*warped
        if GEOMETRY[symbol][7]-GEOMETRY[symbol][6]>4:
            cavity+=float(weight)*warped;cavity_weight+=float(weight)
    # Blend all open interiors continuously. Selecting a single 'dominant'
    # drawing made teeth/tongue jump when two pose weights crossed each other.
    closed=float(weights[0]+weights[1])
    aperture=float(sum(w*(GEOMETRY[s][7]-GEOMETRY[s][6]) for s,w in zip(symbols,weights)))
    if cavity_weight>1e-5:
        mask=np.zeros((418,418),np.uint8)
        cv2.fillConvexPoly(mask,np.rint(target[16:32]*256).astype('int32'),255,lineType=cv2.LINE_AA,shift=8)
        def soft(x):
            x=np.clip(x,0,1);return x*x*(3-2*x)
        strength=float(soft((closed-.01)/.09)*soft((aperture-1.5)/2))
        m=cv2.GaussianBlur(mask,(3,3),.5).astype('float32')[:,:,None]/255*strength
        mix=mix*(1-m)+(cavity/cavity_weight)*m
    mix[:,:,:3]=np.clip(mix[:,:,:3]*255/np.maximum(mix[:,:,3:4],1),0,255)
    return mix
