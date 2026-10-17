"""Opt-in relaxed labiodental contact with separate upper-teeth/lip surfaces."""
import json
import numpy as np
from PIL import Image
from expressive_cartoon_head import ExpressiveCartoonHead,ROOT
from cartoon_head import GEOMETRY,POINTS,landmarks,warp
from layered_cartoon_head import over

class FVContactHead(ExpressiveCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);folder=root/'fv-rig';meta=json.loads((folder/'manifest.json').read_text())
        self.geometry=dict(GEOMETRY,G=tuple(meta['geometry']));self.points=dict(POINTS,G=landmarks('G',self.geometry))
        self.fv_layers={n:np.asarray(Image.open(folder/(n+'.png')).convert('RGBA')) for n in ('lip-contact','upper-teeth')}
    def contact_target(self,target):
        # A fading consonant plate must not inflate into a large vowel cavity.
        contact=target.copy();height=float(np.ptp(contact[:16,1]));scale=min(1.,15/max(height,1));cy=float((contact[0,1]+contact[8,1])/2)
        contact[:32,1]=cy+(contact[:32,1]-cy)*scale
        return contact
    def contact_surface(self,target):
        contact=self.contact_target(target)
        lips=warp(self.fv_layers['lip-contact'],self.points['G'],contact,2)
        teeth=warp(self.fv_layers['upper-teeth'],self.points['G'],contact,2)
        return over(lips,teeth)
