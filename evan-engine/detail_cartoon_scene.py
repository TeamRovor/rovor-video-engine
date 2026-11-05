"""Optional authored precision accent on the matched super/small/detail phrase.

Existing separate brows, head, shoulders, elbows, wrists and index only.
No inferred emotion, new finger drawings or acoustic retiming.
"""
from cartoon_body import ROOT
from compact_cartoon_scene import compact_controls
from rounded_duration_cartoon_scene import RoundedDurationCartoonSceneBody
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
from expressive_cartoon_head import brow_controls
from painted_timing import flowing_track

def detail_event(plan):
    words=plan.get('words',[])
    for i in range(len(words)-2):
        if [w['word'].lower() for w in words[i:i+3]]==['super','small','detail']:
            a,b,c=words[i:i+3]
            return dict(anticipate=max(0,a['start']-.38),prepare=a['start']-.08,
                        arrive=b['start']+.08,hold=c['end']-.08,settle=c['end']+.75,
                        scriptIndices=[w['scriptIndex'] for w in (a,b,c)])
    return None

def detail_track(t,e,back,accent,delay=0):
    if e is None:return 0.
    return flowing_track(t-delay,[(e['anticipate'],0.),(e['prepare'],back),
        (e['arrive'],accent),(e['hold'],accent),(e['settle'],0.)])

def detail_controls(t,plan):
    c=compact_controls(t,plan);e=detail_event(plan)
    # A compact precision indication, not a fabricated thumb/index pinch.
    for side,back,accent,delays in [
        ('right',[.8,3.,4.],[-4.,-30.,-30.],[0.,.035,.075]),
        ('left',[-.3,-1.,-.5],[1.2,4.,1.5],[.02,.065,.11])]:
        c[side]=[v+detail_track(t,e,b,a,d) for v,b,a,d in zip(c[side],back,accent,delays)]
    c['index']=[v+detail_track(t,e,0.,a,d) for v,a,d in zip(c['index'],[2.,-24.,-14.],[.06,.085,.11])]
    c['head']+=detail_track(t,e,.6,-1.7,.025)
    c['body_roll']+=detail_track(t,e,-.12,.35,.07)
    return c

class DetailCartoonHead(RoundedDurationCartoonHead):
    def expression_control(self,t,plan):
        c=brow_controls(t,plan);e=detail_event(plan)
        for key,back,accent,delay in [('leftRaise',0.,-1.,.02),('rightRaise',.5,4.,0.),
            ('leftTilt',0.,-1.,.02),('rightTilt',0.,-2.,0.)]:
            c[key]+=detail_track(t,e,back,accent,delay)
        return c

class DetailCartoonSceneBody(RoundedDurationCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.head=DetailCartoonHead(root)
    def layers(self,t,plan,controls=None):
        return super().layers(t,plan,detail_controls(t,plan) if controls is None else controls)
    def render(self,t,plan,controls=None):
        return super().render(t,plan,detail_controls(t,plan) if controls is None else controls)
