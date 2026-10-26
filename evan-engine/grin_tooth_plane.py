"""Registered drawn grin crown for isolated construction review, not speech."""
import json,hashlib,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load
from lower_lip_plane import arch_surface

class GrinToothPlane:
 def __init__(self):
  folder=ROOT/'grin-tooth-isolated-v1';path=folder/'source.png';registration=json.loads((folder/'Registration.json').read_text())
  if hashlib.sha256(path.read_bytes()).hexdigest()!=registration['sourceSha256']:raise ValueError('Grin crown registration/source mismatch')
  self.band_guides=np.asarray(registration['halfAlphaEdges'],np.float32)
  self.source=load(path);self.edge=np.asarray(registration['sourceUpperEdge'],np.float32)
  if self.edge.shape!=(9,2) or not np.isfinite(self.edge).all() or np.any(np.diff(self.edge[:,0])<=0):raise ValueError('Expected nine ordered grin crown source points')
 def pose(self,upper):
  arch=np.asarray(upper,np.float32).copy()
  if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine ordered upper lip points')
  # shortcut: 1px burial hides crown border under lip; artist ownership remains unapproved.
  arch[:,1]-=1.
  scale=float((arch[-1,0]-arch[0,0])/(self.edge[-1,0]-self.edge[0,0]))
  return arch_surface(self.source,self.edge,arch,scale)
 def pose_grin_band(self,upper,lower):
  """Postroll-only two-edge registration; caller clips to the actual lumen."""
  import cv2
  upper,lower=[np.asarray(a,np.float32) for a in (upper,lower)]
  for arch in (upper,lower):
   if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine ordered lip points')
  guides=self.band_guides
  if guides.shape!=(9,3) or not np.isfinite(guides).all() or np.any(np.diff(guides[:,0])<=0) or np.any(guides[:,2]<=guides[:,1]):raise ValueError('Expected ordered crown edge pairs')
  # shortcut: upper55% of the held lumen is authored dental depth; never use for speech.
  gap=np.interp(upper[:,0],lower[:,0],lower[:,1])-upper[:,1]
  if np.any(gap<-.01):raise ValueError('Crossed lip arches')
  yy,xx=np.mgrid[:1536,:1536].astype('float32');xx/=3;yy/=3
  sx=guides[0,0]+(xx-upper[0,0])*(guides[-1,0]-guides[0,0])/(upper[-1,0]-upper[0,0])
  top=np.interp(xx,upper[:,0],upper[:,1])-1
  depth=1+.55*np.maximum(0,np.interp(xx,upper[:,0],gap))
  a=np.interp(sx,guides[:,0],guides[:,1]);b=np.interp(sx,guides[:,0],guides[:,2])
  sy=a+(yy-top)*(b-a)/depth
  part=cv2.remap(self.source,sx.astype('float32'),sy.astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  return cv2.resize(part,(512,512),interpolation=cv2.INTER_AREA)
