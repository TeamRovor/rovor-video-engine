"""Optional duration-sensitive jaw undershoot, separate from phone identity.

Short open vowels cannot reach the same excursion as sustained vowels. This is
an authored cartoon performance curve, not measured speaker biomechanics.
Acoustic weights still carry the recording's existing energy response.
"""
import numpy as np
from dental_fv_cartoon_head import DentalFVCartoonHead
from separated_cartoon_head import jaw_weights
from rounded_cartoon_head import rounding_identity
from expressive_cartoon_head import brow_controls
from speech_planner import planned_weights,VOWELS
from painted_timing import ease

def vowel_excursion(duration):
    return .45+.55*float(ease((duration-.08)/.14))

def duration_budget(t,plan):
    weighted=0.;total=0.
    for p in plan['phonemes']:
        if p['value'] not in 'CD' or p['phone'].rstrip('012') not in VOWELS:continue
        a,b=p['start'],p['end']
        if t<a-.035 or t>b+.045:continue
        strength=float(ease((t-(a-.035))/.060))*(1-float(ease((t-(b-.020))/.065)))
        weighted+=strength*(1-vowel_excursion(b-a));total+=strength
    return 1-weighted/max(1.,total)

def duration_jaw_weights(t,plan,identity=None):
    jaw=jaw_weights(t,plan,identity)
    if plan.get('alignment',{}).get('status')!='acoustic':return jaw
    budget=duration_budget(t,plan);out=jaw.copy()
    for i in [3,4]:
        removed=out[i]*(1-budget);out[i]-=removed;out[2]+=removed
    return out

class DurationCartoonHead(DentalFVCartoonHead):
    def jaw_control(self,t,plan,identity=None):
        return duration_jaw_weights(t,plan,identity)
    def at(self,t,plan):
        if plan.get('alignment',{}).get('status')!='acoustic':return super().at(t,plan)
        identity=planned_weights(t,plan,plan['fallbackCues'])
        return self.weights(identity,brow_controls(t,plan),shape_weights=rounding_identity(t,plan),geometry_weights=self.jaw_control(t,plan,identity))
