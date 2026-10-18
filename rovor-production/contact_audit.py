"""Reusable 2D rig contact-validation: catches impossible detached limb/tool plans.

Input poses are director-authored *actual geometry control points*, not prose
or fake rendered-image checks. Mathematical continuity cannot approve visual art.
Each physical scene should prove that the same wrist controls the limb and hand,
and the hand controls any attached prop throughout an action interval.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import hypot,isfinite
from collections.abc import Sequence

class ContactError(ValueError): pass

@dataclass(frozen=True)
class P:
 x:float
 y:float
 def __post_init__(self):
  if not all(isfinite(v) for v in (self.x,self.y)):raise ContactError('nonfinite joint')
 def distance(self,o):return hypot(self.x-o.x,self.y-o.y)

@dataclass(frozen=True)
class Pose:
 frame:int
 shoulder:P
 elbow:P
 wrist:P
 hand:P
 grip:P|None=None


def audit_contact_track(poses:Sequence[Pose],*,shoulder_to_elbow=(18.,190.),elbow_to_wrist=(15.,190.),wrist_to_hand=18.,hand_to_grip=18.,max_frame_gap=12):
 """Fail closed on disconnected puppet mechanics; pass != polished anatomy.

 Poses must refer to one staged coordinate system (per orientation). The grip
 must come from the *same* prop control layer used by the renderer, not guessed
 from the intended script. Each 60fps interval may be sampled every <=12 frames.
 """
 if not poses or not isinstance(poses,Sequence):raise ContactError('no pose evidence')
 if not all(type(x) is Pose for x in poses):raise ContactError('not shared real pose joints')
 if type(max_frame_gap) is not int or max_frame_gap<1:raise ContactError('invalid frame gap')
 details=[]
 for i,p in enumerate(poses):
  if type(p.frame) is not int or p.frame<0 or (i and (p.frame<=poses[i-1].frame or p.frame-poses[i-1].frame>max_frame_gap)):
   raise ContactError('non-monotonic or insufficient pose sampling')
  upper=p.shoulder.distance(p.elbow);lower=p.elbow.distance(p.wrist)
  if not shoulder_to_elbow[0]<=upper<=shoulder_to_elbow[1]:raise ContactError(f'frame {p.frame}: upper arm length {upper:.1f} out of bounds')
  if not elbow_to_wrist[0]<=lower<=elbow_to_wrist[1]:raise ContactError(f'frame {p.frame}: lower arm length {lower:.1f} out of bounds')
  attached=p.wrist.distance(p.hand)
  if attached>wrist_to_hand:raise ContactError(f'frame {p.frame}: detached hand {attached:.1f}px')
  if p.grip is not None and p.hand.distance(p.grip)>hand_to_grip:
   raise ContactError(f'frame {p.frame}: tool floats {p.hand.distance(p.grip):.1f}px from hand')
  details.append({'frame':p.frame,'upper_px':round(upper,2),'lower_px':round(lower,2),'hand_gap_px':round(attached,2),'grip_gap_px':round(p.hand.distance(p.grip),2) if p.grip else None})
 return {'structural_contact_valid':True,'pose_count':len(poses),'samples':details,'artist_approved':False,'source_verified':False,'video_rendered':False}