"""Purposeful secondary character motion derived from already-authored posing.

No live random movement and no audio amplitude triggers. The animator chooses
primary poses; small lagged motions react to head/torso movement and naturally
settle once the primary pose is held. Engineering blockout, not approved art.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Secondary:
    hairTilt:float=0.
    hairShift:float=0.
    tieTilt:float=0.
    tieLift:float=0.


def _bound(value,limit):
    return max(-limit,min(limit,value))


def secondary_at(t,sampler,delay=.14):
    """Deterministic follow-through computed from authored poses at prior times.

    sampler(time) must return a pose with headTilt/headNod/bodyLean numeric fields.
    Intentional offset response avoids perpetual bouncing during held dialogue.
    """
    if not isinstance(t,(int,float)) or not math.isfinite(t) or t<0:
        raise ValueError('Secondary animation requires nonnegative finite time')
    if not isinstance(delay,(int,float)) or not math.isfinite(delay) or not .03<=delay<=.30:
        raise ValueError('Secondary delay must be in [0.03, 0.30] seconds')
    current=sampler(t)
    prev=sampler(max(0.,t-delay))
    prev2=sampler(max(0.,t-2*delay))
    fields=('headTilt','headNod','bodyLean')
    if any(not isinstance(getattr(p,k,None),(int,float)) or not math.isfinite(getattr(p,k))
           for p in (current,prev,prev2) for k in fields):
        raise ValueError('Secondary pose channels must be finite')
    head=(prev.headTilt-current.headTilt)+.35*(prev.headNod-current.headNod)
    torso=prev.bodyLean-current.bodyLean
    # An earlier primary movement changes the follow-through slope; the visual
    # element is always related to acting rather than inferred emotion/audio.
    acceleration=(current.bodyLean-2*prev.bodyLean+prev2.bodyLean)
    return Secondary(
        hairTilt=_bound(.48*head,5.5),
        hairShift=_bound(.16*head,2.2),
        tieTilt=_bound(.8*torso+.18*acceleration,7.0),
        tieLift=_bound(.17*abs(torso),2.2),
    )
