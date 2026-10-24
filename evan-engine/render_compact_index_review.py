"""Native-size right-arm comparison through one narrated point and settle."""
import argparse,json,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from cartoon_scene import CartoonMaterialSceneBody,scene_controls
from compact_cartoon_scene import CompactCartoonSceneBody,compact_controls
from cartoon_hand import transformed_hand
from painted_character import arm_transforms
from render_cartoon_head_study import font
START=384;END=489;FPS=48;CROP=(870,470,1420,1010)

class Review:
    def __init__(self,plan,wav,bodies=None,titles=None,heading=None,control_functions=None):
        self.plan=plan;self.bodies=bodies or [CartoonMaterialSceneBody(),CompactCartoonSceneBody()]
        self.titles=titles or ['CURRENT: long curl','STUDY: shallow projected curl']
        self.heading=heading or 'Point to pause · same artwork, audio and arm acting'
        self.control_functions=control_functions or [scene_controls,compact_controls]
        with wave.open(str(wav)) as f:
            if f.getnchannels()!=1 or f.getsampwidth()!=2:raise ValueError('Expected mono PCM16')
            rate=f.getframerate();samples=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
        self.strip=Image.new('RGB',(1180,40),'#e0e8e2');d=ImageDraw.Draw(self.strip)
        for x in range(1180):
            a=round((START/FPS+(END-START)/FPS*x/1180)*rate);b=round((START/FPS+(END-START)/FPS*(x+1)/1180)*rate);s=samples[a:b]
            if len(s):d.line((x,20-float(s.max())*18,x,20-float(s.min())*18),fill='#48636d')
    def arm(self,body,controls):
        arm=body.arms['right'];parent=arm_transforms(arm.geometry,controls['right'])[2]
        out=body.index_rig.render(controls['index'],parent)
        if not getattr(body,'joined_wrist',False):out.alpha_composite(transformed_hand(body.palm,arm.geometry,controls['right']))
        fore,(x,y)=arm.render(controls['right']);out.alpha_composite(fore,(x+220,y));return out.crop(CROP)
    def frame(self,i):
        t=i/FPS;im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
        d.text((48,18),self.heading,font=font(26),fill='#233442')
        for x,title,body,controls in zip([48,682],self.titles,self.bodies,[f(t,self.plan) for f in self.control_functions]):
            d.text((x,60),title,font=font(22),fill='#48636d');arm=self.arm(body,controls);im.paste(arm,(x,95),arm)
        im.paste(self.strip,(50,652));cursor=50+round((i-START)/(END-START)*1180);d.line((cursor,645,cursor,698),fill='#b65b3e',width=2)
        d.text((50,699),f'Original recording {t:.4f}s · native body pixels · not a lip-sync assessment',font=font(15),fill='#48636d')
        return im
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=START);p.add_argument('--end',type=int,default=END);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav);a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-START:06}.jpg',quality=97)
