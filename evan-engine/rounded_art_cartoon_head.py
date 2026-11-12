"""Candidate generated rounded cavity/rim under separate teeth/tongue layers."""
import cv2,numpy as np
from PIL import Image
from bounded_cartoon_head import BoundedCartoonHead
from layered_cartoon_head import ROOT,over
from cartoon_head import POINTS

def rounded_art_strength(w,shape_weights=None):
    # Art identity follows the current phone mixture; using the width lead/
    # release mixture left a second old outline during a fully rounded vowel.
    identity=np.asarray(w,float);identity=identity/identity.sum()
    return float(np.clip((identity[5]+identity[6])/max(1-identity[0],1e-9)*(1-w[1]-w[7]),0,1))

class RoundedArtCartoonHead(BoundedCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);self.round_art={n:np.asarray(Image.open(root/f'round-rig-v1/{n}.png').convert('RGBA')) for n in ['cavity','rim','interior-mask']}
    def cavity_surface(self,w,oral,shape_weights=None):
        old=super().cavity_surface(w,oral,shape_weights);strength=rounded_art_strength(w,shape_weights)
        if strength<=0:return old
        cavity=self.sample_surface(self.round_art['cavity'],POINTS['E'],oral,2)
        rim=self.sample_surface(self.round_art['rim'],POINTS['E'],oral,2)
        return old*(1-strength)+over(cavity,rim)*strength
    def interior_mask(self,cavity,w,oral,shape_weights=None):
        strength=rounded_art_strength(w,shape_weights)
        if strength<=0:return super().interior_mask(cavity,w,oral,shape_weights)
        old=super().cavity_surface(w,oral,shape_weights);old=super().interior_mask(old,w,oral,shape_weights)
        matte=self.sample_surface(self.round_art['interior-mask'],POINTS['E'],oral,2)
        inner=cv2.erode(matte[:,:,3],np.ones((3,3),np.uint8))[:,:,None]/255
        return old*(1-strength)+inner*strength
    def clip_interiors(self,teeth,tongue,interior,w,shape_weights=None):
        teeth,tongue=super().clip_interiors(teeth,tongue,interior,w,shape_weights)
        return teeth*(1-rounded_art_strength(w)),tongue
