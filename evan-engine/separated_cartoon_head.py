"""Opt-in jaw easing independent of tongue/contact material identity.

Authored 2D performance controls, not new phone alignment or measured anatomy.
The symmetric 83.3 ms window anticipates/releases by 41.7 ms; it adds no
playback delay. Original bilabial/FV weights and fully settled rest are exact.
"""
import numpy as np
from lingual_cartoon_head import LingualCartoonHead
from speech_planner import planned_weights
from expressive_cartoon_head import brow_controls
from rounded_cartoon_head import rounding_identity

KERNEL=(1,4,6,4,1)
TONGUE_JAW_RETAIN=.25

def jaw_weights(t,plan,identity=None):
    fallback=plan['fallbackCues']
    current=planned_weights(t,plan,fallback) if identity is None else np.asarray(identity,float)
    if plan.get('alignment',{}).get('status')!='acoustic' or current[0]>=1-1e-9:
        return current.copy()
    jaw=sum(planned_weights(max(0,t+(i-2)/48),plan,fallback)*v for i,v in enumerate(KERNEL))/sum(KERNEL)
    # A tongue contact can lift without fully opening the jaw. Transfer most
    # of H's geometry to the existing modest B aperture, retaining its width.
    transfer=jaw[8]*(1-TONGUE_JAW_RETAIN);jaw[8]-=transfer;jaw[2]+=transfer
    # Do not smear closures/contact releases into neighboring vowels.
    contacts=current[[1,7]];budget=max(0.,1-float(contacts.sum()))
    jaw[[1,7]]=0
    if jaw.sum()>1e-12:jaw*=budget/jaw.sum()
    else:jaw[0]=budget
    jaw[[1,7]]=contacts
    return jaw

class SeparatedCartoonHead(LingualCartoonHead):
    def at(self,t,plan):
        if plan.get('alignment',{}).get('status')!='acoustic':
            return super().at(t,plan)
        identity=planned_weights(t,plan,plan['fallbackCues'])
        shape=rounding_identity(t,plan)
        return self.weights(identity,brow_controls(t,plan),shape_weights=shape,geometry_weights=jaw_weights(t,plan,identity))
