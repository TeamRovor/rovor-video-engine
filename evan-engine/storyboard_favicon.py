"""Opt-in six-shot illustrated favicon story built around the original Evan rig.

Different compositions and actual object animation; NOT a studio-quality
approval. Never mutates the baseline renderer, source sprites or speech plan.
Designed for the exact verified 22.047375-second narration, not arbitrary MP3.
"""
import argparse
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw
from cartoon_body import CartoonBody, REVIEW_BODY_OPTIONS, narration_acting
from render_cartoon_head_study import font, HERE
from render_profile import LANDSCAPE, VERTICAL

DURATION = 22.047375
BEATS = (
    (0., 2.36, "hook"),
    (2.36, 4.72, "globe-closeup"),
    (4.72, 9.04, "problem-explained"),
    (9.04, 14.80, "favicon-reveal"),
    (14.80, 19.44, "website-payoff"),
    (19.44, DURATION, "brand-outro"),
)
INK = "#203445"
NAVY = "#152e42"
TEAL = "#2b8990"
GOLD = "#dfaa59"
PAPER = "#f5f0e5"


def clamp(x):
    return max(0., min(1., float(x)))


def smooth(x):
    t = clamp(x)
    return t*t*(3-2*t)


def shot_at(t):
    if not 0 <= t < DURATION + .00001:
        raise ValueError("Storyboard only supports the original 22-second narration")
    for lo,hi,name in BEATS:
        if lo <= t < hi:
            return (lo,hi,name)
    return BEATS[-1]


class StoryboardFaviconScene:
    """Renders original layered Evan plus authored object-animation shots."""

    def __init__(self, plan, vertical=False):
        self.plan = plan
        self.vertical = vertical
        self.size = VERTICAL if vertical else LANDSCAPE
        self.W, self.H = self.size
        self.body = CartoonBody(**REVIEW_BODY_OPTIONS)
        self.logo = Image.open(HERE.parent/"evan-character/brand/rovor-mark-black.png").convert("RGBA")
        self.fonts = {n: font(n) for n in (24, 28, 30, 34, 38, 42, 50, 56, 60, 68, 76, 92)}
        self._logos = {}

    def f(self, n):
        return self.fonts[n]

    def label(self, draw, at, text, size=42, color=INK, anchor=None):
        draw.text((int(at[0]),int(at[1])),str(text),font=self.f(size),fill=color,anchor=anchor)

    def mark(self, image, x, y, width):
        width = max(8, int(width))
        if width not in self._logos:
            h=max(8,round(width*self.logo.height/self.logo.width))
            self._logos[width]=self.logo.resize((width,h),Image.Resampling.LANCZOS)
        image.alpha_composite(self._logos[width],(int(x),int(y)))

    def globe(self, draw, x, y, r, color="#52777e"):
        x,y,r=int(x),int(y),int(r)
        box=(x-r,y-r,x+r,y+r)
        draw.ellipse(box,outline=color,width=max(3,r//12))
        draw.ellipse((x-r//2,y-r,x+r//2,y+r),outline=color,width=max(2,r//17))
        draw.line((x-r,y,x+r,y),fill=color,width=max(3,r//14))
        draw.arc((x-r,y-r//2,x+r,y+r//2),0,180,fill=color,width=max(2,r//17))

    def browser(self, image, rect, branded=False, highlight=False, title="YOUR WEBSITE", scale=1):
        x,y,w,h=map(int,rect)
        d=ImageDraw.Draw(image)
        radius=max(10,round(20*scale))
        d.rounded_rectangle((x,y,x+w,y+h),radius=radius,fill="white",outline="#b8ccc7",width=max(2,round(3*scale)))
        bar_h=round(min(h*.23,110))
        d.rounded_rectangle((x+8,y+8,x+w-8,y+bar_h),radius=max(8,radius//2),fill="#deebe8")
        sz=max(25,round(39*scale))
        icon_x=x+round(40*scale);icon_y=y+round(35*scale)
        if branded:self.mark(image,icon_x,icon_y,sz)
        else:self.globe(d,icon_x+sz//2,icon_y+sz//2,sz//2)
        self.label(d,(x+round(105*scale),y+round(33*scale)),title,28 if scale<=1 else 34,INK)
        if highlight:
            d.rounded_rectangle((icon_x-12,icon_y-12,icon_x+sz+12,icon_y+sz+12),
                                radius=12,outline="#dc9350",width=5)
        # Draw neutral website wireframe. No fake clients or statistics.
        top=y+bar_h+round(36*scale)
        usable=max(0,h-(top-y)-45)
        if usable>70:
            d.rounded_rectangle((x+35,top,x+w-35,top+min(round(usable*.35),100)),
                                radius=10,fill="#edf2ef")
            d.rounded_rectangle((x+35,top+min(round(usable*.35),100)+22,
                                 x+int(w*.63),top+min(round(usable*.35),100)+40),
                                radius=7,fill="#d3dfdf")
            d.rounded_rectangle((x+35,top+min(round(usable*.35),100)+54,
                                 x+int(w*.47),top+min(round(usable*.35),100)+72),
                                radius=7,fill="#e2e9e7")

    def background(self, image, name):
        d=ImageDraw.Draw(image)
        d.rectangle((0,0,self.W,self.H),fill=NAVY if name=="brand-outro" else PAPER)
        if name!="brand-outro":
            d.ellipse((-430,self.H-380,720,self.H+580),fill="#e3e9df")
            d.ellipse((self.W-320,-340,self.W+370,380),fill="#e4ece8")
        else:
            d.ellipse((-300,-300,self.W//2,self.H//2),fill="#1c4055")
            d.ellipse((self.W-500,self.H-500,self.W+300,self.H+300),fill="#1c4055")

    def enter(self, t, start, travel=180):
        return int((1-smooth((t-start)/.48))*travel)

    def character(self, image, t, figure, x, y, width, scene_start, mirror=False):
        if figure is None:
            figure=self.body.render(t,self.plan,narration_acting(t))
        width=int(width);height=round(width*figure.height/figure.width)
        portrait=figure.resize((width,height),Image.Resampling.LANCZOS)
        if mirror:portrait=portrait.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        move=self.enter(t,scene_start,95)
        image.alpha_composite(portrait,(int(x),int(y+move)))

    def arrow(self, d, x, y, magnitude=1):
        x,y=int(x),int(y);s=int(22*magnitude)
        d.polygon(((x,y),(x+s//3,y+3*s),(x+s,y+2*s),(x+int(s*1.5),y+int(s*2.4)),
                   (x+2*s,y+int(s*2.2)),(x+int(s*1.5),y+int(s*1.5)),(x+3*s,y+s//2)),
                  fill=NAVY,outline="white",width=2)

    def render(self,t,figure=None):
        start,end,name=shot_at(t)
        im=Image.new("RGBA",self.size)
        self.background(im,name)
        d=ImageDraw.Draw(im)
        vertical=self.vertical
        W,H=self.size
        appear=smooth((t-start)/.5)
        if name=="hook":
            if vertical:
                self.label(d,(65,90),"YOUR WEBSITE",68)
                self.label(d,(65,175),"HAS THIS?",76)
                self.browser(im,(65,335,950,565),False,False,"YOUR WEBSITE",1.45)
                self.character(im,t,figure,130,950,855,start)
                self.label(d,(80,1800),"LOOK AT THE BROWSER TAB",34)
            else:
                self.label(d,(100,115),"YOU OPEN YOUR WEBSITE...",60)
                x=80+self.enter(t,start,320)
                self.browser(im,(x,335,1200,565),False,False,"YOUR WEBSITE",1.7)
                self.character(im,t,figure,1330,280,700,start)
                self.label(d,(115,925),"BUT SOMETHING LOOKS OFF.",38)
        elif name=="globe-closeup":
            if vertical:
                self.label(d,(65,75),"THAT TINY GLOBE?",68)
                self.label(d,(65,160),"NOT YOUR LOGO.",56)
                self.browser(im,(100,400,885,425),False,True,"BROWSER TAB",1.8)
                cx=540;cy=1160
                d.ellipse((cx-285,cy-285,cx+285,cy+285),fill="white",outline=GOLD,width=13)
                self.globe(d,cx,cy,160)
                self.arrow(d,cx+155,cy+115,1.4)
                self.character(im,t,figure,80,1430,510,start)
            else:
                self.label(d,(130,110),"WAIT—WHAT'S THAT?",76)
                self.browser(im,(100,310,1050,550),False,True,"YOUR WEBSITE",1.45)
                cx=1420;cy=520
                zoom=smooth((t-start)/.65)
                r=round(180+60*zoom)
                d.ellipse((cx-r,cy-r,cx+r,cy+r),fill="white",outline=GOLD,width=14)
                self.globe(d,cx,cy,round(r*.54))
                d.line((cx-r+32,cy+r-35,cx-r-110,cy+r+125),fill=GOLD,width=18)
                self.label(d,(1190,845),"GENERIC ICON",50)
        elif name=="problem-explained":
            # A graphic comparison, not a static text card: icon appears in
            # its proper browser tab after the narration names the favicon.
            is_revealed=t>=7.59
            if vertical:
                self.label(d,(75,90),"THE PROBLEM",68)
                self.browser(im,(70,300,940,480),False,True,"BEFORE",1.4)
                if is_revealed:
                    reveal_x=1000-int(smooth((t-7.59)/.6)*930)
                    self.browser(im,(reveal_x,840,940,480),True,True,"WITH FAVICON",1.4)
                else:
                    d.rounded_rectangle((70,860,1010,1290),radius=25,fill="#d9e5e1")
                    self.label(d,(140,1000),"MISSING A FAVICON",50)
                self.character(im,t,figure,300,1250,850,start)
            else:
                self.label(d,(100,115),"IT'S NOT A RANDOM BROWSER THING.",60)
                x1=90
                self.browser(im,(x1,350,825,505),False,True,"BEFORE",1.25)
                if is_revealed:
                    dx=self.enter(t,7.59,350)
                    self.browser(im,(1000+dx,350,825,505),True,True,"AFTER",1.25)
                    self.label(d,(1240,898),"FAVICON",50,TEAL)
                else:
                    d.rounded_rectangle((1000,350,1825,855),radius=25,fill="#d6e5de")
                    self.label(d,(1090,565),"MISSING",76,INK)
                    self.label(d,(1090,675),"A FAVICON",76,INK)
        elif name=="favicon-reveal":
            if vertical:
                self.label(d,(70,85),"YOUR BRAND",68)
                self.label(d,(70,170),"IN A TINY TAB.",68)
                self.browser(im,(80,390,920,620),True,True,"FAVICON",1.6)
                cx=540;cy=1285
                rad=225
                d.ellipse((cx-rad,cy-rad,cx+rad,cy+rad),fill="white",outline=TEAL,width=10)
                self.mark(im,cx-145,cy-145,290)
                self.label(d,(92,1695),"SMALL IMAGE. CLEAR IDENTITY.",42)
            else:
                self.label(d,(100,120),"THAT'S A FAVICON.",76)
                x=140+self.enter(t,start,420)
                self.browser(im,(x,350,1050,545),True,True,"YOUR WEBSITE",1.45)
                cx=1535;cy=580
                r=200
                d.ellipse((cx-r,cy-r,cx+r,cy+r),fill="white",outline=TEAL,width=12)
                self.mark(im,cx-110,cy-110,220)
                self.label(d,(1250,835),"YOUR BRAND",50,INK)
        elif name=="website-payoff":
            # Tab identities stay stable while cards slide into the comparison.
            if vertical:
                self.label(d,(80,120),"ONE SMALL DETAIL.",68)
                self.label(d,(80,210),"A CLEARER IDENTITY.",56)
                for i,(yy,txt) in enumerate(((425,"TAB"),(710,"BOOKMARK"),(995,"SEARCH"))):
                    off=self.enter(t,start+.18*i,500)
                    self.browser(im,(85+off,yy,900,240),True,False,txt,1.24)
                self.character(im,t,figure,210,1310,770,start)
                self.label(d,(90,1820),"COHESIVE BRANDING",42)
            else:
                self.label(d,(90,110),"SMALL DETAIL.",76)
                self.label(d,(90,208),"FINISHED FEEL.",76)
                for i,(xx,txt) in enumerate(((100,"BROWSER"),(720,"TAB"),(1340,"BOOKMARK"))):
                    off=self.enter(t,start+.17*i,350)
                    self.browser(im,(xx,435+off,495,360),True,False,txt,1.05)
                self.label(d,(120,885),"YOUR MARK, WHERE PEOPLE ACTUALLY LOOK.",38)
        else:
            # Branded ending: original mark, Rovor copy and character close.
            if vertical:
                cx=540
                d.rounded_rectangle((100,430,980,950),radius=44,fill="white")
                self.mark(im,270,520,530)
                self.label(d,(145,1100),"ROVOR DIGITAL",76,"white")
                self.label(d,(145,1220),"GO BEYOND YOUR",56,"#dceae6")
                self.label(d,(145,1290),"CURRENT REACH.",56,"#dceae6")
                self.character(im,t,figure,250,1360,690,start)
            else:
                d.rounded_rectangle((100,255,1040,830),radius=45,fill="white")
                self.mark(im,285,340,570)
                self.label(d,(1110,330),"ROVOR",92,"white")
                self.label(d,(1110,455),"DIGITAL",92,"white")
                self.label(d,(1110,635),"GO BEYOND YOUR",50,"#dceae6")
                self.label(d,(1110,700),"CURRENT REACH.",50,"#dceae6")
        # Discrete cinematic wipes mark concept changes instead of leaving the
        # same fixed layout onscreen for 22 seconds.
        if name!="hook" and t<start+.16:
            span=int(W*(1-smooth((t-start)/.16)))
            d.rectangle((0,0,span,H),fill=NAVY)
        return im.convert("RGB")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan",type=Path)
    p.add_argument("out",type=Path)
    p.add_argument("--vertical",action="store_true")
    p.add_argument("--times",default="0.6,3.1,5.8,9.8,16.0,20.3")
    a=p.parse_args()
    times=[float(v) for v in a.times.split(",")]
    if len(times)>30: p.error("Maximum 30 explicit preview frames")
    scene=StoryboardFaviconScene(json.loads(a.plan.read_text()),a.vertical)
    a.out.mkdir(parents=True,exist_ok=True)
    for t in times:
        if not 0<=t<DURATION:p.error("Preview timestamp outside narration")
        frame=scene.render(t)
        name=f"story-{t:07.3f}-{'portrait' if a.vertical else 'landscape'}.jpg"
        frame.save(a.out/name,quality=88)
        print(name,flush=True)


if __name__=="__main__":
    main()
