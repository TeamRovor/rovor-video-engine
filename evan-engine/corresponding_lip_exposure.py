"""Review-only source-matched lip edge with actual painted cavity backing.

No new artwork, skin-colored gap fill, alpha wash, retiming or default changes.
The source jaw and lip remain one drawing; upper face still borrows old mouth.
"""
import cv2,numpy as np
from PIL import Image
from jaw_overlap_exposure import JawOverlapExposure
from guided_jaw_exposure import CaptureHead,target_mesh
from lip_surface_correspondence import source_mesh,corresponding_fields
from layered_cartoon_head import over,straight

class CavityCaptureHead(CaptureHead):
 def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
  self.material_cavity=cavity.copy()
  return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)

class CorrespondingLipExposure(JawOverlapExposure):
 def __init__(self):
  super().__init__();self.head=CavityCaptureHead();self.source_points,self.correspondence=source_mesh(self.jaw)
 def at(self,t,plan):
  baseline,previous,row=super().at(t,plan);self.before_correspondence=previous
  target,minimum=target_mesh(self.head.last_painted_target,self.head.exposure_skin);maps=corresponding_fields(self.source_points,target)
  jaw=cv2.resize(cv2.remap(self.jaw,*maps,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  # Existing painted cavity, not procedurally invented skin or hole paint.
  cavity=self.head.material_cavity.copy()
  old_jaw=self.last_parts['Jaw and lower lip combined'].copy()
  carrier=self.last_parts['Upper face with cheek wings'].copy()
  parts={'Neck backing':self.neck.copy(),'Painted mouth cavity backing':cavity,'Source-matched jaw and lower lip':jaw,'Upper face with cheek wings':self.last_parts['Upper face with cheek wings']}
  assembled=np.zeros_like(jaw)
  for part in parts.values():assembled=over(assembled,part)
  self.last_parts=parts;candidate=Image.fromarray(np.rint(np.clip(straight(assembled),0,255)).astype('uint8'))
  def stack(materials):
   result=np.zeros_like(jaw)
   for part in materials:result=over(result,part)
   return Image.fromarray(np.rint(np.clip(straight(result),0,255)).astype('uint8'))
  self.ablations={'Previous':previous,'Edge correspondence only':stack([self.neck,jaw,carrier]),'Cavity backing only':stack([self.neck,cavity,old_jaw,carrier]),'Both':candidate}
  p=np.array(previous);n=np.array(candidate);b=np.array(baseline);region=np.zeros(p.shape[:2],bool);region[318:365,190:280]=True
  counts={name:dict(below128=int(np.count_nonzero(np.array(image)[318:365,190:280,3]<128)),below240=int(np.count_nonzero(np.array(image)[318:365,190:280,3]<240))) for name,image in self.ablations.items()}
  row.update(oralAlphaCounts=counts,oralROI=[190,318,280,365],maximumUpper288Difference=int(np.max(abs(p[:288].astype(int)-n[:288].astype(int)))),maximumBottom400Difference=int(np.max(abs(p[400:].astype(int)-n[400:].astype(int)))))
  assert row['maximumUpper288Difference']==0
  return previous,candidate,row
