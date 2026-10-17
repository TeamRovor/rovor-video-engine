"""Opt-in gesture study: independently attached wrist drawings.

The first body renderer remains a preserved baseline. Finger-pose drawings are
not individually rigged fingers, and hidden shoulder surfaces still need work.
"""
import json
import numpy as np
from PIL import Image
from cartoon_body import CartoonBody,CartoonArm,acting,ROOT
from cartoon_hand import split_hand,transformed_hand
from painted_timing import flowing_track

def pointing_acting(t):
    controls=acting(t)
    def track(keys,delay=0):return flowing_track(max(0,t-delay),keys)
    controls['right']=[track([(0,-1),(.8,-2),(1.8,-5),(2.8,-8),(3.7,-8),(4.8,-2)]),
        track([(0,0),(.8,2),(1.6,-10),(2.7,-34),(3.5,-34),(4.8,-4)],.035),
        track([(0,0),(1.5,2),(2.9,-30),(3.8,-30),(4.8,0)],.08)]
    controls['left']=[v*.45 for v in controls['left']]
    return controls

class CartoonGestureBody(CartoonBody):
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root)
        self.hand_meta=json.loads((root/'hand-rig/manifest.json').read_text());self.pose=pose
        self.hands={};arms={}
        for name,g in self.meta['arms'].items():
            g=dict(g,wrist=self.hand_meta['wrists'][name])
            im=Image.open(root/f'body-rig/arm-{name}.png').convert('RGBA');arm,hand=split_hand(im,g)
            arms[name]=CartoonArm(arm,g);self.hands[name]={'open':hand}
        self.arms=arms
        self.hands['right']['point']=Image.open(root/'hand-rig/right-point.png').convert('RGBA')
    def layers(self,t,plan,controls=None):
        controls=pointing_acting(t) if controls is None else controls
        # Parent supplies the same head registration and independent torso.
        layers=super().layers(t,plan,controls);out={'torso':layers['torso']}
        for name,arm in self.arms.items():
            pose=controls.get(name+'Hand',self.pose if name=='right' else 'open')
            if pose not in self.hands[name]:raise ValueError('Unsupported hand pose: '+name+' '+pose)
            out['hand-'+name]=transformed_hand(self.hands[name][pose],arm.geometry,controls.get(name,(0,0,0)))
            out['arm-'+name]=layers['arm-'+name]
        out['head']=layers['head'];return out
    def render(self,t,plan,controls=None):
        return super().render(t,plan,pointing_acting(t) if controls is None else controls)

class CartoonSocketBody(CartoonGestureBody):
    """Local underarm source replacement, preserving the original center art."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        self.torso=Image.open(root/'socket-rig/torso.png').convert('RGBA');self.socket_review=True

class CartoonExpressionBody(CartoonSocketBody):
    """Opt-in authored brows on the local-underarm gesture rig."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        from expressive_cartoon_head import ExpressiveCartoonHead
        self.head=ExpressiveCartoonHead(root)

class CartoonFVBody(CartoonExpressionBody):
    """Opt-in relaxed F/V contact candidate on the current expressive rig."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        from fv_cartoon_head import FVContactHead
        self.head=FVContactHead(root);self.fv_review=True
