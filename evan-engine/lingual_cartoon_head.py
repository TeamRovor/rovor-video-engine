"""Opt-in rooted tongue blade, existing acoustic L lift and front-tooth occlusion."""
import cv2,numpy as np
from PIL import Image
from material_cartoon_head import MaterialCartoonHead
from expressive_cartoon_head import ROOT
from cartoon_head import POINTS,warp,SIZE
from layered_cartoon_head import over,straight
from painted_timing import ease

def tongue_lift(weights):
    identity=np.asarray(weights,float)
    return float(np.clip(identity[8]/max(float(identity.sum()),1e-9),0,1))

def tongue_matrix(lift):
    lift=float(np.clip(lift,0,1));sx=.8+.2*lift;sy=.42+.58*lift
    return np.array([[sx,0,237*(1-sx)],[0,sy,354*(1-sy)]],np.float32)

class LingualCartoonHead(MaterialCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);self.blade=np.asarray(Image.open(root/'tongue-rig/blade.png').convert('RGBA'));self.root_floor=np.asarray(Image.open(root/'tongue-rig/root-floor.png').convert('RGBA'))
    def tongue_surface(self,w,oral,shape_weights=None):
        art=self.blade.astype('float32').copy();art[:,:,:3]*=art[:,:,3:4]/255
        art=cv2.warpAffine(art,tongue_matrix(tongue_lift(w)),(SIZE,SIZE),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        art=self.constrain_surface(art)
        blade=self.sample_surface(straight(art).astype('uint8'),POINTS['H'],oral,2)
        root=self.sample_surface(self.root_floor,POINTS['H'],oral,2)
        return over(root,blade)
    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        visible=self.cavity_visibility(aperture);fv=float(w[7])
        if (visible<=0 and fv<=0) or fv>=1:
            return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        floor=float(ease((aperture-8)/12))
        lifted=tongue_lift(w)*float(ease((aperture-1.2)/4))
        vowel=cavity*visible
        vowel=over(vowel,tongue,visible*max(floor,lifted))
        # The blade stays inside the cavity and behind the upper incisors.
        vowel=over(vowel,teeth,visible*float(ease((aperture-2)/7))*self.teeth_rounding_visibility(w))
        vowel=over(vowel,closed,self.closed_visibility(aperture))
        return over(face,vowel*(1-fv)+contact*fv)
