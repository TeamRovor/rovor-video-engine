"""Registered rigid hand drawing for isolated parent-motion review only."""
import json,hashlib,cv2,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load

class ThumbsUpPlane:
 def __init__(self):
  folder=ROOT/'thumbs-up-v1';path=folder/'source.png';self.registration=json.loads((folder/'Registration.json').read_text())
  if hashlib.sha256(path.read_bytes()).hexdigest()!=self.registration['sourceSha256']:raise ValueError('Thumbs-up source/registration mismatch')
  self.source=load(path);r=self.registration;v=np.asarray(r['targetOutwardAxis'],float);scale=r['targetWidth']/np.linalg.norm(np.diff(r['sourceWristGuide'],axis=0))
  self.linear=np.column_stack([[-v[1],v[0]],-v])*scale
 def pose(self,parent):
  parent=np.asarray(parent,float)
  if parent.shape!=(3,3) or not np.isfinite(parent).all() or not np.allclose(parent[2],[0,0,1]) or not np.allclose(parent[:2,:2].T@parent[:2,:2],np.eye(2),atol=1e-6) or np.linalg.det(parent[:2,:2])<=0:raise ValueError('Expected finite proper rigid hand parent')
  r=self.registration;linear=parent[:2,:2]@self.linear;anchor=parent[:2,:2]@r['targetWrist']+parent[:2,2]+[220,0]
  h,w=self.source.shape[:2];corners=(np.array([[0,0],[w,0],[w,h],[0,h]])-r['sourceAnchor'])@linear.T+anchor
  lo=np.maximum(np.floor(corners.min(axis=0)-2),[0,0]);hi=np.minimum(np.ceil(corners.max(axis=0)+2),[1464,1536]);out=np.zeros((1536,1464,4),np.float32)
  if np.any(hi<=lo):return out
  x0,y0=lo.astype(int);x1,y1=hi.astype(int);yy,xx=np.mgrid[:(y1-y0)*3,:(x1-x0)*3]
  offset=np.stack([xx/3+x0-anchor[0],yy/3+y0-anchor[1]],axis=-1);source=offset@np.linalg.inv(linear).T+r['sourceAnchor']
  # Three samples per axis antialias the reduced rotated outline; source alpha is unchanged.
  sampled=cv2.remap(self.source,source[:,:,0].astype('float32'),source[:,:,1].astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  out[y0:y1,x0:x1]=cv2.resize(sampled,(x1-x0,y1-y0),interpolation=cv2.INTER_AREA)
  # shortcut: source matte/seam unapproved; no alpha cleanup or finger articulation.
  return out
