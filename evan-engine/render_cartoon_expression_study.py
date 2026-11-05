"""Native head close-up for word-anchored brow acting and existing speech."""
import argparse,json,cv2
from pathlib import Path
from PIL import ImageDraw
from expressive_cartoon_head import ExpressiveCartoonHead,brow_controls
from render_cartoon_head_study import frame as head_frame,font

def frame(head,plan,t):
    im=head_frame(head,plan,t,4.8125);d=ImageDraw.Draw(im)
    d.rectangle((55,20,650,65),fill='#f3eee2');d.text((90,35),'BROW + SPEECH ACTING STUDY',font=font(22),fill='#576575')
    d.rectangle((55,658,1230,715),fill='#f3eee2');d.text((90,674),'Original brows move separately. Hair/glasses limit range; face and mouth cleanup remain.',font=font(17),fill='#586775')
    c=brow_controls(t,plan);d.text((750,140),f'Brow raise: L {c["leftRaise"]:.1f} / R {c["rightRaise"]:.1f}',font=font(20),fill='#586775')
    return im
class TimedHead:
    def __init__(self,head,plan,t):self.head=head;self.plan=plan;self.t=t
    def weights(self,w):return self.head.weights(w,brow_controls(self.t,self.plan))
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=231);a=p.parse_args();plan=json.loads(a.plan.read_text());head=ExpressiveCartoonHead();a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(TimedHead(head,plan,i/48),plan,i/48).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=a.end,fps=48)))
