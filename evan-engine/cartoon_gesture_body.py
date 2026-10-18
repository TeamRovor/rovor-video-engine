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

class CartoonNeckBody(CartoonFVBody):
    """One deforming neck surface beneath the untouched original collar."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        from cartoon_neck import collar_torso
        self.torso=collar_torso(self.torso);self.neck_review=True
    def head_layer(self,t,plan,controls):
        from cartoon_neck import split_head_neck,SCALE,TRANSLATE,PIVOT
        from speech_planner import planned_weights
        from cartoon_head import SYMBOLS
        w=planned_weights(t,plan,plan['fallbackCues']);delta=sum(float(v)*(self.head.geometry[s][8]-393) for s,v in zip(SYMBOLS,w))
        head,neck=split_head_neck(self.head.at(t,plan),delta)
        self._neck_layer=self.draw_neck(neck,controls.get('head',0),delta)
        head=head.resize((round(512*SCALE),round(512*SCALE)),Image.Resampling.LANCZOS);layer=Image.new('RGBA',(1464,1536));layer.alpha_composite(head,(int(TRANSLATE[0])+220,int(TRANSLATE[1])))
        return layer.rotate(controls.get('head',0),Image.Resampling.BICUBIC,center=(PIVOT[0]+220,PIVOT[1]))
    def draw_neck(self,neck,tilt,delta):
        from cartoon_neck import render_neck
        return render_neck(neck,tilt,delta)
    def layers(self,t,plan,controls=None):
        layers=super().layers(t,plan,controls)
        return {'neck':self._neck_layer,**layers}


class CartoonNeckArtBody(CartoonNeckBody):
    """Registered extended-neck art, keeping all original facial acting."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        self.torso=Image.open(root/'neck-art-rig/torso.png').convert('RGBA')
        self.neck_art=Image.open(root/'neck-art-rig/neck.png').convert('RGBA');self.neck_art_review=True
    def draw_neck(self,neck,tilt,delta):
        from cartoon_neck import render_neck,jaw_cut
        raw=np.asarray(self.neck_art).copy();yy,xx=np.mgrid[:512,:512]
        # Upper neck retains the current jaw's original ink and shadow. The
        # new drawing supplies broad lower overlap, not a new face sprite.
        raw[:,:,3]=(raw[:,:,3]*np.clip((yy-jaw_cut(xx,delta)+3)/5,0,1)).astype('uint8')
        plate=Image.fromarray(raw);plate.alpha_composite(neck)
        return render_neck(plate,tilt,delta,bounds=(195,355),spread=.25)


class CartoonSolidMouthBody(CartoonNeckArtBody):
    """Opt-in solid cavity during narrow vowel transitions."""
    def __init__(self,root=ROOT,pose='point'):
        super().__init__(root,pose)
        from solid_cartoon_head import SolidCavityHead
        self.head=SolidCavityHead(root);self.solid_mouth_review=True
