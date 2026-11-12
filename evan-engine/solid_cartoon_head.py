"""Opt-in opaque oral material; opening is driven by mesh aperture, not dissolve."""
from fv_cartoon_head import FVContactHead
from painted_timing import ease
import numpy as np

class SolidCavityHead(FVContactHead):
    def oral_target(self,target,aperture):
        opening=float(ease((aperture-1)/7))
        if opening>=1:return target.copy()
        oral=target.copy();height=max(1.,float(np.ptp(target[:16,1])))
        scale=(1.2+(height-1.2)*opening)/height
        # Preserve the drawn corner-to-corner tilt as the slit closes. A
        # horizontal collapse left a second line beneath the tilted smile.
        a,b=target[0],target[8];slope=float((a[1]-b[1])/(a[0]-b[0]))
        chord=b[1]+(oral[:32,0]-b[0])*slope
        oral[:32,1]=chord+(oral[:32,1]-chord)*scale
        return oral
    def closed_visibility(self,aperture):
        # Keep an unbroken ink stroke while subpixel cavity coverage is sparse.
        return 1-float(ease((aperture-2)/1.2))
    def cavity_visibility(self,aperture):
        # Fade only while the inner slit has subpixel coverage. Keep the
        # material opaque as geometry opens it, avoiding brown skin mixtures.
        return float(ease((aperture-1)/1.2))
