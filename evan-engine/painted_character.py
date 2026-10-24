"""Painted source-art character: registered facial drawings and three-joint arms.

This is a raster mesh rig, not a vector or verified native Moho rig. Joint
transforms are continuous; no whole-character pose swaps or fabricated lips.
"""
import json, math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from painted_face_mesh import interpolate, blend_drawings
from painted_timing import speech_weights, flowing_track

ROOT=Path(__file__).resolve().parent.parent/'evan-character/painted-v1/rig'

def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

def sample_track(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*float(smooth((t-a)/(b-a)))
    return keys[-1][1]

def rotation(pivot,degrees):
    x,y=pivot;a=math.radians(degrees);c,s=math.cos(a),math.sin(a)
    return np.array([[c,-s,x-c*x+s*y],[s,c,y-s*x-c*y],[0,0,1]],dtype='float32')

def arm_transforms(geo,angles):
    upper=rotation(geo['shoulder'],angles[0])
    fore=upper@rotation(geo['elbow'],angles[1])
    hand=fore@rotation(geo['wrist'],angles[2])
    return upper,fore,hand

def skin_vertices(vertices,geo,angles):
    """Continuous skin weights across elbow/wrist, hierarchical FK transforms."""
    v=np.c_[vertices,np.ones(len(vertices))]
    transforms=arm_transforms(geo,angles)
    e=smooth((vertices[:,1]-geo['elbow'][1]+55)/110)
    w=smooth((vertices[:,1]-geo['wrist'][1]+30)/60)
    weights=np.array([1-e,e*(1-w),e*w]).T
    return sum((v@matrix.T)[:,:2]*weights[:,i:i+1] for i,matrix in enumerate(transforms))

class ArmMesh:
    def __init__(self,image,geometry):
        self.image=np.asarray(image).copy();self.geometry=geometry
        bbox=image.getbbox();x0,y0,x1,y1=bbox
        xs=np.linspace(x0-3,x1+3,9);ys=np.linspace(y0-3,y1+3,20)
        self.vertices=np.array([(x,y) for y in ys for x in xs],dtype='float32')
        self.triangles=[]
        for y in range(19):
            for x in range(8):
                a=y*9+x;b=a+1;c=a+9;d=c+1
                self.triangles.extend([(a,b,d),(a,d,c)])

    def posed_vertices(self,angles):
        return skin_vertices(self.vertices,self.geometry,angles)

    def render(self,angles):
        dst=self.posed_vertices(angles)
        x0,y0=np.floor(dst.min(axis=0)-2).astype(int);x1,y1=np.ceil(dst.max(axis=0)+2).astype(int)
        width,height=x1-x0,y1-y0
        mx=np.full((height,width),-1,np.float32);my=mx.copy()
        for ids in self.triangles:
            src=self.vertices[list(ids)];tri=dst[list(ids)]-[x0,y0]
            bx,by,bw,bh=cv2.boundingRect(tri.astype('float32'))
            bx=max(0,bx);by=max(0,by);bw=min(width-bx,bw);bh=min(height-by,bh)
            if bw<=0 or bh<=0:continue
            inv=cv2.getAffineTransform(tri.astype('float32'),src)
            yy,xx=np.mgrid[by:by+bh,bx:bx+bw].astype('float32')
            mask=np.zeros((bh,bw),np.uint8)
            cv2.fillConvexPoly(mask,np.rint(tri-[bx,by]).astype('int32'),255)
            u=inv[0,0]*xx+inv[0,1]*yy+inv[0,2];v=inv[1,0]*xx+inv[1,1]*yy+inv[1,2]
            a=mask>0;mx[by:by+bh,bx:bx+bw][a]=u[a];my[by:by+bh,bx:bx+bw][a]=v[a]
        out=cv2.remap(self.image,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        return Image.fromarray(out),(int(x0),int(y0))

class PaintedCharacter:
    def __init__(self,root=ROOT):
        self.root=Path(root);self.meta=json.loads((self.root/'manifest.json').read_text())
        self.torso=Image.open(self.root/'torso.png').convert('RGBA')
        self.heads={s:np.asarray(Image.open(self.root/f'head-{s}.png').convert('RGBA')).copy() for s in self.meta['face_order']}
        self.weight=np.asarray(Image.open(self.root/'lower-face-weight.png')).astype('float32')[:,:,None]/255
        self.arms={n:ArmMesh(Image.open(self.root/f'arm-{n}.png').convert('RGBA'),g) for n,g in self.meta['arms'].items()}
        self.face_cache={}

    def face(self,a,b,amount):
        amount=max(0,min(1,amount));key=(a,b,round(amount,6))
        if key in self.face_cache:return self.face_cache[key].copy()
        w=key[2]
        if a==b or w<=0:mix=self.heads[a].astype('float32')
        elif w>=1:mix=self.heads[b].astype('float32')
        else:mix=interpolate(self.heads,a,b,w)
        # Identical hair/sunglasses/nose every frame. Entire cheeks/lips/chin
        # below this feathered boundary use the registered painted pose.
        raw=self.heads['X'].astype('float32')*(1-self.weight)+mix*self.weight
        im=Image.fromarray(np.clip(raw,0,255).astype('uint8'))
        self.face_cache[key]=im
        return im.copy()

    def speaking_face(self,t,cues,plan=None):
        from speech_planner import planned_weights
        weights=planned_weights(t,plan,cues) if plan else speech_weights(t,cues)
        raw=blend_drawings(self.heads,weights)
        raw=self.heads['X'].astype('float32')*(1-self.weight)+raw*self.weight
        return Image.fromarray(np.clip(raw,0,255).astype('uint8'))

    def render(self,t,cues,controls=None,speech_plan=None):
        controls=controls or {};pad=220
        canvas=Image.new('RGBA',(1464,1536))
        canvas.alpha_composite(self.torso,(pad,0))
        for name,arm in self.arms.items():
            angles=controls.get(name,(0,0,0));im,(x,y)=arm.render(angles)
            canvas.alpha_composite(im,(x+pad,y))
        head=self.speaking_face(t,cues,speech_plan)
        trans=self.meta['head_transform'];scale=trans['scale'];head=head.resize((round(418*scale),round(418*scale)),Image.Resampling.LANCZOS)
        layer=Image.new('RGBA',canvas.size);x,y=trans['translate'];layer.alpha_composite(head,(x+pad,y))
        tilt=controls.get('head',0)
        if tilt:layer=layer.rotate(tilt,Image.Resampling.BICUBIC,center=(trans['pivot'][0]+pad,trans['pivot'][1]))
        canvas.alpha_composite(layer)
        # Whole upper-body follow-through around the hips connects the head and
        # hands to a breathing, weight-bearing torso instead of a fixed statue.
        roll=controls.get('body_roll',0.)
        if roll:canvas=canvas.rotate(roll,Image.Resampling.BICUBIC,center=(755,965))
        return canvas
