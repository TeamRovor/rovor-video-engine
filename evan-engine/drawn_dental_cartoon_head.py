"""Optional registered broad dental source drawing, separate from L blade.

Acoustic phone partition unchanged. Existing floor, interior and teeth occlude
both tongue parts. This is a cel drawing study, not dental speaker calibration.
"""
import cv2,numpy as np
from PIL import Image
from phone_tongue_cartoon_head import PhoneTongueCartoonHead
from rooted_floor_cartoon_head import rooted_blade_matrix
from lingual_cartoon_head import tongue_lift
from layered_cartoon_head import straight,over,ROOT
from cartoon_head import POINTS,SIZE
from contour_cartoon_head import contour_maps
class DrawnDentalCartoonHead(PhoneTongueCartoonHead):
 def __init__(self,root=ROOT):
  super().__init__(root)
  self.dental_tip=np.asarray(Image.open(root/'dental-tongue-v1/tip.png').convert('RGBA'))
  self.dental_morph_fallbacks=0
 def blade_matrix(self,w):return rooted_blade_matrix(tongue_lift(w))
 def tongue_parts(self,w,oral):
  d=float(self.dental_fraction)
  if d<=0:return super().tongue_parts(w,oral)
  def premul(raw):
   a=raw.astype(np.float32).copy();a[:,:,:3]*=a[:,:,3:4]/255;return a
  source=premul(self.dental_tip)
  if d<1:
   original=premul(self.blade)
   # Share one alpha envelope before color mixing; avoid two ghost tips.
   try:
    a,b=contour_maps(original,source,d)
    source=self._remap(original,a)*(1-d)+self._remap(source,b)*d
   except ValueError:
    self.dental_morph_fallbacks+=1
    return super().tongue_parts(w,oral)
  source=cv2.warpAffine(source,self.blade_matrix(w),(SIZE,SIZE),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
  source=self.constrain_surface(source)
  blade=self.sample_surface(straight(source).astype('uint8'),POINTS['H'],oral,2)
  floor=self.sample_surface(self.root_floor,POINTS['H'],oral,2)
  return blade,floor

 def teeth_surface(self,w,oral,shape_weights=None):
  teeth=super().teeth_surface(w,oral,shape_weights)
  if self.dental_fraction<=0:return teeth
  blade,_=self.tongue_parts(w,oral)
  alpha=teeth[:,:,3];ys=np.arange(SIZE,dtype=np.float32)[:,None]
  opaque=alpha>=127.5;bottom=np.max(np.where(opaque,ys,-1000),axis=0)
  # Only the lower1.5px of the existing incisors can be covered by the tip.
  # Upper tooth pixels, the lip boundary and all other phones stay untouched.
  edge=np.clip((ys-(bottom[None,:]-1.5))/1.5,0,1)*(alpha/255)
  return over(teeth,blade,float(self.dental_fraction)*edge[:,:,None])
