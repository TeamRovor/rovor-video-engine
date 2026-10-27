"""Opt-in stronger head/torso attitude on the existing small-detail cue."""
import numpy as np
from dismissive_cartoon_review import dismissive_controls
from detail_cartoon_scene import detail_event,detail_track

def payoff_controls(t,plan):
 if not np.isfinite(t):raise ValueError('Expected finite review time')
 c=dismissive_controls(t,plan);event=detail_event(plan)
 c['head']+=detail_track(t,event,.5,-3.2,.025)
 c['body_roll']+=detail_track(t,event,-.15,.85,.07)
 return c
