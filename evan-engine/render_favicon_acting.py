"""Narration-specific cartoon acting review in native 1080p landscape/vertical.

Experimental artwork and timing; not an approved production renderer.
"""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw
from cartoon_body import CartoonBody, narration_acting
from render_cartoon_head_study import font, HERE
from render_profile import DEFAULT_FPS, LANDSCAPE, VERTICAL, frame_count


def stage(t):
    if t<4.72:return ('That tiny browser globe?', 'Your brand belongs here.')
    if t<9.04:return ('Meet your favicon.', 'A small detail with a purpose.')
    if t<14.8:return ('Your brand. In the tab.', 'A tiny version of your logo.')
    if t<19.44:return ('Small detail.', 'A more finished website.')
    return ('ROVOR DIGITAL', 'Go beyond your current reach.')


class FaviconScene:
    def __init__(self,plan,vertical=False):
        self.plan=plan;self.vertical=vertical;self.body=CartoonBody()
        self.size=VERTICAL if vertical else LANDSCAPE
        self.logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA')
        self.icons={s:self.logo.resize((s,round(s*self.logo.height/self.logo.width)),Image.Resampling.LANCZOS) for s in (34,48,72)}

    def icon(self,im,x,y,size,branded):
        if branded:
            im.alpha_composite(self.icons[size],(x,y))
        else:
            d=ImageDraw.Draw(im);d.ellipse((x,y,x+size,y+size),outline='#49717b',width=3)
            d.ellipse((x+size*.3,y,x+size*.7,y+size),outline='#49717b',width=2)
            d.line((x,y+size/2,x+size,y+size/2),fill='#49717b',width=2)

    def browser(self,im,box,t):
        d=ImageDraw.Draw(im);x,y,w,h=box
        d.rounded_rectangle((x,y,x+w,y+h),radius=24,fill='white',outline='#bfccc9',width=3)
        d.rounded_rectangle((x+20,y+18,x+w-20,y+100),radius=14,fill='#e0e9e5')
        self.icon(im,x+42,y+36,48,t>=10.15)
        d.text((x+115,y+40),'Your website',font=font(32),fill='#233442')
        title,subtitle=stage(t)
        d.text((x+36,y+150),title,font=font(38),fill='#233442')
        d.text((x+36,y+211),subtitle,font=font(27),fill='#62808a')
        # A finite reveal follows the explanation; there is no perpetual pulse.
        if 2.35<=t<4.75:
            d.rounded_rectangle((x+29,y+23,x+103,y+95),radius=12,outline='#ba7b42',width=4)
        if t>=10.15:
            d.text((x+36,y+h-65),'FAVICON',font=font(21),fill='#62808a')

    def render(self,t,figure=None):
        im=Image.new('RGBA',self.size,'#f3eee2');d=ImageDraw.Draw(im)
        if figure is None:figure=self.body.render(t,self.plan,narration_acting(t))
        if self.vertical:
            d.ellipse((-300,700,1350,2050),fill='#e0e7de')
            im.alpha_composite(self.icons[48],(72,65))
            d.text((145,74),'ROVOR DIGITAL',font=font(32),fill='#233442')
            d.text((72,170),'SMALL DETAIL.',font=font(61),fill='#233442')
            d.text((72,246),'VISIBLE DIFFERENCE.',font=font(49),fill='#233442')
            figure=figure.resize((1200,1259),Image.Resampling.LANCZOS)
            figure=figure.crop((0,0,1200,1035))
            im.alpha_composite(figure,(-150,345))
            # A small tab-level icon sits ahead of the pointing finger.
            if 2.35<=t<4.75:
                d.rounded_rectangle((950,850,1065,965),radius=22,fill='white',outline='#bfccc9',width=3)
                self.icon(im,984,882,48,False)
            self.browser(im,(65,1380,950,370),t)
            d.text((72,1810),'ANIMATION DEVELOPMENT STUDY',font=font(23),fill='#657c83')
        else:
            d.ellipse((-350,760,1100,1600),fill='#e0e7de')
            figure=figure.resize((1560,1637),Image.Resampling.LANCZOS)
            im.alpha_composite(figure,(-210,20))
            im.alpha_composite(self.icons[48],(1040,72))
            d.text((1120,78),'ROVOR DIGITAL',font=font(37),fill='#233442')
            d.text((1000,230),'Small detail.',font=font(61),fill='#233442')
            d.text((1000,307),'Visible difference.',font=font(61),fill='#233442')
            self.browser(im,(1200,660,650,340),t)
            d.text((1200,1040),'ANIMATION DEVELOPMENT STUDY',font=font(23),fill='#657c83')
        return im.convert('RGB')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--vertical',action='store_true');p.add_argument('--fps',type=int,default=DEFAULT_FPS)
    p.add_argument('--duration',type=float,default=22.047375)
    p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int)
    a=p.parse_args();total=frame_count(a.duration,a.fps)
    end=a.end if a.end is not None else total
    if not 0<=a.start<end<=total:p.error('Expected 0 <= start < end <= total frames')
    fingerprint={'planSha256':hashlib.sha256(a.plan.read_bytes()).hexdigest(),
                 'fps':a.fps,'size':list(VERTICAL if a.vertical else LANDSCAPE),
                 'duration':a.duration,'renderer':'favicon-acting-v1'}
    a.frames.mkdir(parents=True,exist_ok=True);manifest=a.frames/'render-profile.json'
    if manifest.exists():
        if json.loads(manifest.read_text())!=fingerprint:p.error('Output folder belongs to a different render profile')
    elif any(a.frames.glob('*.jpg')):p.error('Existing frames have no render profile; use a new folder')
    else:manifest.write_text(json.dumps(fingerprint,indent=2)+'\n')
    scene=FaviconScene(json.loads(a.plan.read_text()),a.vertical)
    for i in range(a.start,end):
        target=a.frames/f'{i:06}.jpg'
        scene.render(i/a.fps).save(target,quality=96)
    print(json.dumps(dict(start=a.start,end=end,**fingerprint)))


if __name__=='__main__':main()
