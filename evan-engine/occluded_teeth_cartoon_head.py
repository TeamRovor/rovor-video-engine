"""Optional tooth retraction behind the lip matte instead of rounded fades.

Authored 2D geometry control, not measured jaw depth or new phone alignment.
The existing aperture/FV material gates remain; only rounded tooth fades are
replaced. No new artwork or source pixel editing.
"""
import numpy as np
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from rounded_art_cartoon_head import rounded_art_strength
from layered_cartoon_head import LayeredCartoonHead
from cartoon_head import POINTS

def tooth_retraction(w,oral):
    s=rounded_art_strength(w)
    return s*max(8.,.45*float(np.ptp(oral[:16,1])))

class OccludedTeethCartoonHead(BroadCavityCartoonHead):
    def teeth_surface(self,w,oral,shape_weights=None):
        move=tooth_retraction(w,oral)
        if move<=0:return super().teeth_surface(w,oral,shape_weights)
        target=oral.copy();target[:,1]-=move
        return self.sample_surface(self.layers['upper-teeth'],POINTS['C'],target,2)
    def clip_interiors(self,teeth,tongue,interior,w,shape_weights=None):
        # Skip RoundedArt's additional tooth opacity. Preserve the same matte
        # multiplication and separate tongue instead of pre-compositing them.
        return LayeredCartoonHead.clip_interiors(self,teeth,tongue,interior,w,shape_weights)
    def teeth_rounding_visibility(self,w):
        return 1.
