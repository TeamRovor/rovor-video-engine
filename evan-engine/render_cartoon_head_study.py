"""Native-resolution cartoon facial diagnostic, NOT a finished character scene."""
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from cartoon_head import CartoonHead
from english_articulation import cartoon_controls
from speech_planner import planned_weights
HERE=Path(__file__).resolve().parent

def font(size):
    return ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc',size)

def frame(head,plan,t,duration):
    im=Image.new('RGBA',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
    logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA');logo.thumbnail((70,70));im.alpha_composite(logo,(750,60))
    d.text((840,70),'ROVOR DIGITAL',font=font(28),fill='#233442')
    d.text((90,35),'CARTOON FACIAL MOTION STUDY',font=font(22),fill='#576575')
    w=planned_weights(t,plan,plan['fallbackCues']);im.alpha_composite(head.weights(w),(110,70))
    word=next((p['word'] for p in plan['words'] if p['start']<=t<p['end']),'')
    d.text((750,190),word,font=font(54),fill='#253d4a')
    active=next((p for p in plan['phonemes'] if p['start']<=t<p['end']),None)
    d.text((750,265),'Sound: '+(active['phone'] if active else 'pause'),font=font(24),fill='#586775')
    for i,(name,value) in enumerate(cartoon_controls(w).items()):
        y=330+i*34;d.text((750,y),name,font=font(18),fill='#586775');d.rectangle((950,y+3,1150,y+18),fill='#d7ddd8');d.rectangle((950,y+3,950+200*value,y+18),fill='#2e7684')
    rms=plan['audio']['rms'];step=plan['audio']['step'];reference=max(rms[:math.ceil(duration/step)]+[.001]);points=[]
    for x in range(1100):
        j=min(len(rms)-1,round(x/1099*duration/step));v=min(1,rms[j]/reference);points.append((90+x,635-35*v))
    d.line(points,fill='#698d95',width=2);x=90+1100*t/duration;d.line((x,584,x,654),fill='#b1693d',width=2)
    d.text((90,674),'Head component test — torso, hands and emotional acting are still to be built.',font=font(18),fill='#586775')
    return im.convert('RGB')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int);p.add_argument('--duration',type=float,default=4.8);p.add_argument('--fps',type=int,default=48);p.add_argument('--mouth-method',choices=('mesh','layers'),default='mesh');a=p.parse_args()
    plan=json.loads(a.plan.read_text())
    if a.mouth_method=='layers':
        from layered_cartoon_head import LayeredCartoonHead
        head=LayeredCartoonHead()
    else:head=CartoonHead()
    a.frames.mkdir(parents=True,exist_ok=True)
    end=a.end if a.end is not None else math.ceil(a.duration*a.fps)
    for i in range(a.start,end):frame(head,plan,i/a.fps,a.duration).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=end,fps=a.fps,component='cartoon head diagnostic')))
