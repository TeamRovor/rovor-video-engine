"""Optional inertial chin anchors separate from fast oral contact geometry.

Reuse existing face-skin artwork. This is independent control of three mesh
anchors, not a separately redrawn jaw layer or anatomical mandible rig.
"""
import numpy as np
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
from duration_cartoon_head import duration_jaw_weights
CHIN_ANCHORS=np.array([45,46,47])
CHIN_KERNEL=np.array([1,8,28,56,70,56,28,8,1],float)/256

def chin_weights(t,plan):
 if plan.get('alignment',{}).get('status')!='acoustic':return None
 # Symmetric166.7ms support: anticipation/follow-through, no playback delay.
 return sum(duration_jaw_weights(max(0,t+(i-4)/48),plan)*weight for i,weight in enumerate(CHIN_KERNEL))

class IndependentChinCartoonHead(DrawnDentalCartoonHead):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self._chin_weights=None
 def skin_target(self,weights,target):
  skin=super().skin_target(weights,target)
  if self._chin_weights is not None:
   slow=self.target_points(self._chin_weights)
   skin[CHIN_ANCHORS]=slow[CHIN_ANCHORS]
  return skin
 def at(self,t,plan):
  previous=self._chin_weights
  try:
   self._chin_weights=chin_weights(t,plan)
   return super().at(t,plan)
  finally:self._chin_weights=previous
