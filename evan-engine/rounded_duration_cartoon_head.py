"""Optional conservative height undershoot for short held rounded AO vowels.

Preserve original source drawings, phone/material/rounding identity, mouth
corners/width, and independent chin. Authored control, not measured anatomy.
"""
import numpy as np
from independent_chin_cartoon_head import IndependentChinCartoonHead
from duration_cartoon_head import duration_jaw_weights
from painted_timing import ease
MIN_ROUNDED_EXCURSION=.75

def rounded_duration_budget(t,plan):
 weighted=total=0.
 for p in plan['phonemes']:
  if p['phone'].rstrip('012')!='AO' or p['value']!='E':continue
  a,b=p['start'],p['end']
  if t<a-.035 or t>b+.045:continue
  strength=float(ease((t-(a-.035))/.060))*(1-float(ease((t-(b-.020))/.065)))
  excursion=MIN_ROUNDED_EXCURSION+(1-MIN_ROUNDED_EXCURSION)*float(ease((b-a-.08)/.14))
  weighted+=strength*(1-excursion);total+=strength
 return 1-weighted/max(1.,total)

def rounded_duration_jaw_weights(t,plan,identity=None):
 old=duration_jaw_weights(t,plan,identity)
 if plan.get('alignment',{}).get('status')!='acoustic':return old
 budget=rounded_duration_budget(t,plan)
 if budget==1:return old
 new=old.copy();removed=new[5]*(1-budget);new[5]-=removed;new[2]+=removed
 return new

class RoundedDurationCartoonHead(IndependentChinCartoonHead):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self._rounded_reference=None;self.capture_rounding=False;self.last_rounding=None
 def jaw_control(self,t,plan,identity=None):
  new=rounded_duration_jaw_weights(t,plan,identity)
  if self.capture_rounding:
   old=duration_jaw_weights(t,plan,identity);opening=np.array([self.geometry[k][7]-self.geometry[k][6] for k in 'XABCDEFGH'])
   self.last_rounding=dict(budget=rounded_duration_budget(t,plan),oldAperture=float(old@opening),newAperture=float(new@opening),contactWeight=float(new[1]),fvWeight=float(new[7]))
  return new
 def target_points(self,weights,shape_weights=None):
  if self._rounded_reference is None or shape_weights is None:return super().target_points(weights,shape_weights)
  old=self._rounded_reference;opening=np.array([self.geometry[k][7]-self.geometry[k][6] for k in 'XABCDEFGH']);before=float(old@opening);after=float(np.asarray(weights)@opening)
  target=super().target_points(old,shape_weights)
  if before==after:return target
  # Scale height about the original sloping mouth-corner chord. All X,
  # corners and non-mouth anchors remain the old phone/rounding trajectory.
  left,right=target[8].copy(),target[0].copy();u=(target[:32,0]-left[0])/(right[0]-left[0]);chord=left[1]+u*(right[1]-left[1]);target[:32,1]=chord+(target[:32,1]-chord)*(after/max(before,1e-9));target[8]=left;target[0]=right
  return target
 def at(self,t,plan):
  previous=self._rounded_reference
  try:
   self._rounded_reference=duration_jaw_weights(t,plan) if plan.get('alignment',{}).get('status')=='acoustic' else None
   return super().at(t,plan)
  finally:self._rounded_reference=previous
