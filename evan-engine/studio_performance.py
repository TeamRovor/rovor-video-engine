"""Director-authored cartoon acting beats, separate from acoustic viseme timing.

A pose is approached during its anticipation window, then held. Motion NEVER
follows a continuous energy wiggle. No emotion is inferred from transcription.
All cues are authored editorial decisions, not proof of finished acting.
"""
from __future__ import annotations
import math

JOINT_DEFAULTS = {
    'headTilt': 1.0, 'headNod': 0.0, 'bodyLean': 0.0,
    'browL': 0.0, 'browR': 0.0,
    'shoulderL': 25.0, 'shoulderR': -25.0,
    'elbowL': 0.0, 'elbowR': 0.0,
    'wristL': 0.0, 'wristR': 0.0,
    'smile': .18, 'handL': 'relaxed', 'handR': 'relaxed'
}
BOUNDS = {
    'headTilt':(-30,30), 'headNod':(-25,25), 'bodyLean':(-20,20),
    'browL':(-18,18), 'browR':(-18,18),
    'shoulderL':(-180,180), 'shoulderR':(-180,180),
    'elbowL':(-155,155), 'elbowR':(-155,155),
    'wristL':(-90,90), 'wristR':(-90,90), 'smile':(-1,1)
}
HAND_POSES = frozenset(('relaxed','open','point','explain','fist'))


def ease(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)


def validate_direction(direction):
    if not isinstance(direction,dict) or direction.get('schemaVersion') != 1:
        raise ValueError('Direction must be schemaVersion 1')
    if direction.get('origin') != 'editorial-authored':
        raise ValueError('Performance must be explicitly editorial-authored')
    beats=direction.get('beats')
    if not isinstance(beats,list) or not beats:
        raise ValueError('Direction must contain authored beats')
    cursor=0.
    poses=[]
    for i,beat in enumerate(beats):
        if not isinstance(beat,dict) or not isinstance(beat.get('intent'),str) or not beat['intent'].strip():
            raise ValueError(f'Beat {i} needs a meaningful acting intent')
        at=beat.get('at'); anticipate=beat.get('anticipate',.12); hold=beat.get('hold',.1)
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (at,anticipate,hold)):
            raise ValueError(f'Beat {i} contains nonfinite times')
        if at < 0 or anticipate < .04 or hold < 0 or at-anticipate < cursor-1e-8:
            raise ValueError(f'Beat {i} overlaps previous held pose or has invalid timing')
        pose=beat.get('pose')
        if not isinstance(pose,dict) or not pose:
            raise ValueError(f'Beat {i} has no pose')
        for channel,value in pose.items():
            if channel not in JOINT_DEFAULTS:
                raise ValueError(f'Unrecognized rig channel: {channel}')
            if channel.startswith('hand'):
                if value not in HAND_POSES:raise ValueError(f'Unknown hand pose: {value}')
            elif not isinstance(value,(int,float)) or not math.isfinite(value) or not BOUNDS[channel][0]<=value<=BOUNDS[channel][1]:
                raise ValueError(f'Out-of-range rig channel: {channel}')
        cursor = at+hold
        poses.append((float(at),float(anticipate),float(hold),pose))
    return poses


def direction_pose(time,direction):
    """Compute a complete numeric pose; categorical hands change at cue arrival.

    Re-validates external JSON every call: safe for diagnostics; production can
    cache validate_direction before rendering thousands of frames.
    """
    if not math.isfinite(time) or time < 0:raise ValueError('Invalid scene time')
    beats=validate_direction(direction)
    current=dict(JOINT_DEFAULTS)
    for at,anticipate,hold,new in beats:
        start=at-anticipate
        if time < start:return current
        if time < at:
            t=ease((time-start)/anticipate)
            return {k: (v if k.startswith('hand') else v+(new.get(k,v)-v)*t)
                    for k,v in current.items()}
        current.update(new)
    return current


def directed_hand_exposures(side,time,direction):
    """Keep source drawings registered and dissolve only near a real authored cue.

    This is a diagnostic drawing transition, not real finger in-between artwork.
    """
    if side not in ('L','R'):raise ValueError('Side must be L or R')
    if not math.isfinite(time) or time < 0:raise ValueError('Invalid scene time')
    hand='hand'+side
    previous=JOINT_DEFAULTS[hand]
    for at,anticipate,hold,pose in validate_direction(direction):
        target=pose.get(hand,previous)
        if target!=previous:
            blend=min(.12,anticipate)
            if at-blend <= time < at:
                w=ease((time-(at-blend))/blend)
                return [(previous,1-w),(target,w)]
            if time < at:return [(previous,1.)]
            previous=target
        elif time < at:return [(previous,1.)]
    return [(previous,1.)]


def describe(direction):
    beats=validate_direction(direction)
    return {'schemaVersion':1,'source':'editorial-authored',
            'beatCount':len(beats),'allBeatsHaveIntent':True,
            'sourceAudioAligned':False,'animationApproved':False,
            'notes':'Human-directed acting only. Mouth controls must come from separately audited audio.'}