"""Optional L / TH-DH articulation of the existing registered tongue drawing.

Authored deformation, not a new dental drawing or a measured tongue model.
Keep timing, H salience, mouth aperture and all lip/teeth masks unchanged.
"""
import numpy as np
from rooted_floor_cartoon_head import RootedFloorCartoonHead
from lingual_cartoon_head import tongue_lift
from painted_timing import ease

def dental_fraction(t,plan):
    """Partition existing H kernel evidence; do not infer identity from volume."""
    if plan.get('alignment',{}).get('status')!='acoustic':return 0.
    dental=total=0.
    for g in plan.get('gestures',plan['phonemes']):
        phone=g['phone'].rstrip('012')
        if phone not in ('L','TH','DH'):continue
        a,b=g['start'],g['end'];radius=max(.055,min(.14,(b-a)/2+.045))
        distance=abs((t+.018-(a+b)/2)/radius)
        strength=(1-distance*distance)**2 if distance<1 else 0.
        total+=strength
        if phone in ('TH','DH'):dental+=strength
    return dental/total if total>1e-12 else 0.

def phone_blade_matrix(lift,dental):
    lift=float(np.clip(lift,0,1));dental=float(np.clip(dental,0,1))
    sx=.8+(.2+.55*dental)*lift
    sy=.12+(.88-.55*dental)*float(ease(lift))
    return np.array([[sx,0,237*(1-sx)],[0,sy,354*(1-sy)]],np.float32)

class PhoneTongueCartoonHead(RootedFloorCartoonHead):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.dental_fraction=0.
    def blade_matrix(self,w):
        return phone_blade_matrix(tongue_lift(w),self.dental_fraction)
    def at(self,t,plan):
        previous=self.dental_fraction
        try:
            self.dental_fraction=dental_fraction(t,plan)
            result=super().at(t,plan)
            if self.capture_tongue and self.last_tongue is not None:
                self.last_tongue['dentalFraction']=self.dental_fraction
            return result
        finally:self.dental_fraction=previous
