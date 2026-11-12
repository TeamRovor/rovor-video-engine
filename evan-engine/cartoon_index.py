"""One independently skinned three-phalange index; remaining digits are drawn."""
import json
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from painted_character import rotation

def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

class IndexRig:
    def __init__(self,root=ROOT):
        self.meta=json.loads((root/'index-rig/manifest.json').read_text());self.joints=np.array(self.meta['joints'],np.float32);self.axis=np.array(self.meta['axis'],np.float32);self.normal=np.array([-self.axis[1],self.axis[0]])
        self.registration=np.vstack([self.meta['registration']['sourceToBody'],[0,0,1]]).astype('float32')
        self.source=np.asarray(Image.open(root/'index-rig/index-source.png').convert('RGBA')).astype('float32');self.source[:,:,:3]*=self.source[:,:,3:4]/255
        ss=np.linspace(-60,480,33);qq=np.linspace(-100,90,9)
        self.vertices=np.array([self.joints[0]+self.axis*s+self.normal*q for s in ss for q in qq],np.float32)
        s=(self.vertices-self.joints[0])@self.axis;d=(self.joints-self.joints[0])@self.axis
        a=smooth((s-d[1]+80)/160);b=smooth((s-d[2]+65)/130);self.weights=np.c_[1-a,a*(1-b),a*b]
        self.triangles=[]
        for y in range(32):
            for x in range(8):
                a=y*9+x;self.triangles.extend([(a,a+1,a+10),(a,a+10,a+9)])
    def matrices(self,angles):
        a=rotation(self.joints[0],angles[0]);b=a@rotation(self.joints[1],angles[1]);c=b@rotation(self.joints[2],angles[2]);return a,b,c
    def posed_vertices(self,angles):
        angles=np.asarray(angles,float)
        if angles.shape!=(3,) or not np.isfinite(angles).all() or np.any(angles<np.array([-10,0,0])-.0001) or np.any(angles>np.array([0,60,35])+.0001):
            raise ValueError('Index angles exceed the inspected construction range')
        v=np.c_[self.vertices,np.ones(len(self.vertices))]
        return sum((v@m.T)[:,:2]*self.weights[:,i:i+1] for i,m in enumerate(self.matrices(angles)))
    def render(self,angles,parent=None,canvas=(1464,1536),pad=220,source_view=False):
        source=self.vertices;posed=self.posed_vertices(angles)
        matrix=np.eye(3) if source_view else (np.eye(3) if parent is None else parent)@self.registration
        target=(np.c_[posed,np.ones(len(posed))]@matrix.T)[:,:2];target[:,0]+=pad
        origin=np.floor(target.min(axis=0)-2).astype(int);end=np.ceil(target.max(axis=0)+2).astype(int);width,height=end-origin
        mx=np.full((height,width),-1,np.float32);my=mx.copy()
        for ids in self.triangles:
            src=source[list(ids)];tri=(target[list(ids)]-origin).astype('float32');x,y,w,h=cv2.boundingRect(tri);x=max(0,x);y=max(0,y);w=min(width-x,w);h=min(height-y,h)
            if w<=0 or h<=0:continue
            inv=cv2.getAffineTransform(tri,src);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32');mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(tri-[x,y]).astype('int32'),255);take=mask>0
            mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take];my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
        raw=cv2.remap(self.source,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);raw[:,:,:3]*=255/np.maximum(raw[:,:,3:4],1)
        out=Image.new('RGBA',canvas);out.alpha_composite(Image.fromarray(np.clip(raw,0,255).astype('uint8')),(int(origin[0]),int(origin[1])));return out
