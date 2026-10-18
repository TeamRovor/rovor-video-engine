"""Word-anchored pointing with an independent index and a held listening pause."""
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_gesture_body import CartoonRoundedBody
from cartoon_hand import transformed_hand
from cartoon_index import IndexRig
from painted_character import arm_transforms
from painted_timing import flowing_track

REST_INDEX=np.array([-10.,60.,35.])

def scene_events(plan):
    words={}
    for word in plan.get('words',[]):words.setdefault(word['word'],word)
    out=[]
    if all(x in words for x in ('tiny','globe','here','logo')):
        out.append(dict(anchor='globe / up here',anticipate=words['tiny']['start']-.45,arrive=words['globe']['start']-.08,hold=words['here']['end']+.08,settle=words['logo']['end']+.45))
    if 'favicon' in words:
        w=words['favicon'];out.append(dict(anchor='favicon',anticipate=w['start']-.60,arrive=w['start']-.08,hold=w['end']+.08,settle=w['end']+.93))
    return out

def scene_controls(t,plan):
    events=scene_events(plan)
    def arm_track(base,back,point,delay=0):
        keys=[(0.,base)]
        for e in events:
            keys.extend([(e['anticipate']-.12,base),(e['anticipate']+.08,back),(e['arrive'],point),(e['hold'],point),(e['settle'],base)])
        return flowing_track(max(0,t-delay),keys)
    def extension(delay=0):
        keys=[(0.,0.)]
        for e in events:
            keys.extend([(e['anticipate']+.25,0.),(e['arrive']-.08,1.),(e['hold'],1.),(e['settle']-.1,0.)])
        return flowing_track(max(0,t-delay),keys)
    index=REST_INDEX*np.array([1-extension(),1-extension(.025),1-extension(.05)])
    return dict(right=[arm_track(-2.,-1.,-8.),arm_track(0.,5.,-34.,.035),arm_track(0.,6.,-30.,.065)],
        left=[arm_track(0.,-1.,2.),arm_track(0.,-2.,6.,.05),arm_track(0.,-1.,1.5,.09)],index=index.tolist(),
        head=flowing_track(t,[(0,0),(1.8,.4),(2.7,1.3),(3.6,-1),(4.8,0),(6.5,-1),(7.4,0),(8.7,.8),(9.2,.2),(9.65,-.5),(10.08,0)]),
        body_roll=flowing_track(t,[(0,0),(2.8,.35),(4.9,0),(8.6,.3),(9.8,0)]))

class CartoonSceneBody(CartoonRoundedBody):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.index_rig=IndexRig(root);self.palm=Image.open(root/'index-rig/palm.png').convert('RGBA')
    def layers(self,t,plan,controls=None):
        controls=scene_controls(t,plan) if controls is None else controls
        base=super().layers(t,plan,controls);out={};g=self.arms['right'].geometry;angles=controls['right']
        for name,im in base.items():
            if name=='hand-right':
                parent=arm_transforms(g,angles)[2]
                out['index-right']=self.index_rig.render(controls['index'],parent)
                out['palm-right']=transformed_hand(self.palm,g,angles)
            else:out[name]=im
        return out
    def render(self,t,plan,controls=None):
        return super().render(t,plan,scene_controls(t,plan) if controls is None else controls)

class CartoonMaterialSceneBody(CartoonSceneBody):
    """Same scene controls, with contact material interpolation enabled."""
    def __init__(self,root=ROOT):
        super().__init__(root)
        from material_cartoon_head import MaterialCartoonHead
        self.head=MaterialCartoonHead(root)
