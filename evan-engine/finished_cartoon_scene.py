"""Complete thought: a small favicon detail, then the branded payoff.

Authored acting/staging uses existing word anchors, never retimes speech.
"""
import numpy as np
from PIL import Image,ImageDraw
from cartoon_body import ROOT
from detail_cartoon_scene import DetailCartoonHead,detail_controls,detail_track
from relaxed_cartoon_scene import RelaxedCartoonSceneBody
from painted_timing import ease
from render_cartoon_head_study import font


def finish_event(plan):
    words=plan.get('words',[])
    for i in range(len(words)-5):
        part=words[i:i+6]
        if [w['word'].lower() for w in part]==['whole','website','feel','way','more','finished']:
            _,website,feel,_,more,finished=part
            return dict(anticipate=feel['start']-.35,prepare=feel['start']-.05,
                        arrive=more['start']+.08,hold=finished['end']-.04,
                        settle=finished['end']+.37,reveal=website['start'],
                        scriptIndices=[w['scriptIndex'] for w in part])
    return None


def finished_controls(t,plan):
    c=detail_controls(t,plan);event=finish_event(plan)
    for side,back,accent,delays in [
        ('right',[.4,1.5,2.],[-2.,-16.,-20.],[0.,.04,.08]),
        ('left',[-.3,-1.,-.5],[2.,7.,2.],[.025,.065,.105])]:
        c[side]=[v+detail_track(t,event,b,a,d) for v,b,a,d in zip(c[side],back,accent,delays)]
    c['head']+=detail_track(t,event,-.35,1.1,.025)
    c['body_roll']+=detail_track(t,event,-.08,.22,.06)
    return c


class FinishedCartoonHead(DetailCartoonHead):
    def expression_control(self,t,plan):
        c=super().expression_control(t,plan);event=finish_event(plan)
        for key,accent,delay in [('leftRaise',2.,.02),('rightRaise',2.5,0.),
                                 ('leftTilt',1.,.02),('rightTilt',-1.,0.)]:
            c[key]+=detail_track(t,event,0.,accent,delay)
        return c


class FinishedCartoonSceneBody(RelaxedCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=FinishedCartoonHead(root)
    def layers(self,t,plan,controls=None):
        return super().layers(t,plan,finished_controls(t,plan) if controls is None else controls)
    def render(self,t,plan,controls=None):
        return super().render(t,plan,finished_controls(t,plan) if controls is None else controls)


def favicon_progress(t,plan):
    event=finish_event(plan)
    return 0. if event is None else float(ease((t-event['reveal'])/.35))


def favicon_weights(progress):
    # Sequential fades keep the official mark from ghosting into the globe.
    return 1-float(ease(progress*2)),float(ease((progress-.5)*2))


class FinishedStage:
    """Official bitmap mark in both header and tab; illustrated browser UI."""
    def __init__(self):
        logo=Image.open(ROOT.parent/'brand/rovor-mark-black.png').convert('RGBA')
        self.header=logo.copy();self.header.thumbnail((52,52))
        self.favicon=logo.copy();self.favicon.thumbnail((24,24),Image.Resampling.LANCZOS)
    def draw(self,figure,t,plan):
        im=Image.new('RGBA',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
        d.ellipse((-200,570,650,850),fill='#d9e3dc')
        im.alpha_composite(figure.resize((849,891),Image.Resampling.LANCZOS),(-120,30))
        im.alpha_composite(self.header,(684,50))
        d.text((755,62),'ROVOR DIGITAL',font=font(25),fill='#233442')
        d.text((685,158),'Small detail.',font=font(43),fill='#233442')
        d.text((685,210),'Visible difference.',font=font(43),fill='#233442')
        d.rounded_rectangle((685,350,1195,568),radius=20,fill='#ffffff',outline='#bdc8c6',width=2)
        d.rounded_rectangle((685,350,1195,406),radius=20,fill='#dce6e2')
        d.rectangle((687,384,1193,406),fill='#dce6e2')
        for x in [708,727,746]:d.ellipse((x,369,x+7,376),fill='#829c99')
        d.rounded_rectangle((778,360,1112,399),radius=9,fill='#ffffff')
        d.text((826,368),'Your website',font=font(18),fill='#46616b')
        progress=favicon_progress(t,plan)
        old_strength,new_strength=favicon_weights(progress)
        old=Image.new('RGBA',(48,48));od=ImageDraw.Draw(old)
        od.ellipse((12,12,35,35),outline='#49717b',width=2)
        od.arc((18,12,29,35),0,360,fill='#49717b',width=1)
        od.line((12,23,35,23),fill='#49717b',width=1)
        old.putalpha(old.getchannel('A').point(lambda a:round(a*old_strength)))
        im.alpha_composite(old,(779,356-round(progress*10)))
        new=self.favicon.copy();new.putalpha(new.getchannel('A').point(lambda a:round(a*new_strength)))
        im.alpha_composite(new,(803-new.width//2,379-new.height//2+round((1-progress)*10)))
        # Copy changes once the new mark is legible. Single messages avoid
        # two overlapping captions during the word-anchored reveal.
        if new_strength<.5:
            d.text((719,439),'That tiny browser globe?',font=font(26),fill='#314b58')
            d.text((719,486),'It could be your brand.',font=font(23),fill='#62808a')
            d.text((685,603),'A small detail in your browser tab.',font=font(22),fill='#48636d')
        else:
            d.text((719,439),'Your brand belongs here.',font=font(26),fill='#314b58')
            d.text((719,486),'Even in the browser tab.',font=font(23),fill='#62808a')
            d.text((685,603),'A more finished first impression.',font=font(22),fill='#48636d')
        return im.convert('RGB')
