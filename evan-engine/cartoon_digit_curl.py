"""Opt-in partial finger curl from one source; no replacement drawings.

Construction experiment only: in-plane bending does not model a closed fist.
"""
import json
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_index import IndexRig,smooth

class CurlDigit(IndexRig):
 def __init__(self,name,root=ROOT):
  folder=root/'digit-curl-v1';meta=json.loads((folder/'manifest.json').read_text());self.joints=np.array(meta['digits'][name]['joints'],np.float32);tip=np.array(meta['digits'][name]['tip']);self.axis=tip-self.joints[0];self.axis/=np.linalg.norm(self.axis);self.normal=np.array([-self.axis[1],self.axis[0]]);self.registration=np.eye(3,dtype=np.float32)
  self.image=Image.open(folder/(name+'.png')).convert('RGBA');self.source=np.array(self.image,dtype=np.float32);self.source[:,:,:3]*=self.source[:,:,3:4]/255
  ys,xs=np.where(self.source[:,:,3]>0);points=np.c_[xs,ys]-self.joints[0];ss=points@self.axis;qq=points@self.normal
  self.vertices=np.array([self.joints[0]+self.axis*s+self.normal*q for s in np.linspace(ss.min()-3,ss.max()+3,33)for q in np.linspace(qq.min()-3,qq.max()+3,9)],np.float32)
  s=(self.vertices-self.joints[0])@self.axis;d=(self.joints-self.joints[0])@self.axis;m=smooth(s/70);a=smooth((s-d[1]+35)/70);b=smooth((s-d[2]+30)/60);self.weights=np.c_[1-m,m*(1-a),m*a*(1-b),m*a*b]
  self.triangles=[]
  for y in range(32):
   for x in range(8):
    a=y*9+x;self.triangles.extend([(a,a+10,a+1),(a,a+9,a+10)])
 def posed_vertices(self,angles):
  angles=np.asarray(angles,float)
  if angles.shape!=(3,)or not np.isfinite(angles).all()or np.any(abs(angles)>35):raise ValueError('Expected three finite partial-curl angles within35degrees')
  v=np.c_[self.vertices,np.ones(len(self.vertices))]
  posed=sum((v@m.T)[:,:2]*self.weights[:,i:i+1]for i,m in enumerate((np.eye(3),*self.matrices(angles))))
  p=posed[np.array(self.triangles)];v=p[:,1:]-p[:,0,None]
  if np.any(v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]<=0):raise ValueError('Partial curl folds a mesh triangle')
  return posed

class CartoonDigitCurl:
 def __init__(self,root=ROOT):
  self.palm=Image.open(root/'digit-curl-v1/palm-index.png').convert('RGBA');self.digits={name:CurlDigit(name,root)for name in ['middle','ring','little','thumb']}
 def render(self,controls):
  if set(controls)!=set(self.digits):raise ValueError('Expected controls for all four moving digits')
  for name,rig in self.digits.items():rig.posed_vertices(controls[name])
  image=self.palm.copy()
  if not any(np.any(controls[name])for name in self.digits):
   for rig in self.digits.values():image.alpha_composite(rig.image)
   return image
  for name,rig in self.digits.items():image.alpha_composite(rig.render(controls[name],canvas=image.size,pad=0,source_view=True))
  return image
