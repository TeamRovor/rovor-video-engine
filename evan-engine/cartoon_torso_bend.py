"""Opt-in upper-body parent with a pelvis-fixed torso transition."""
import cv2
import numpy as np
from PIL import Image
from cartoon_body import CartoonArm
from painted_character import rotation,smooth
from painted_timing import flowing_track
from skeptical_cartoon_review import skeptical_event

PIVOT=(732,730)
CHEST=520

def skeptical_bend(t,plan):
    if not np.isfinite(t):raise ValueError('Expected finite time')
    e=skeptical_event(plan)
    if e is None:return 0.
    return flowing_track(t,[(e['anticipate'],0.),(e['arrive'],-3.),(e['hold'],-3.),(e['settle'],0.)])

class TorsoBend(CartoonArm):
    def __init__(self,image):
        if image.size!=(1464,1536):raise ValueError('Expected registered body canvas')
        super().__init__(image,{})
        self.original=image.copy()
        xs=np.linspace(0,1463,17);ys=np.linspace(0,PIVOT[1],31)
        self.vertices=np.array([(x,y)for y in ys for x in xs],np.float32)
        self.triangles=[]
        for y in range(30):
            for x in range(16):
                a=y*17+x;self.triangles.extend([(a,a+1,a+18),(a,a+18,a+17)])
    def posed_vertices(self,angle):
        if not np.isfinite(angle) or abs(angle)>3:raise ValueError('Expected bounded torso bend within3degrees')
        v=self.vertices
        parent=(np.c_[v,np.ones(len(v))]@rotation(PIVOT,angle).T)[:,:2]
        weight=1-smooth((v[:,1]-CHEST)/(PIVOT[1]-CHEST))
        target=v+(parent-v)*weight[:,None]
        tri=target[np.array(self.triangles)];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
        self.minimum_area2=float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0]))
        if self.minimum_area2<=0:raise ValueError('Folded torso mesh')
        return target
    def bend(self,angle):
        if angle==0:return self.original.copy()
        im,xy=self.render(angle)
        layer=Image.new('RGBA',self.original.size);layer.alpha_composite(im,tuple(xy))
        # The original lower body bypasses resampling at the fixed pelvis.
        layer.paste(self.original.crop((0,PIVOT[1],1464,1536)),(0,PIVOT[1]))
        return layer

def bend_layers(layers,rig,angle):
    rig.posed_vertices(angle)
    if angle==0:return {k:v.copy()for k,v in layers.items()}
    matrix=rotation(PIVOT,angle)[:2];result={}
    for name,im in layers.items():
        if name=='torso':result[name]=rig.bend(angle);continue
        raw=np.asarray(im).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
        moved=cv2.warpAffine(raw,matrix,im.size,flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        moved[:,:,:3]*=255/np.maximum(moved[:,:,3:4],1)
        result[name]=Image.fromarray(np.clip(moved,0,255).astype('uint8'))
    return result
