"""Same-audio old/new FV comparison, with explicit review cuts."""
import argparse,json,cv2
from pathlib import Path
from PIL import Image,ImageDraw
from fv_cartoon_head import FVContactHead
from expressive_cartoon_head import ExpressiveCartoonHead,brow_controls
from speech_planner import planned_weights
from render_cartoon_head_study import font,HERE
SOURCE_FRAMES=list(range(35))+list(range(393,450))

def frame(old,new,plan,index):
    t=SOURCE_FRAMES[index]/48;w=planned_weights(t,plan,plan['fallbackCues']);expression=brow_controls(t,plan)
    im=Image.new('RGBA',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
    d.text((65,35),'OLD CONTACT',font=font(24),fill='#586775');d.text((715,35),'NEW LIP + UPPER-TEETH SURFACES',font=font(24),fill='#233442')
    im.alpha_composite(old.weights(w,expression),(50,75));im.alpha_composite(new.weights(w,expression),(700,75))
    active=next((p for p in plan['phonemes'] if p['start']<=t<p['end']),None);word=next((p['word'] for p in plan['words'] if p['start']<=t<p['end']),'pause')
    label='Opening sentence' if index<35 else 'Review cut: favicon'
    d.text((65,615),f'{label} · recording {t:.3f}s · {word} · '+(active['phone'] if active else 'pause'),font=font(23),fill='#365563')
    d.text((65,666),'Same timing and audio. New contact remains an anatomy candidate, not production approval.',font=font(18),fill='#586775')
    logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA');logo.thumbnail((50,50));im.alpha_composite(logo,(1160,643))
    return im.convert('RGB')
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=len(SOURCE_FRAMES));a=p.parse_args();plan=json.loads(a.plan.read_text());old=ExpressiveCartoonHead();new=FVContactHead();a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(old,new,plan,i).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=a.end,fps=48)))
