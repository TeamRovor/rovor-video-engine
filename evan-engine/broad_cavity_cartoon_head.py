"""Optional broad cavity/rim art without a baked red floor."""
import cv2,numpy as np
from PIL import Image
from light_lip_cartoon_head import LightLipCartoonHead
from layered_cartoon_head import ROOT,over
from cartoon_head import POINTS

class BroadCavityCartoonHead(LightLipCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.broad_art={n:np.asarray(Image.open(root/f'broad-rig-v1/{n}.png').convert('RGBA')) for n in ['cavity','rim','interior-mask']}
    def broad_cavity_surface(self,oral):
        cavity=self.sample_surface(self.broad_art['cavity'],POINTS['C'],oral,2)
        rim=self.sample_surface(self.broad_art['rim'],POINTS['C'],oral,2)
        return over(cavity,rim)
    def broad_interior_mask(self,cavity,oral):
        matte=self.sample_surface(self.broad_art['interior-mask'],POINTS['C'],oral,2)
        return cv2.erode(matte[:,:,3],np.ones((3,3),np.uint8))[:,:,None]/255
