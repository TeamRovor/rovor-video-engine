"""Opt-in premultiplied oral-material interpolation for F/V release."""
from rounded_cartoon_head import RoundedCartoonHead
from layered_cartoon_head import over
from painted_timing import ease

class MaterialCartoonHead(RoundedCartoonHead):
    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        fv=float(w[7])
        # Retain exact existing endpoints and all non-contact mouth rendering.
        if fv<=0 or fv>=1:
            return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        visible=self.cavity_visibility(aperture)
        vowel=cavity*visible
        vowel=over(vowel,teeth,visible*float(ease((aperture-2)/7))*self.teeth_rounding_visibility(w))
        vowel=over(vowel,tongue,visible*float(ease((aperture-8)/12)))
        vowel=over(vowel,closed,self.closed_visibility(aperture))
        # Interpolate the two premultiplied oral groups BEFORE placing on skin.
        # Overlapping opaque pixels remain opaque; two partial alpha-over calls
        # exposed skin with coverage (1-fv)+fv*fv instead of full material.
        return over(face,vowel*(1-fv)+contact*fv)
