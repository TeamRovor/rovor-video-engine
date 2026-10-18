"""Original separate brow drawings with held, word-anchored acting accents."""
import json
import cv2
import numpy as np
from PIL import Image
from layered_cartoon_head import LayeredCartoonHead,ROOT
from painted_character import rotation
from painted_timing import flowing_track
from speech_planner import planned_weights

# Authored acting decisions; the aligner supplies timing, not emotion inference.
CUES=[('ever',dict(leftRaise=4,rightRaise=5,leftTilt=-2,rightTilt=2)),
      ('tiny',dict(leftRaise=-1,rightRaise=7,leftTilt=-3,rightTilt=-4)),
      ('here',dict(leftRaise=3,rightRaise=5,leftTilt=1,rightTilt=-2))]

def expression_events(plan):
    events=[]
    for word,values in CUES:
        match=next((w for w in plan['words'] if w['word']==word),None)
        if match:events.append(dict(word=word,scriptIndex=match['scriptIndex'],start=match['start'],end=match['end'],values=values))
    return events

def brow_controls(t,plan):
    out=dict(leftRaise=0.,rightRaise=0.,leftTilt=0.,rightTilt=0.)
    for e in expression_events(plan):
        a=e['start'];b=e['end'];peak=(a+b)/2
        envelope=flowing_track(t,[(max(0,a-.22),0),(peak,1),(max(peak+.06,b+.12),1),(b+.45,0)])
        for name,v in e['values'].items():out[name]+=envelope*v
    return {k:float(np.clip(v,-8,8)) for k,v in out.items()}

class ExpressiveCartoonHead(LayeredCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);folder=root/'expression-rig'
        self.brow_meta=json.loads((folder/'manifest.json').read_text());self.clean=np.asarray(Image.open(folder/'browless-head.png').convert('RGBA'))
        self.repair=np.asarray(Image.open(folder/'repair-mask.png'))>0
        self.forehead=np.asarray(Image.open(folder/'forehead-mask.png')).astype('float32')/255
        self.brows={n:np.asarray(Image.open(folder/f'brow-{n}.png').convert('RGBA')).astype('float32') for n in ('left','right')}
    def weights(self,weights,expression=None,shape_weights=None,geometry_weights=None):
        out=np.asarray(super().weights(weights,shape_weights=shape_weights,geometry_weights=geometry_weights)).copy();out[self.repair,:3]=self.clean[self.repair,:3]
        canvas=out.astype('float32');canvas[:,:,:3]*=canvas[:,:,3:4]/255
        expression=expression or {}
        for name,raw in self.brows.items():
            m=rotation(self.brow_meta['pivots'][name],float(np.clip(expression.get(name+'Tilt',0),-8,8)));m[1,2]-=float(np.clip(expression.get(name+'Raise',0),-8,8))
            art=raw.copy();art[:,:,:3]*=art[:,:,3:4]/255
            art=cv2.warpAffine(art,m[:2],(512,512),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);art*=self.forehead[:,:,None]
            canvas=art+canvas*(1-art[:,:,3:4]/255)
        canvas[:,:,:3]*=255/np.maximum(canvas[:,:,3:4],1)
        result=np.clip(canvas,0,255).astype('uint8')
        changed=self.repair|(self.forehead>0)
        result[~changed]=out[~changed]
        return Image.fromarray(result)
    def at(self,t,plan):return self.weights(planned_weights(t,plan,plan['fallbackCues']),brow_controls(t,plan))
