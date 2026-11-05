"""Opt-in registered peach lower-lip contact artwork, with unchanged timings."""
import json
import numpy as np
from PIL import Image
from material_cartoon_head import MaterialCartoonHead
from cartoon_head import landmarks,warp,POINTS
from expressive_cartoon_head import ROOT
from layered_cartoon_head import over

class SculptedContactHead(MaterialCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);folder=root/'fv-rig-v2';meta=json.loads((folder/'manifest.json').read_text())
        self.source_geometry=dict(self.geometry,G=tuple(meta['geometry']))
        self.source_points=landmarks('G',self.source_geometry)
        self.fv_layers={n:np.asarray(Image.open(folder/(n+'.png')).convert('RGBA')) for n in ('lip-contact','upper-teeth','lower-lip')}

    def contact_parts(self,target):
        destination=self.contact_target(target)
        lips=warp(self.fv_layers['lip-contact'],self.source_points,destination,2)
        teeth=warp(self.fv_layers['upper-teeth'],self.source_points,destination,2)
        volume=warp(self.fv_layers['lower-lip'],self.source_points,destination,2)
        # Opposite inner-ring landmarks give the actual aperture (the same Y
        # controls used by the jaw). Keep peach lip volume outside the opening.
        aperture=float(target[20,1]-target[28,1])
        cavity=warp(self.layers['cavity-outline'],POINTS['C'],self.oral_target(target,aperture),2)
        volume*=1-np.clip(cavity[:,:,3:4]/255,0,1)*self.cavity_visibility(aperture)
        return dict(lips=lips,teeth=teeth,lower_lip=volume)
    def contact_surface(self,target):
        parts=self.contact_parts(target)
        return over(parts['lower_lip'],over(parts['lips'],parts['teeth']))
