"""Optional two-part drawn seal on a uniform mouth-corner parent.

A bilabial-only drawn seal; original resting smile retained.
Component color interpolation is not continuous open-lip anatomy or retiming.
"""
import json,cv2,numpy as np
from PIL import Image
from independent_chin_cartoon_head import IndependentChinCartoonHead
from planar_fv_cartoon_head import contact_matrix
from layered_cartoon_head import ROOT,over
class UniformSealCartoonHead(IndependentChinCartoonHead):
 def __init__(self,root=ROOT):
  super().__init__(root);folder=root/'lip-seal-v1';self._seal_mix=0.;self.capture_seal=False;self.last_seal=None;self.seal_meta=json.loads((folder/'manifest.json').read_text());self.seal_art={n:np.asarray(Image.open(folder/(n+'.png')).convert('RGBA')) for n in ['seam','lower-shadow']}
 def closed_parts(self,target):
  m=contact_matrix(target,self.seal_meta['workingCorners']);parts={}
  for name,art in self.seal_art.items():
   raw=art.astype(np.float32);raw[:,:,:3]*=raw[:,:,3:4]/255;raw=cv2.warpAffine(raw,m*2,(1024,1024),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);parts[name]=self.constrain_surface(cv2.resize(raw,(512,512),interpolation=cv2.INTER_AREA))
  return parts
 def weights(self,weights,*args,**kwargs):
  previous=self._seal_mix
  try:
   w=np.asarray(weights,float);self._seal_mix=float(w[1]/w.sum())
   return super().weights(weights,*args,**kwargs)
  finally:self._seal_mix=previous
 def closed_surface(self,target):
  old=super().closed_surface(target)
  if self._seal_mix<=0:
   if self.capture_seal:self.last_seal=dict(mix=0.,sourceUsed=False)
   return old
  parts=self.closed_parts(target);new=over(parts['lower-shadow'],parts['seam'])
  result=old*(1-self._seal_mix)+new*self._seal_mix
  if self.capture_seal:self.last_seal=dict(mix=self._seal_mix,sourceUsed=True,validPremultiplied=bool(np.isfinite(result).all() and result.min()>=0 and result[:,:,3].max()<=255.0001 and np.all(result[:,:,:3]<=result[:,:,3:4]+1e-4)),coveragePixels=float(result[:,:,3].sum()/255))
  return result
