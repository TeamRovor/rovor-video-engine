"""Reusable 2D track continuity and contact guard.

Detects prop teleportation, irregular timestamps and unattached contact points.
This is an engineering gate only, never animation/acting or filmmaking approval.
"""
from math import hypot,isfinite

def audit_positions(samples, *, fps=60, max_pixels_per_frame=30):
 """samples=[(frame_number, x, y),...] inclusive, regularly spaced."""
 if fps<=0 or max_pixels_per_frame<=0:raise ValueError('Invalid sample policy')
 issues=[]
 if len(samples)<2:return {'valid':False,'issues':['At least two samples required'],'max_step':None,'artisticApproval':False}
 max_step=0
 for i,(n,x,y) in enumerate(samples):
  if not all(isfinite(float(v)) for v in (n,x,y)):issues.append(f'Nonfinite pose at index {i}');continue
  if i:
   pn,px,py=samples[i-1]
   if n!=pn+1:issues.append(f'Frame discontinuity at index {i}')
   step=hypot(x-px,y-py)
   max_step=max(max_step,step)
   if step>max_pixels_per_frame:issues.append(f'Teleportation at frame {n}: {step:.3f} pixels/frame')
 return {'valid':not issues,'issues':issues,'max_step':round(max_step,3),'artisticApproval':False}

def audit_contact(attachments, *, max_distance=15):
 """attachments=[(frame, hand_position, prop_anchor),...]."""
 defects=[]
 for frame,hand,prop in attachments:
  if len(hand)!=2 or len(prop)!=2 or not all(isfinite(v) for v in (*hand,*prop)):
   defects.append((frame,'Malformed contact anchor'));continue
  d=hypot(hand[0]-prop[0],hand[1]-prop[1])
  if d>max_distance:defects.append((frame,f'Detached by {d:.2f}px'))
 return {'valid':bool(attachments) and not defects,'defects':defects,'artisticApproval':False}