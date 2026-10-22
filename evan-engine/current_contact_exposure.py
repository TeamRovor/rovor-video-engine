"""Review-only current-frame F/V assembly; no default profile promotion.

The existing contact drawing stays in the upper-face carrier. Jaw UVs use
fresh oral controls even when the painted-vowel builder is bypassed.
"""
import cv2
import numpy as np
from PIL import Image
from corresponding_lip_exposure import CorrespondingLipExposure,CavityCaptureHead
from guided_jaw_exposure import target_mesh
from jaw_overlap_exposure import upper_ownership
from lip_surface_correspondence import corresponding_fields
from layered_cartoon_head import over,straight
from painted_contour_cartoon_head import oral_fields

class CurrentContactHead(CavityCaptureHead):
 def cavity_surface(self,w,oral,shape_weights=None):
  cavity=super().cavity_surface(w,oral,shape_weights)
  self.current_backing=cavity.copy()
  if self._fv_strength>=1:
   # Keep the SAME backing material at the exact contact endpoint. The
   # foreground contact path remains intact; only its hidden joint backing
   # uses the painted cavity already used at arbitrarily near-full contact.
   source=self.painted['Cavity'].astype('float32').copy();source[:,:,:3]*=source[:,:,3:4]/255
   fields=oral_fields(self.painted_points,oral)
   self.current_backing=cv2.resize(cv2.remap(source,*fields,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  return cavity
 def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
  result=super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
  self.material_cavity=self.current_backing.copy()
  return result
 def oral_target(self,target,aperture):
  oral=super().oral_target(target,aperture)
  self.current_oral=oral.copy();self.current_fv=float(self._fv_strength)
  return oral

class CurrentContactExposure(CorrespondingLipExposure):
 def __init__(self):
  super().__init__();self.head=CurrentContactHead()
 def at(self,t,plan):
  baseline=self.head.at(t,plan)
  return self.assemble(baseline)
 def assemble(self,baseline):
  target,minimum=target_mesh(self.head.current_oral,self.head.exposure_skin)
  maps=corresponding_fields(self.source_points,target)
  jaw=cv2.resize(cv2.remap(self.jaw,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  owned=upper_ownership(target)
  if not np.all(owned[:315,190:280]==1):raise ValueError('Upper-face/nose ownership lost coverage')
  carrier=np.array(baseline).astype('float32');carrier[:,:,:3]*=carrier[:,:,3:4]/255;carrier*=owned[:,:,None]
  parts={'Neck backing':self.neck.copy(),'Painted mouth cavity backing':self.head.material_cavity.copy(),'Source-matched jaw and lower lip':jaw,'Upper face with cheek wings':carrier}
  result=np.zeros_like(jaw)
  for part in parts.values():result=over(result,part)
  candidate=Image.fromarray(np.rint(np.clip(straight(result),0,255)).astype('uint8'))
  self.last_parts=parts;self.last_target=target.copy()
  before=np.array(baseline);after=np.array(candidate)
  nose=int(np.max(abs(before[288:315,190:280].astype(int)-after[288:315,190:280].astype(int))))
  if nose>1:raise ValueError(f'Upper nose changed: {nose}')
  return baseline,candidate,dict(minimumTriangleArea2=minimum,fv=self.head.current_fv,lipCenter=self.head.current_oral[20].tolist(),chinY=float(self.head.exposure_skin[46,1]),noseMaximumRGBAChange=nose,upper288RowsExact=bool(np.array_equal(before[:288],after[:288])),oralBelow240=int(np.count_nonzero(after[318:365,190:280,3]<240)),continuousFVFallbacks=self.head.continuous_fv_fallbacks)
