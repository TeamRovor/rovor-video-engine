"""Opt-in replacement hand during the existing opening indication gesture."""
import json
import numpy as np
from cartoon_body import ROOT
from painted_character import arm_transforms,rotation
from painted_timing import flowing_track
from payoff_cartoon_review import payoff_controls

_hand=json.loads((ROOT/'point-hand-fit-v1/manifest.json').read_text())
_arm=dict(json.loads((ROOT/'body-rig/manifest.json').read_text())['arms']['right'],wrist=_hand['targetWrist'])
# Manually inspected distal index centerline; an authored ray, not pixel tracking.
_points=np.array([[975.,930.,1.],[1110.,1060.,1.]])@np.array(_hand['sourceToBody']).T
POINT_TARGET=np.array([803.,379.])

def opening_point_event(plan):
 phrase='tiny little globe sitting up here instead of your logo'.split()
 words=plan.get('words',[])
 for i in range(len(words)-len(phrase)+1):
  part=words[i:i+len(phrase)]
  if [w['word'].lower()for w in part]!=phrase:continue
  times=[part[0]['start']-.45,part[2]['start']-.08,part[5]['end']+.08,part[-1]['end']+.45]
  if not np.isfinite(times).all() or times[0]<0 or np.any(np.diff(times)<=0):raise ValueError('Expected ordered opening point times')
  e=dict(zip(['anticipate','arrive','hold','settle'],times))
  e.update(poseOn=(times[0]+.08+times[1])/2+.065,poseOff=(times[2]+times[3])/2+.065,scriptIndices=[w['scriptIndex']for w in part])
  return e
 return None

def pointing_ray(controls):
 points=(np.c_[_points,np.ones(2)]@arm_transforms(_arm,controls['right'])[2].T)[:,:2]+[220,0]
 points=(np.c_[points,np.ones(2)]@rotation((732,950),-controls['body_roll']).T)[:,:2]
 return points*[849/1464,891/1536]+[-120,30]

def _ray_error(c):
 a,b=pointing_ray(c);d=b-a;v=POINT_TARGET-a
 return (d[0]*v[1]-d[1]*v[0])/np.linalg.norm(d)

def opening_point_controls(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 c=payoff_controls(t,plan);e=opening_point_event(plan)
 if e is None:return c
 weight=flowing_track(t,[(e['anticipate'],0.),(e['arrive'],1.),(e['hold'],1.),(e['settle'],0.)])
 if not weight:return c
 candidate={**c,'right':list(c['right'])};lo,hi=-120.,60.
 candidate['right'][2]=lo;left=_ray_error(candidate)
 candidate['right'][2]=hi
 if left*_ray_error(candidate)>=0:raise ValueError('Opening target is outside wrist aim bracket')
 for _ in range(32):
  mid=(lo+hi)/2;candidate['right'][2]=mid;value=_ray_error(candidate)
  if left*value>0:lo=mid;left=value
  else:hi=mid
 candidate['right'][2]=(lo+hi)/2;a,b=pointing_ray(candidate)
 if np.dot(b-a,POINT_TARGET-b)<=0:raise ValueError('Opening target must lie beyond the index tip')
 c['right'][2]+=weight*(candidate['right'][2]-c['right'][2])
 return c

def opening_point_pose(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 e=opening_point_event(plan)
 # Replacement drawings switch during the existing wrist swing; no finger blend.
 return 'point'if e is not None and e['poseOn']<=t<e['poseOff']else'open'
