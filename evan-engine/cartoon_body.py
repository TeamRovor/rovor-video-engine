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
from cartoon_wrist import WristPlate, without_hand
from cartoon_expression import upper_face
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


def narration_acting(t):
    """Authored favicon-take acting in seconds, with intentional held attitudes.

    Preserve acting() as the original 4.8125-second comparison baseline.
    These gestures follow the known recording, not arbitrary keyword guesses.
    """
    def track(keys, delay=0):
        return flowing_track(max(0, t-delay), keys)
    left = [(0,0),(.55,0),(1.4,3),(2.1,3),(2.7,1),(4.7,1),
            (5.3,-1),(6.9,-1),(7.6,3),(8.7,3),(9.1,0),
            (10.1,5),(12.7,5),(13.5,2),(14.7,2),
            (15.4,1),(17.2,1),(18.1,3),(19.2,3),
            (20.1,2),(21.4,2),(21.85,0)]
    right = [(0,0),(.65,0),(1.45,-2),(2,-2),(2.65,-10),(4.45,-10),
             (5.1,-1),(6.8,-1),(7.6,-4),(8.6,-4),(9.1,-1),
             (10,-7),(12.7,-7),(13.4,-4),(14.5,-4),
             (15.2,-2),(16.8,-2),(17.7,-5),(19,-5),
             (20,-3),(21.4,-3),(21.85,0)]
    head = [(0,0),(.5,0),(1.1,1.2),(1.8,1.2),(2.35,-1.8),(4.3,-1.8),
            (4.95,.8),(6.8,.8),(7.3,-.8),(8.8,-.8),(9.5,.5),
            (12.6,.5),(13.2,-1),(14.6,-1),(15.1,.8),(16.9,.8),
            (17.5,-.6),(19.1,-.6),(19.8,.7),(21.3,.7),(22.047375,0)]
    # Head leads the arm, forearm follows the shoulder, wrist settles last.
    return dict(left=[track(left),track([(a,v*2) for a,v in left],.055),
                      track([(a,v*.5) for a,v in left],.11)],
                right=[track(right),track([(a,v*2.5) for a,v in right],.06),
                       track([(a,v*.5) for a,v in right],.12)],
                head=track(head), right_hand='point' if 2.35<=t<4.75 else 'open',
                brow_left=track([(0,0),(.7,0),(1.2,2.8),(4.4,2.8),(5.1,-1),
                                 (6.8,-1),(7.5,1.5),(8.8,1.5),(9.4,0),
                                 (14.5,0),(15.2,2),(18.8,2),(19.7,1),(22.047375,0)]),
                brow_right=track([(0,0),(.7,0),(1.2,.5),(4.4,.5),(5.1,2),
                                  (6.8,2),(7.5,1.5),(8.8,1.5),(9.4,0),
                                  (14.5,0),(15.2,2),(18.8,2),(19.7,1),(22.047375,0)]),
                body_roll=track([(0,0),(1.4,.45),(4.4,.45),(5.1,-.35),
                                 (8.7,-.35),(10,.55),(14.5,.55),
                                 (15.3,-.25),(19,-.25),(20,.35),
                                 (21.4,.35),(22.047375,0)]))

class CartoonBody:
    def __init__(self,root=ROOT,contact_candidate=False):
        self.meta=json.loads((root/'body-rig/manifest.json').read_text())
        self.torso=Image.open(root/'body-rig/torso.png').convert('RGBA')
        self.arms={n:CartoonArm(Image.open(root/f'body-rig/arm-{n}.png').convert('RGBA'),g) for n,g in self.meta['arms'].items()}
        self.head=LayeredCartoonHead(root,contact_candidate=contact_candidate)
        hand_meta=root/'hand-source/manifest.json'
        self.point_hand=None
        if hand_meta.exists():
            plate=json.loads(hand_meta.read_text())['point-right']
            geo=self.meta['arms']['right']
            self.point_hand=WristPlate(Image.open(root/'hand-source'/plate['file']),plate,geo)
            original=Image.open(root/'body-rig/arm-right.png').convert('RGBA')
            self.point_forearm=CartoonArm(without_hand(original,geo,plate.get('targetAttachment')),geo)
    def layers(self,t,plan,controls=None):
        controls=acting(t) if controls is None else controls
        layers={'torso':Image.new('RGBA',(1464,1536))};layers['torso'].alpha_composite(self.torso,(220,0))
        for name,arm in self.arms.items():
            pointing=name=='right' and controls.get('right_hand')=='point' and self.point_hand is not None
            if pointing:arm=self.point_forearm
            im,(x,y)=arm.render(controls.get(name,(0,0,0)))
            layer=Image.new('RGBA',(1464,1536));layer.alpha_composite(im,(x+220,y));layers['arm-'+name]=layer
            if pointing:
                im,(x,y)=self.point_hand.render(controls.get(name,(0,0,0)))
                layer.alpha_composite(im,(x+220,y))
        head=self.head.at(t,plan)
        head=upper_face(head,controls.get('brow_left',0),controls.get('brow_right',0))
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
