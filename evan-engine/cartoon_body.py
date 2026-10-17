"""Opt-in first cartoon FK body study, with continuous independent arms.

Original shoulder overlap supports modest angles only. Hands have no finger rig.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from painted_character import ArmMesh
from painted_timing import flowing_track
from layered_cartoon_head import LayeredCartoonHead
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'

class CartoonArm(ArmMesh):
    def __init__(self,image,geometry):
        super().__init__(image,geometry)
        # Interpolate associated color to avoid dark fringes on moving alpha.
        self.image=self.image.astype('float32')
        self.image[:,:,:3]*=self.image[:,:,3:4]/255
        self.image=np.clip(self.image,0,255).astype('uint8')
    def render(self,angles):
        image,xy=super().render(angles)
        raw=np.asarray(image).astype('float32')
        raw[:,:,:3]*=255/np.maximum(raw[:,:,3:4],1)
        return Image.fromarray(np.clip(raw,0,255).astype('uint8')),xy

def acting(t):
    def track(keys,delay=0):return flowing_track(max(0,t-delay),keys)
    left=[(0,0),(.55,0),(1.35,4),(2.2,6),(3.1,3),(4.8,0)]
    right=[(0,0),(.8,0),(1.6,-3),(2.6,-6),(3.8,-4),(4.8,0)]
    return dict(left=[track(left),track([(a,v*3) for a,v in left],.035),track([(a,v*.6) for a,v in left],.085)],
        right=[track(right),track([(a,v*3) for a,v in right],.04),track([(a,v*.6) for a,v in right],.09)],
        head=track([(0,0),(.8,1.4),(1.8,-1.1),(3,1),(4.8,0)]),
        body_roll=track([(0,0),(1.5,.6),(2.8,-.5),(4.8,0)]))

class CartoonBody:
    def __init__(self,root=ROOT):
        self.meta=json.loads((root/'body-rig/manifest.json').read_text())
        self.torso=Image.open(root/'body-rig/torso.png').convert('RGBA')
        self.arms={n:CartoonArm(Image.open(root/f'body-rig/arm-{n}.png').convert('RGBA'),g) for n,g in self.meta['arms'].items()}
        self.head=LayeredCartoonHead(root)
    def layers(self,t,plan,controls=None):
        controls=acting(t) if controls is None else controls
        layers={'torso':Image.new('RGBA',(1464,1536))};layers['torso'].alpha_composite(self.torso,(220,0))
        for name,arm in self.arms.items():
            im,(x,y)=arm.render(controls.get(name,(0,0,0)))
            layer=Image.new('RGBA',(1464,1536));layer.alpha_composite(im,(x+220,y));layers['arm-'+name]=layer
        head=self.head.at(t,plan)
        raw=np.asarray(head).copy();raw[440:,:,3]=0
        raw[425:440,:,3]=(raw[425:440,:,3].astype(float)*np.linspace(1,0,15)[:,None]).astype('uint8')
        head=Image.fromarray(raw);tr=self.meta['head_transform'];s=tr['scale']
        head=head.resize((round(512*s),round(512*s)),Image.Resampling.LANCZOS)
        layer=Image.new('RGBA',(1464,1536));x,y=tr['translate'];layer.alpha_composite(head,(x+220,y))
        layers['head']=layer.rotate(controls.get('head',0),Image.Resampling.BICUBIC,center=(tr['pivot'][0]+220,tr['pivot'][1]))
        return layers
    def render(self,t,plan,controls=None):
        controls=acting(t) if controls is None else controls
        out=Image.new('RGBA',(1464,1536))
        for layer in self.layers(t,plan,controls).values():out.alpha_composite(layer)
        return out.rotate(controls.get('body_roll',0),Image.Resampling.BICUBIC,center=(732,950))
