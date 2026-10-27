"""Opt-in held explanatory palm; unchanged speech, source art and closing shot."""
import numpy as np
from finished_cartoon_scene import finished_controls
from painted_timing import flowing_track

def definition_event(plan):
 phrase="it's basically a tiny version of your brand made specifically for browser tabs".split()
 words=plan.get('words',[])
 for i in range(len(words)-len(phrase)+1):
  part=words[i:i+len(phrase)]
  if [w['word'].lower() for w in part]!=phrase:continue
  first,last=part[0],part[-1]
  times=[max(0.,first['start']-.4),first['start']+.12,last['start']+.06,last['end']+.12]
  if not np.isfinite(times).all() or first['start']<0 or np.any(np.diff(times)<=0):raise ValueError('Expected ordered definition cue times')
  return dict(zip(['anticipate','arrive','hold','settle'],times),scriptIndices=[w['scriptIndex'] for w in part])
 return None

def definition_controls(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 c=finished_controls(t,plan);event=definition_event(plan)
 if event is None:return c
 weight=flowing_track(t,[(event['anticipate'],0.),(event['arrive'],1.),(event['hold'],1.),(event['settle'],0.)])
 if weight:
  # shortcut: one fixed open-palm drawing; new finger acting needs registered artwork.
  c['right']=[v*(1-weight)+p*weight for v,p in zip(c['right'],[-3.,-38.,-5.])]
 return c
