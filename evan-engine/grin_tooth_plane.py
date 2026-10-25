"""Registered drawn grin crown for isolated construction review, not speech."""
import json,hashlib,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load
from lower_lip_plane import arch_surface

class GrinToothPlane:
 def __init__(self):
  folder=ROOT/'grin-tooth-isolated-v1';path=folder/'source.png';registration=json.loads((folder/'Registration.json').read_text())
  if hashlib.sha256(path.read_bytes()).hexdigest()!=registration['sourceSha256']:raise ValueError('Grin crown registration/source mismatch')
  self.source=load(path);self.edge=np.asarray(registration['sourceUpperEdge'],np.float32)
  if self.edge.shape!=(9,2) or not np.isfinite(self.edge).all() or np.any(np.diff(self.edge[:,0])<=0):raise ValueError('Expected nine ordered grin crown source points')
 def pose(self,upper):
  arch=np.asarray(upper,np.float32).copy()
  if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine ordered upper lip points')
  # shortcut: 1px burial hides crown border under lip; artist ownership remains unapproved.
  arch[:,1]-=1.
  scale=float((arch[-1,0]-arch[0,0])/(self.edge[-1,0]-self.edge[0,0]))
  return arch_surface(self.source,self.edge,arch,scale)
