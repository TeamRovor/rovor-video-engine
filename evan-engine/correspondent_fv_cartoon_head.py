"""Optional common oral silhouette during F/V transitions.

Both oral constructions move to the same interpolated alpha envelope before
mixing; no full-face patch or timing edit. This is drawn-envelope correspondence,
not anatomical lip topology or speaker calibration.
"""
import cv2,numpy as np
from planar_fv_cartoon_head import PlanarFVCartoonHead
from contour_cartoon_head import contour_maps
from layered_cartoon_head import ROOT,over
from lingual_cartoon_head import tongue_lift
from painted_timing import ease

class CorrespondentFVCartoonHead(PlanarFVCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);self.fv_correspondence_fallbacks=0;self.fv_correspondence_samples=0;self.capture_fv_registration=False;self.last_fv_registration=None
    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        fv=float(w[7]);visible=self.cavity_visibility(aperture)
        if fv<=0 or fv>=1:
            return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        floor=float(ease((aperture-8)/12));lift=tongue_lift(w)*float(ease((aperture-1.2)/4))
        tongue_opacity=visible*max(floor,lift);teeth_opacity=visible*float(ease((aperture-2)/7))*self.teeth_rounding_visibility(w);closed_opacity=self.closed_visibility(aperture)
        def assemble(c,t,blade,lips):
            value=over(c*visible,blade,tongue_opacity)
            return over(over(value,t,teeth_opacity),lips,closed_opacity)
        vowel=assemble(cavity,teeth,tongue,closed)
        try:
            fields=contour_maps(vowel,contact,fv)
        except ValueError:
            self.fv_correspondence_fallbacks+=1
            return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        self.fv_correspondence_samples+=1
        # Remap each working oral surface with the SAME field. Internal teeth /
        # tongue stay registered to their lip parent and retain material alpha.
        before_vowel=vowel;before_contact=contact
        vowel=assemble(*(self._remap(part,fields[0]) for part in [cavity,teeth,tongue,closed]))
        contact=self._remap(contact,fields[1])
        if self.capture_fv_registration:
            def mismatch(a,b):return int(np.count_nonzero((a[:,:,3]>=127.5)!=(b[:,:,3]>=127.5)))
            self.last_fv_registration=dict(contactWeight=fv,beforeDisagreementPixels=mismatch(before_vowel,before_contact),afterDisagreementPixels=mismatch(vowel,contact),validPremultiplied=all(bool(np.isfinite(v).all() and np.all(v>=0) and np.all(v[:,:,:3]<=v[:,:,3:4]+1e-4) and v[:,:,3].max()<=255.0001) for v in [vowel,contact]))
        # The radial field exists over the whole canvas, but only the oral
        # drawings belong to this control. Preserve the original blend outside
        # their opaque-contour bounds plus a 3px antialias margin. Otherwise
        # resampling minute alpha dust can change unrelated skin by one LSB.
        boxes=[]
        for surface in [before_vowel,before_contact]:
            contours,_=cv2.findContours((surface[:,:,3]>=127.5).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            boxes.append(cv2.boundingRect(max(contours,key=cv2.contourArea)))
        x0=max(0,min(b[0] for b in boxes)-3);y0=max(0,min(b[1] for b in boxes)-3)
        x1=min(face.shape[1],max(b[0]+b[2] for b in boxes)+3);y1=min(face.shape[0],max(b[1]+b[3] for b in boxes)+3)
        mixed=before_vowel*(1-fv)+before_contact*fv
        aligned=vowel*(1-fv)+contact*fv
        mixed[y0:y1,x0:x1]=aligned[y0:y1,x0:x1]
        return over(face,mixed)
