"""Experimental 3-second acted story: generic globe escapes its browser tab.

An actual animated object, tabletop set and Evan's original layered rig.
No stock/AI video. This short scene is an audition, NOT studio-quality approval.
Speech and mouth come from the original verified 22.047s narration plan.
"""
import math
from PIL import Image,ImageDraw,ImageFont
from cartoon_body import CartoonBody,REVIEW_BODY_OPTIONS,narration_acting
from render_profile import LANDSCAPE,VERTICAL

START=2.35
END=5.65
BG="#f2efe7"
INK="#1d3145"
GLOBE="#3c9ba1"
GOLD="#dc9851"


def clamped(v):
    return max(0.,min(1.,float(v)))


def ease(v):
    x=clamped(v)
    return x*x*(3-2*x)


def hop(t):
    """Authored beats: hatch from browser tab, run, dodge, settle."""
    if not START<=t<=END:
        raise ValueError("Action belongs to the established original narration only")
    if t<2.97:
        u=ease((t-START)/.62)
        return (u,1.-u,20+66*u,2*u,0., "hatch")
    if t<4.43:
        u=clamped((t-2.97)/1.46)
        # Accelerating run with two bounces, supported squash/stretch.
        return (1.+1.4*u,0.,86,math.sin(u*5*math.pi),u, "run")
    if t<4.94:
        u=ease((t-4.43)/.51)
        return (2.4-.49*u,0.,86,-u,u,"dodge")
    u=ease((t-4.94)/.71)
    return (1.91+.06*u,0.,86,0.,u,"settle")


def framespec(t,vertical=False):
    v,air,r,leg,progress,beat=hop(t)
    if vertical:
        start=(159.,365.)
        # Laptop is upstage, the tiny mascot runs into foreground.
        if beat=="hatch":
            x=start[0]+v*380
            y=start[1]+v*595-160*math.sin(math.pi*clamped(v))
        else:
            x=539+(v-1)*240
            y=950-26*abs(math.sin((t-2.97)*10)) if beat=="run" else 930
    else:
        start=(219.,295.)
        if beat=="hatch":
            x=start[0]+v*480
            y=start[1]+v*384-190*math.sin(math.pi*clamped(v))
        else:
            x=699+(v-1)*410
            y=684-30*abs(math.sin((t-2.97)*10)) if beat=="run" else 678
    return dict(x=x,y=y,r=r,air=air,leg=leg,beat=beat,progress=progress,
                # Reaction displaces Evan's body plate without distorting the source drawing.
                evanRecoil=(45*math.sin(math.pi*ease((t-3.48)/.62))
                            if 3.48<t<4.1 else 0))


class GlobePuppet:
    """Tiny original object-character with separate face/limb acting."""

    def __init__(self,scale=1.):
        self.s=scale

    def render(self,image,state,t):
        d=ImageDraw.Draw(image)
        x,y,r=state["x"],state["y"],state["r"]
        radius=max(9,int(r*self.s))
        beat=state["beat"]
        stride=math.sin((t-2.97)*22) if beat=="run" else 0
        jumping=14*abs(math.sin((t-2.97)*11)) if beat=="run" else 0
        stretch=1+.09*abs(stride) if beat=="run" else 1
        if beat=="dodge":stretch=.8
        cx=int(x);cy=int(y-jumping)
        half_w=int(radius*stretch)
        half_h=int(radius/stretch)
        # Independent ground shadow prevents the figure from floating.
        ground=cy+half_h+int(42*self.s)+int(jumping)
        d.ellipse((cx-radius*.88,ground-10*self.s,cx+radius*.88,ground+12*self.s),
                  fill="#c8d7d2")
        sw=max(3,int(7*self.s))
        # Limbs behind the body and timed like a running cartoon.
        if beat!="hatch" or radius>30:
            for side in (-1,1):
                shoulder=(cx+side*half_w*.7,cy+half_h*.15)
                end=(cx+side*(half_w+32*self.s),cy+(18+26*side*stride)*self.s)
                d.line((shoulder[0],shoulder[1],end[0],end[1]),
                       fill=INK,width=sw,joint="curve")
                knee=(cx+side*half_w*.36,cy+half_h*.8)
                foot=(cx+side*(radius*.5+27*stride),cy+half_h+(38+15*abs(stride))*self.s)
                d.line((knee[0],knee[1],foot[0],foot[1]),fill=INK,width=sw+1,joint="curve")
                d.ellipse((foot[0]-12*self.s,foot[1]-6*self.s,
                           foot[0]+18*self.s,foot[1]+7*self.s),fill=INK)
        body=(cx-half_w,cy-half_h,cx+half_w,cy+half_h)
        d.ellipse(body,fill="#ffffff",outline=INK,width=max(4,int(7*self.s)))
        # Meridian + latitude evokes the generic browser globe, but it can emote.
        d.arc((cx-half_w*.68,cy-half_h,cx+half_w*.68,cy+half_h),75,285,fill=GLOBE,width=sw)
        d.arc((cx-half_w,cy-half_h*.49,cx+half_w,cy+half_h*.49),10,170,fill=GLOBE,width=sw)
        d.line((cx-half_w*.75,cy,cx+half_w*.75,cy),fill=GLOBE,width=sw)
        eye_y=cy-int(17*self.s)
        eye_space=int(26*self.s)
        pupil_offset=int(7*self.s if beat in ("dodge","settle") else -3*self.s)
        for pos in (-eye_space,eye_space):
            rad=max(4,int(10*self.s))
            d.ellipse((cx+pos-rad,eye_y-rad,cx+pos+rad,eye_y+rad),fill=INK)
            d.ellipse((cx+pos+pupil_offset-3*self.s,eye_y-5*self.s,
                       cx+pos+pupil_offset+2*self.s,eye_y),fill="white")
        if beat in ("hatch","dodge"):
            d.ellipse((cx-12*self.s,cy+17*self.s,cx+12*self.s,cy+48*self.s),fill=INK)
        else:
            d.arc((cx-25*self.s,cy+16*self.s,cx+25*self.s,cy+49*self.s),
                  0,165,fill=INK,width=max(3,int(5*self.s)))
        if beat=="run" and abs(stride)>.72:
            # Three short speed lines, finite and direction-specific.
            for j in range(3):
                xx=cx-half_w-(25+16*j)*self.s
                yy=cy+(j-1)*18*self.s
                d.line((xx-22*self.s,yy,xx,yy),fill="#9fbeb9",width=max(2,int(3*self.s)))


class CartoonDesktopSet:
    def __init__(self,vertical=False):
        self.vertical=vertical
        self.size=VERTICAL if vertical else LANDSCAPE
        self.W,self.H=self.size
        self.scale=self.W/1920 if not vertical else self.W/1080

    def draw(self,im,t):
        d=ImageDraw.Draw(im)
        w,h=self.size
        d.rectangle((0,0,w,h),fill=BG)
        # A lived-in studio set with actual foreground occlusion, not infographic cards.
        if self.vertical:
            d.polygon(((0,0),(w,0),(w,650),(0,520)),fill="#e2e9e2")
            d.rectangle((60,120,w-60,190),fill="#c0d7cf")
            d.rectangle((90,190,140,360),fill="#839a90")
            d.ellipse((43,175,192,280),fill="#7e9e79")
            self.monitor(im,(85,290,905,690),t)
            d.rectangle((0,1090,w,h),fill="#bb8871")
            d.polygon(((0,1090),(w,1090),(w,1190),(0,1240)),fill="#d4a080")
            d.line((0,1090,w,1090),fill="#754b41",width=10)
        else:
            d.polygon(((0,0),(w,0),(w,380),(0,285)),fill="#e2e9e2")
            d.rectangle((0,205,190,230),fill="#8ba9a1")
            d.ellipse((54,126,176,260),fill="#77a185")
            d.rectangle((100,236,133,560),fill="#536e60")
            self.monitor(im,(145,220,945,715),t)
            d.rectangle((0,815,w,h),fill="#bf8b73")
            d.polygon(((0,815),(w,815),(w,900),(0,937)),fill="#d3a086")
            d.line((0,815,w,815),fill="#845748",width=11)

    def foreground(self,im):
        """Landscape desk foreground hides the lower rig, preserving real depth."""
        if self.vertical:
            return
        d=ImageDraw.Draw(im)
        w,h=self.size
        d.rectangle((0,815,w,h),fill="#bf8b73")
        d.polygon(((0,815),(w,815),(w,900),(0,937)),fill="#d3a086")
        d.line((0,815,w,815),fill="#845748",width=11)

    def monitor(self,im,box,t):
        d=ImageDraw.Draw(im)
        x0,y0,x1,y1=box
        d.rounded_rectangle((x0+10,y0+12,x1+12,y1+12),radius=29,fill="#a8b8b4")
        d.rounded_rectangle(box,radius=28,fill=INK)
        d.rounded_rectangle((x0+22,y0+22,x1-22,y1-22),radius=16,fill="#ecf4ef")
        d.rounded_rectangle((x0+35,y0+37,x1-35,y0+118),radius=15,fill="#d1e0db")
        # The favicon hole appears as the little globe takes off.
        departure=ease((t-2.35)/.25)
        px=x0+74
        py=y0+75
        if departure<.93:
            r=max(4,round(16*(1-departure)))
            d.ellipse((px-r,py-r,px+r,py+r),fill="#578984",outline=INK,width=2)
        else:
            d.ellipse((px-18,py-18,px+18,py+18),outline="#bdcec9",width=3)
        # No fake screenshot or customer: neutral site layout placeholders.
        d.rounded_rectangle((x0+75,y0+165,x1-95,y0+275),radius=22,fill="#d6e5df")
        d.rounded_rectangle((x0+75,y0+300,x0+int((x1-x0)*.57),y0+326),
                            radius=10,fill="#bfd1cb")
        d.rounded_rectangle((x0+75,y0+351,x1-200,y0+372),
                            radius=10,fill="#d2ddd8")
        # monitor foot is visually anchored behind the desk
        mid=(x0+x1)//2
        d.polygon(((mid-52,y1),(mid+52,y1),(mid+84,y1+100),(mid-84,y1+100)),fill="#334c58")
        d.rounded_rectangle((mid-150,y1+95,mid+150,y1+125),radius=10,fill="#283d4b")


class EvanGlobeAction:
    """Storyboard module compatible with render_acting_video's cached layers."""
    def __init__(self,plan,vertical=False):
        self.plan=plan
        self.vertical=vertical
        self.size=VERTICAL if vertical else LANDSCAPE
        self.body=CartoonBody(**REVIEW_BODY_OPTIONS)
        self.set=CartoonDesktopSet(vertical)
        self.puppet=GlobePuppet(.95 if vertical else 1)

    def render(self,t,figure=None):
        st=framespec(t,self.vertical)
        im=Image.new("RGBA",self.size)
        self.set.draw(im,t)
        if figure is None:
            figure=self.body.render(t,self.plan,narration_acting(t))
        if self.vertical:
            # Medium close-up shares the physical desk rather than splitting
            # the frame into disconnected presentation-card halves.
            width=1170
            x=-40+int(st["evanRecoil"])
            y=865
        else:
            # Foreground Evan is staged for genuine interaction with the
            # bouncing prop; his legs are occluded by the near desk.
            width=1170
            x=760+int(st["evanRecoil"]*2)
            y=35
        h=round(width*figure.height/figure.width)
        plate=figure.resize((width,h),Image.Resampling.LANCZOS)
        # Acting accents: brief recoil, overshoot and settle around the waist.
        # Only transforms original fully rendered art, retaining existing
        # lip-sync and anatomical joint continuity inside the layer stack.
        recoil=ease((t-3.48)/.22)*(1-ease((t-4.14)/.47))
        settle=ease((t-4.25)/.24)*(1-ease((t-4.78)/.28))
        angle=-4.2*recoil+1.25*settle
        if abs(angle)>.01:
            plate=plate.rotate(angle,Image.Resampling.BICUBIC,
                               center=(round(width*.5),round(h*.86)))
        im.alpha_composite(plate,(x,y))
        self.set.foreground(im)
        # Prop in front of desk/Evan: their paths share the physical foreground.
        self.puppet.render(im,st,t)
        return im.convert("RGB")
