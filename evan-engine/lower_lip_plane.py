"""One drawn lip plane with independent pressure and a caller-supplied arch.

Source alpha is preserved. Pressure compresses lip thickness below its contact
edge. jaw_arch supplies its complementary jaw paint boundary; neither method
changes teeth, upper lip or timing. Review-only artwork.
"""
import json,cv2,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load

def arch_surface(source,edge,arch,thickness=1):
 arch=np.asarray(arch,dtype=np.float32);edge=np.asarray(edge,dtype=np.float32)
 if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine finite arch points ordered left to right')
 if edge.ndim!=2 or edge.shape[1]!=2 or len(edge)<2 or not np.isfinite(edge).all() or np.any(np.diff(edge[:,0])<=0):raise ValueError('Source edge must be finite and ordered left to right')
 if not np.isfinite(thickness) or thickness<=0:raise ValueError('Thickness must be positive and finite')
 yy,xx=np.mgrid[:1536,:1536].astype('float32');xx/=3;yy/=3
 sx=edge[0,0]+(xx-arch[0,0])*(edge[-1,0]-edge[0,0])/(arch[-1,0]-arch[0,0]);top=np.interp(xx,arch[:,0],arch[:,1]);source_top=np.interp(sx,edge[:,0],edge[:,1])
 sy=source_top+(yy-top)/thickness
 part=cv2.remap(source,sx.astype('float32'),sy.astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
 return cv2.resize(part,(512,512),interpolation=cv2.INTER_AREA)

class LowerLipPlane:
 def __init__(self):
  folder=ROOT/'lower-lip-pressure-v1';self.source=load(folder/'Lower-Lip-Candidate.png');self.edge=np.asarray(json.loads((folder/'Registration.json').read_text())['sourceTopEdge'],np.float32)
  # Measure paint ownership once, never quantize moving target-frame pixels.
  depth=[0.]
  for x,y in self.edge[1:-1]:
   alpha=cv2.remap(self.source[:,:,3],np.full((512,1),x,np.float32),np.arange(512,dtype=np.float32)[:,None],cv2.INTER_LINEAR)[:,0]
   rows=np.where(alpha>=127.5)[0]
   if not len(rows) or rows[-1]>=511:raise ValueError('Lower lip has no bounded half-alpha outer edge')
   bottom=int(rows[-1]);cross=bottom+(alpha[bottom]-127.5)/max(float(alpha[bottom]-alpha[bottom+1]),1e-6)
   depth.append(max(0.,float(cross-y)))
  self.depth=np.asarray([*depth,0.],np.float32)
 def jaw_arch(self,arch,pressure):
  result=np.asarray(arch,np.float32).copy()
  if result.shape!=(9,2) or not np.isfinite(result).all() or np.any(np.diff(result[:,0])<=0):raise ValueError('Expected nine finite ordered jaw arch points')
  if not np.isfinite(pressure) or not 0<=pressure<=1:raise ValueError('Pressure must be within0..1')
  x=self.edge[0,0]+(result[:,0]-result[0,0])/(result[-1,0]-result[0,0])*(self.edge[-1,0]-self.edge[0,0])
  depth=np.interp(x,self.edge[:,0],self.depth)*(1-.4*pressure)
  # shortcut: .8px is authored paint overlap; replace with an approved lip/jaw drawing contract.
  result[:,1]+=np.maximum(0,depth-.8)
  return result
 def pose(self,arch,pressure):
  if not np.isfinite(pressure) or not 0<=pressure<=1:raise ValueError('Pressure must be within0..1')
  # shortcut: thickness is a pressure proxy; design lip roll/tuck before approved animation.
  return arch_surface(self.source,self.edge,arch,1-.4*pressure)
