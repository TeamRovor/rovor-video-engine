"""Opt-in phone-driven lip width independent of audio-driven jaw opening."""
import numpy as np
from solid_cartoon_head import SolidCavityHead
from expressive_cartoon_head import brow_controls
from speech_planner import planned_weights,acoustic_weights

def rounding_identity(t,plan):
    """Authored symmetric 62.5 ms lead/release; not measured phone boundaries."""
    weights=(1,2,3,4,3,2,1)
    return sum(acoustic_weights(max(0,t+(i-3)/48),plan,plan['fallbackCues'],energy_weighting=False)*v for i,v in enumerate(weights))/sum(weights)

class RoundedCartoonHead(SolidCavityHead):
    def target_points(self,weights,shape_weights=None):
        target=super().target_points(weights)
        if shape_weights is None:return target
        identity=np.asarray(shape_weights,float);identity=identity/identity.sum()
        shape=super().target_points(identity)
        rounding=float(identity[5]+identity[6])
        # Contacts suppress rounding, including silent bilabial closures.
        active=float(identity[1:].sum())
        strength=(rounding/max(active,1e-9))*float(np.clip(1-weights[1]-weights[7],0,1))
        target[:32,0]=target[:32,0]*(1-strength)+shape[:32,0]*strength
        # All Y coordinates, jaw/chin and non-mouth anchors retain the existing
        # energy-weighted target. This does not retime a word or phone.
        return target
    def skin_target(self,weights,target):
        # Lip narrowing must not drag nose/ear texture across the cheek.
        return super().target_points(weights)
    def at(self,t,plan):
        fallback=plan['fallbackCues'];jaw=planned_weights(t,plan,fallback)
        identity=rounding_identity(t,plan) if plan.get('alignment',{}).get('status')=='acoustic' else None
        return self.weights(jaw,brow_controls(t,plan),shape_weights=identity)
