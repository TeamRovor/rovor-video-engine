"""One drawn lip plane with independent pressure and a caller-supplied arch.

Source alpha is preserved. Pressure compresses lip thickness below its contact
edge; it does not change jaw, teeth, upper lip or timing. Review-only artwork.
"""
import json,cv2,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load

class LowerLipPlane:
 def __init__(self):
  folder=ROOT/'lower-lip-pressure-v1';self.source=load(folder/'Lower-Lip-Candidate.png');self.edge=np.asarray(json.loads((folder/'Registration.json').read_text())['sourceTopEdge'],np.float32)
 def pose(self,arch,pressure):
  arch=np.asarray(arch,dtype=np.float32)
  if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine finite arch points ordered left to right')
  if not np.isfinite(pressure) or not 0<=pressure<=1:raise ValueError('Pressure must be within0..1')
  yy,xx=np.mgrid[:1536,:1536].astype('float32');xx/=3;yy/=3
  sx=198+(xx-arch[0,0])*76/(arch[-1,0]-arch[0,0]);top=np.interp(xx,arch[:,0],arch[:,1]);source_top=np.interp(sx,self.edge[:,0],self.edge[:,1])
  # shortcut: thickness is a pressure proxy; design lip roll/tuck before narration use.
  sy=source_top+(yy-top)/(1-.4*pressure)
  part=cv2.remap(self.source,sx.astype('float32'),sy.astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  return cv2.resize(part,(512,512),interpolation=cv2.INTER_AREA)
