"""Optional lighter rounded source art on the existing contour/tongue rig."""
import numpy as np
from PIL import Image
from contour_cartoon_head import ContourCartoonHead
from layered_cartoon_head import ROOT

class LightLipCartoonHead(ContourCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.round_art={n:np.asarray(Image.open(root/f'light-lip-rig-v1/{n}.png').convert('RGBA')) for n in ['cavity','rim','interior-mask']}
