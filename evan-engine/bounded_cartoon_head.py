"""Opt-in valid premultiplied samples before layered head compositing."""
import numpy as np
from anchored_cartoon_head import AnchoredCartoonHead

def bounded_premultiplied(raw):
    """Preserve positive-alpha straight colour while bounding coverage/gamut.

    Negative cubic lobes cannot contribute negative coverage. Positive alpha
    overshoot is rescaled together with RGB, rather than making ink brighter
    by clipping only alpha. Valid premultiplied samples remain exact.
    """
    raw=np.asarray(raw)
    if raw.dtype.kind!='f':raw=raw.astype('float32')
    alpha=raw[:,:,3:4]
    out=raw.copy();coverage=np.clip(alpha,0,255)
    scale=np.ones_like(alpha);np.divide(coverage,alpha,out=scale,where=alpha>0)
    out[:,:,:3]=np.clip(raw[:,:,:3]*scale,0,coverage)
    out[:,:,3:4]=coverage
    out[coverage[:,:,0]==0,:3]=0
    return out

class BoundedCartoonHead(AnchoredCartoonHead):
    def constrain_surface(self,raw):
        return bounded_premultiplied(raw)
