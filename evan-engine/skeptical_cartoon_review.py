"""Opt-in asymmetric brows for the browser misconception; no oral changes."""
import numpy as np
from painted_timing import flowing_track

def skeptical_event(plan):
 phrase="that's not some random browser thing".split()
 words=plan.get('words',[])
 for i in range(len(words)-len(phrase)+1):
  part=words[i:i+len(phrase)]
  if [w['word'].lower() for w in part]!=phrase:continue
  times=[max(0.,part[0]['start']-.22),(part[1]['start']+part[1]['end'])/2,part[-1]['end'],part[-1]['end']+.31]
  if not np.isfinite(times).all() or part[0]['start']<0 or np.any(np.diff(times)<=0):raise ValueError('Expected ordered skeptical cue times')
  return dict(zip(['anticipate','arrive','hold','settle'],times),scriptIndices=[w['scriptIndex'] for w in part])
 return None

def skeptical_brows(t,plan,baseline,*,strong=False):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 c=baseline.copy();event=skeptical_event(plan)
 if event is None:return c
 weight=flowing_track(t,[(event['anticipate'],0.),(event['arrive'],1.),(event['hold'],1.),(event['settle'],0.)])
 # Opt-in upper-face review: deepen one furrow while holding the other arch.
 accents=(-6.,8.,-7.,-1.) if strong else (-2.,7.,-4.,-3.)
 for key,accent in zip(('leftRaise','rightRaise','leftTilt','rightTilt'),accents):
  c[key]+=weight*accent
 return c
