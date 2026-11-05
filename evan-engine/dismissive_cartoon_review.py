"""Opt-in left open-palm dismissal; preserve definition and facial controls."""
import numpy as np
from definition_cartoon_review import definition_controls
from skeptical_cartoon_review import skeptical_event
from painted_timing import flowing_track

def dismissive_controls(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 c=definition_controls(t,plan);event=skeptical_event(plan)
 if event is None:return c
 words=plan['words'];part=next(words[i:i+6] for i in range(len(words)-5) if [w['scriptIndex'] for w in words[i:i+6]]==event['scriptIndices'])
 prepare=part[0]['start'];hold=part[3]['end']
 if not np.isfinite([prepare,hold]).all() or not event['anticipate']<prepare<event['arrive']<hold<event['settle']:raise ValueError('Expected ordered dismissive cue times')
 # shortcut: fixed open-palm drawing; a turned or flexing hand needs registered art.
 for i,(back,accent,delay) in enumerate([(0.,1.5,0.),(-4.,28.,.035),(3.,-6.,.07)]):
  c['left'][i]+=flowing_track(t-delay,[(event['anticipate'],0.),(prepare,back),(event['arrive'],accent),(hold,accent),(event['settle'],0.)])
 return c
