"""First bounded cartoon body acting study; optional and not a release renderer."""
import argparse,json,math
import cv2
from pathlib import Path
from PIL import Image,ImageDraw
from cartoon_body import CartoonBody
from render_cartoon_head_study import font,HERE

def frame(body,plan,t):
    im=Image.new('RGBA',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
    d.ellipse((-200,570,650,850),fill='#d9e3dc')
    figure=body.render(t,plan);figure=figure.resize((849,891),Image.Resampling.LANCZOS);im.alpha_composite(figure,(-120,30))
    logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA');logo.thumbnail((52,52));im.alpha_composite(logo,(684,50));d.text((755,62),'ROVOR DIGITAL',font=font(25),fill='#233442')
    d.text((685,158),'Small detail.',font=font(43),fill='#233442');d.text((685,210),'Visible difference.',font=font(43),fill='#233442')
    d.rounded_rectangle((685,310,1195,528),radius=20,fill='#ffffff',outline='#bdc8c6',width=2)
    d.rounded_rectangle((685,310,1195,366),radius=20,fill='#dce6e2');d.rectangle((687,344,1193,366),fill='#dce6e2')
    for x in [708,727,746]:d.ellipse((x,329,x+7,336),fill='#829c99')
    # The narration asks why a globe appears instead of a logo. Keep that
    # actual problem visible; replacing the favicon belongs to a later shot.
    d.rounded_rectangle((778,320,1112,359),radius=9,fill='#ffffff')
    d.ellipse((791,328,814,351),outline='#49717b',width=2);d.arc((797,328,808,351),0,360,fill='#49717b',width=1);d.line((791,339,814,339),fill='#49717b',width=1)
    d.text((826,328),'Your website',font=font(18),fill='#46616b')
    d.text((719,399),'That tiny browser globe?',font=font(26),fill='#314b58');d.text((719,446),'It could be your brand.',font=font(23),fill='#62808a')
    d.text((45,660),'FIRST BODY RIG STUDY',font=font(18),fill='#48636d');d.text((685,603),'Independent shoulders, elbows and wrists',font=font(21),fill='#48636d');d.text((685,636),'Open hands only · shoulder cleanup pending',font=font(18),fill='#657c83')
    return im.convert('RGB')
if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=231);a=p.parse_args();plan=json.loads(a.plan.read_text());b=CartoonBody();a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(b,plan,i/48).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=a.end,fps=48)))
