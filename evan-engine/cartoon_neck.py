"""Original-art neck surface: head-following upper end, collar-fixed base.

This is a limited 2D cutout/mesh attachment, not a head turn or anatomy model.
"""
import cv2
import numpy as np
from PIL import Image
from painted_character import rotation

SCALE=.82;TRANSLATE=np.array([285.,-24.],np.float32);PIVOT=[510,343]

def jaw_cut(xx,delta=0):
    y=np.interp(xx,[0,215,220,257,326,342,512],[398,398,400,412,360,345,345])
    follow=np.clip((326-xx)/65,0,1)
    return y+delta*follow

def split_head_neck(image,delta=0,trim_left_stub=False):
    raw=np.asarray(image).copy();yy,xx=np.mgrid[:512,:512];cut=jaw_cut(xx,delta)
    region=(xx>=214)&(xx<=343)&(yy>=335)
    neck_weight=np.clip((yy-cut+6)/2,0,1)*region
    # The extended neck owns the six-pixel original neck fringe below the jaw.
    head_region=region|((xx>=208)&(xx<214)&(yy>=335)) if trim_left_stub else region
    head_weight=np.ones((512,512));head_weight[head_region]=np.clip((cut[head_region]+5-yy[head_region])/3,0,1)
    neck=raw.copy();head=raw.copy();neck[:,:,3]=(raw[:,:,3]*neck_weight).astype('uint8');head[:,:,3]=(raw[:,:,3]*head_weight).astype('uint8')
    return Image.fromarray(head),Image.fromarray(neck)

def neck_vertices(tilt,delta=0,bounds=(208,349),spread=0):
    xs=np.linspace(*bounds,10);ys=np.linspace(330,480,18);source=np.array([(x,y) for y in ys for x in xs],np.float32)
    rest=source*SCALE+TRANSLATE
    if spread:
        widen=np.clip((source[:,1]-380)/25,0,1)
        rest[:,0]=510.5+(rest[:,0]-510.5)*(1+spread*widen)
    # Original short neck is extended underneath the original V-shaped collar.
    u=np.clip((source[:,1]-(420+delta))/(458-(420+delta)),0,1);ease=u*u*(3-2*u)
    rest[:,1]+=35*ease
    moved=(np.c_[rest,np.ones(len(rest))]@rotation(PIVOT,-tilt).T)[:,:2]
    target=moved*(1-ease[:,None])+rest*ease[:,None]
    return source,target

TRIANGLES=[]
for y in range(17):
    for x in range(9):
        a=y*10+x;TRIANGLES.extend([(a,a+1,a+11),(a,a+11,a+10)])

def render_neck(image,tilt,delta=0,bounds=(208,349),spread=0):
    source,target=neck_vertices(tilt,delta,bounds,spread);origin=np.floor(target.min(axis=0)-2).astype(int);end=np.ceil(target.max(axis=0)+2).astype(int);width,height=end-origin
    mx=np.full((height,width),-1,np.float32);my=mx.copy()
    for ids in TRIANGLES:
        src=source[list(ids)];tri=target[list(ids)]-origin;x,y,w,h=cv2.boundingRect(tri.astype('float32'));x=max(0,x);y=max(0,y);w=min(width-x,w);h=min(height-y,h)
        if w<=0 or h<=0:continue
        inv=cv2.getAffineTransform(tri.astype('float32'),src);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32');mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(tri-[x,y]).astype('int32'),255);take=mask>0
        mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take];my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
    raw=np.asarray(image).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255;out=cv2.remap(raw,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);out[:,:,:3]*=255/np.maximum(out[:,:,3:4],1)
    layer=Image.new('RGBA',(1464,1536));layer.alpha_composite(Image.fromarray(np.clip(out,0,255).astype('uint8')),(int(origin[0])+220,int(origin[1])));return layer

def collar_torso(image):
    # Remove original skin and the old chin-shadow fragment, preserving navy
    # collar/tie pixels as the occluding foreground over the new neck.
    raw=np.asarray(image).copy();yy,xx=np.mgrid[:raw.shape[0],:raw.shape[1]]
    skin=(raw[:,:,0]>110)&(raw[:,:,0]>raw[:,:,2]*1.5)&(xx>435)&(xx<578)&(yy<395)&(yy>290)
    old_shadow=(xx>450)&(xx<560)&(yy>=298)&(yy<319)&(raw[:,:,0]>=raw[:,:,2])&(raw[:,:,0]<90)
    # Keep a two-pixel original skin rim as collar overlap. Color-keying the
    # entire antialiased boundary produces pinholes along the blue collar.
    interior=cv2.erode(skin.astype('uint8'),np.ones((5,5),np.uint8))>0
    raw[:,:,3][interior|old_shadow]=0
    return Image.fromarray(raw)
