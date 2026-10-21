"""Opt-in continuous painted-vowel/FV material path; no phoneme retiming."""
import cv2
import numpy as np
from aperture_response_cartoon_head import ApertureResponseCartoonHead,direct_oral_target
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from painted_contour_cartoon_head import PaintedContourCartoonHead
from contour_cartoon_head import contour_maps
from layered_cartoon_head import over


class ContinuousFVCartoonHead(ApertureResponseCartoonHead):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._fv_strength=0.;self.continuous_fv_samples=0;self.continuous_fv_fallbacks=0

    def weights(self,weights,expression=None,shape_weights=None,geometry_weights=None):
        previous=self._painted_use,self._fv_strength
        try:
            w=np.asarray(weights,float);fv=float(w[7]/w.sum())
            self._painted_use=fv<1.;self._fv_strength=fv
            # Bypass PaintedContour's binary any-FV switch. Keep the same
            # upstream expression, skin, phoneme and independent chin code.
            return ConstructionSkinCartoonHead.weights(self,weights,expression,shape_weights=shape_weights,geometry_weights=geometry_weights)
        finally:self._painted_use,self._fv_strength=previous

    def oral_target(self,target,aperture):
        legacy=ConstructionSkinCartoonHead.oral_target(self,target,aperture)
        fv=self._fv_strength
        if fv>=1:return legacy
        direct=direct_oral_target(target,aperture)
        oral=direct.copy();oral[:32,1]=direct[:32,1]*(1-fv)+legacy[:32,1]*fv
        return oral

    def cavity_surface(self,w,oral,shape_weights=None):
        if self._fv_strength>=1:return super().cavity_surface(w,oral,shape_weights)
        # Build the SAME painted source for arbitrarily small/mixed contact.
        # This copied weight only bypasses its branch; it does not change any
        # planned identity/geometry weights used to construct the target.
        source_w=np.asarray(w).copy();source_w[7]=0
        return PaintedContourCartoonHead.cavity_surface(self,source_w,oral,shape_weights)

    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        fv=float(w[7])
        if fv>=1:return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        group=PaintedContourCartoonHead.composite_oral(self,np.zeros_like(face),cavity,teeth,tongue,contact,closed,aperture,w)
        if fv<=0:return over(face,group)
        before_group,before_contact=group,contact
        try:
            fields=contour_maps(group,contact,fv)
            group=self._remap(group,fields[0])
            contact=self.registered_contact_surface(contact,fields[1],w)
        except ValueError:
            # Finite material blend remains available for degenerate contours;
            # record it rather than silently calling the old hard switch.
            self.continuous_fv_fallbacks+=1
            return over(face,before_group*(1-fv)+before_contact*fv)
        self.continuous_fv_samples+=1
        # Restrict radial sampling to the oral artwork's opaque bounds. This
        # prevents distant tiny-alpha dust from altering unrelated face pixels.
        boxes=[]
        for part in [before_group,before_contact]:
            ys,xs=np.where(part[:,:,3]>=127.5)
            if len(xs):boxes.append((xs.min(),ys.min(),xs.max()+1,ys.max()+1))
        mixed=before_group*(1-fv)+before_contact*fv
        if boxes:
            x0=max(0,min(b[0] for b in boxes)-3);y0=max(0,min(b[1] for b in boxes)-3)
            x1=min(512,max(b[2] for b in boxes)+3);y1=min(512,max(b[3] for b in boxes)+3)
            mixed[y0:y1,x0:x1]=(group*(1-fv)+contact*fv)[y0:y1,x0:x1]
        return over(face,mixed)
