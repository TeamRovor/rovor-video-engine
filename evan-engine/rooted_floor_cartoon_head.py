"""Optional low vowel tongue and floor occlusion of the raised blade root.

Reuse both actual tongue drawings. Ordinary vowels retract the blade below the
floor; H identity lifts it. H still serves L/TH/DH, not separate dental anatomy.
"""
import cv2,numpy as np
from cartoon_head import POINTS,SIZE
from layered_cartoon_head import over,straight
from lingual_cartoon_head import tongue_lift
from duration_cartoon_head import DurationCartoonHead
from painted_timing import ease
from cached_cartoon_sampling import CachedSurfaceMixin

def rooted_blade_matrix(lift):
    lift=float(np.clip(lift,0,1));sx=.8+.2*lift;sy=.12+.88*float(ease(lift))
    return np.array([[sx,0,237*(1-sx)],[0,sy,354*(1-sy)]],np.float32)

class RootedFloorCartoonHead(CachedSurfaceMixin,DurationCartoonHead):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.capture_tongue=False;self.last_tongue=None
    def tongue_parts(self,w,oral):
        art=self.blade.astype('float32').copy();art[:,:,:3]*=art[:,:,3:4]/255
        art=cv2.warpAffine(art,rooted_blade_matrix(tongue_lift(w)),(SIZE,SIZE),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        art=self.constrain_surface(art)
        blade=self.sample_surface(straight(art).astype('uint8'),POINTS['H'],oral,2)
        floor=self.sample_surface(self.root_floor,POINTS['H'],oral,2)
        return blade,floor
    def tongue_surface(self,w,oral,shape_weights=None):
        blade,floor=self.tongue_parts(w,oral)
        # The broad floor covers the blade root; lifted tip remains exposed.
        if self.capture_tongue:
            exposed=blade[:,:,3]*(1-floor[:,:,3]/255)
            self.last_tongue=dict(lift=tongue_lift(w),sourceBladeYScale=float(rooted_blade_matrix(tongue_lift(w))[1,1]),bladeCoverageBeforeFloor=float(blade[:,:,3].sum()/255),bladeCoverageAfterFloor=float(exposed.sum()/255),floorCoverage=float(floor[:,:,3].sum()/255),validPremultiplied=all(bool(np.isfinite(v).all() and v.min()>=0 and v[:,:,3].max()<=255.0001 and np.all(v[:,:,:3]<=v[:,:,3:4]+1e-4)) for v in [blade,floor]))
        return over(blade,floor)
