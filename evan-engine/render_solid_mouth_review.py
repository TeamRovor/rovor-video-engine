"""Same-audio native-head comparison with actual sample-clock waveform."""
import argparse,json,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from fv_cartoon_head import FVContactHead
from solid_cartoon_head import SolidCavityHead
from render_cartoon_head_study import font

START=180;END=252;FPS=48
class Review:
    def __init__(self,plan,wav,rounding=False):
        self.plan=plan;self.old=FVContactHead();self.new=SolidCavityHead()
        self.titles=('BEFORE: fading cavity + smile','AFTER: solid opening')
        if rounding:
            from rounded_cartoon_head import RoundedCartoonHead
            self.old=SolidCavityHead();self.new=RoundedCartoonHead();self.titles=('BEFORE: energy also widens lips','AFTER: phone-driven rounding')
        with wave.open(str(wav)) as f:
            if f.getnchannels()!=1 or f.getsampwidth()!=2:raise ValueError('Expected mono PCM16 reference')
            self.rate=f.getframerate();samples=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
        self.strip=Image.new('RGB',(1180,54),'#e0e8e2');d=ImageDraw.Draw(self.strip)
        for x in range(1180):
            a=round((START/FPS+(END-START)/FPS*x/1180)*self.rate);b=round((START/FPS+(END-START)/FPS*(x+1)/1180)*self.rate);s=samples[a:b]
            if len(s):d.line((x,27-float(s.max())*24,x,27-float(s.min())*24),fill='#48636d')
    def frame(self,i):
        t=i/FPS;im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
        d.text((48,20),'“…instead of your logo.” · identical audio and word timing',font=font(26),fill='#233442')
        for x,title,h in [(48,self.titles[0],self.old),(720,self.titles[1],self.new)]:
            d.text((x,65),title,font=font(23),fill='#48636d');head=h.at(t,self.plan);im.paste(head,(x,100),head)
        im.paste(self.strip,(50,628));cursor=50+round((i-START)/(END-START)*1180);d.line((cursor,620,cursor,690),fill='#b65b3e',width=2)
        for w in self.plan['words']:
            if w['end']<START/FPS or w['start']>END/FPS:continue
            x=50+round((w['start']-START/FPS)/((END-START)/FPS)*1180)
            d.text((x,690),w['word'],font=font(17),fill='#48636d')
        d.text((50,593),f'Source time {t:.4f}s · waveform from original recording',font=font(18),fill='#657c83')
        return im
if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path);p.add_argument('--rounding',action='store_true');p.add_argument('--start',type=int,default=START);p.add_argument('--end',type=int,default=END);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,a.rounding);a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-START:06}.jpg',quality=97)
    print(json.dumps(dict(start=a.start,end=a.end,fps=FPS)))
