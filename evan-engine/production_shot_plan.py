"""Editorial shots at a single exact audio timebase with explicit source-art gates.

No automatic acting-from-loudness and no fake motion previews. Supports separate
foreground Evan, UI planes and an OPTIONAL Rovor rover cutaway. All output stays
review-only until official art and a real-alignment plan are verified.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

ALLOWED = frozenset(('evan-host','browser-explainer','favicon-detail','brand-reveal','rover-cutaway','endcard'))
ROVER_IDS=frozenset(('rovor-left-right-and-top','rovor-side-hero'))


def _number(x,name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):
        raise ValueError('Nonfinite '+name)
    return float(x)


def compile_plan(spec,audio_info):
    if spec.get('schemaVersion')!=1 or spec.get('source')!='editorial-authored':
        raise ValueError('Shot plan must be editorial-authored v1')
    if spec.get('characterStyle')!='rovor-evan-expressive-cartoon' or spec.get('characterArtStatus')!='awaiting-visual-approval':
        raise ValueError('No default auto-approved character artwork')
    fps=spec.get('fps',24)
    if isinstance(fps,bool) or fps not in (24,30,48):raise ValueError('Invalid fps')
    duration=_number(audio_info['durationSec'],'recording duration')
    shots=spec.get('shots')
    if not isinstance(shots,list) or not shots or len(shots)>200:raise ValueError('No bounded editorial shots')
    ordered=[];previous=0
    for i,shot in enumerate(shots):
        if shot.get('kind') not in ALLOWED:raise ValueError('Unsupported shot kind')
        start=_number(shot.get('start'),'shot start');end=_number(shot.get('end'),'shot end')
        start_frame=round(start*fps);end_frame=round(end*fps)
        if start < 0 or end <= start or start_frame!=previous or end_frame<=start_frame:
            raise ValueError('Shots must cover contiguous nonempty frame spans')
        if shot['kind']=='rover-cutaway' and (not shot.get('roverReferenceIds') or not set(shot['roverReferenceIds']).issubset(ROVER_IDS)):
            raise ValueError('Rover cutaways require known exact image source identifiers')
        if not isinstance(shot.get('purpose'),str) or not shot['purpose'].strip():
            raise ValueError('Shot needs an editorial narrative purpose')
        if 'cameraShake' in shot or 'audioRmsToGesture' in shot:
            raise ValueError('Mechanical amplitude-driven movement is forbidden')
        row={'index':i,'kind':shot['kind'],'startFrame':start_frame,'endFrameExclusive':end_frame,
             'purpose':shot['purpose'],'characterAnimationApproved':False,
             'referenceIds':shot.get('roverReferenceIds',[]),'composition':shot.get('composition','medium')}
        ordered.append(row);previous=end_frame
    # Ceil the decoded take at render cadence so the final audio sample is kept.
    # Extend ONLY the endcard tail by at most one frame; never shift speech beats.
    duration_frames=math.ceil(duration*fps)
    tail_padding=duration_frames-previous
    if tail_padding<0 or tail_padding>1:
        raise ValueError('Shots do not end at the decoded recording')
    if tail_padding:
        ordered[-1]['endFrameExclusive']+=tail_padding
        ordered[-1]['audioTailPadFrames']=tail_padding
    for beat in spec.get('actingBeats',[]):
        when=_number(beat.get('at'),'beat time')
        if when<0 or when>duration or not beat.get('intent'):
            raise ValueError('Acting cue lacks timing/intent')
    layout=spec.get('delivery',{})
    safe_left=layout.get('safeLeftPct',.12);safe_right=layout.get('safeRightPct',.12)
    for x in (safe_left,safe_right):
        if not isinstance(x,(int,float)) or not 0<=x<=.25:raise ValueError('Unsafe mobile crop')
    return {'status':'animatic-plan-only-not-art-approved', 'renderReady':False,
            'audioSource':audio_info,'fps':fps,'totalFrames':duration_frames,'shotCount':len(ordered),
            'shots':ordered,'audioTailPadFrames':tail_padding,'actingBeatCount':len(spec.get('actingBeats',[])),
            'voiceAlignmentVerified':False,'actualCharacterLayersRequired':True,
            'delivery':layout,'reasonsNotReady':[
                'Requires approved registered production character art',
                'Requires audited same-take phoneme/word timing',
                'Requires human review of acting and design at normal/slow speed']}


def write_plan(spec_path,audio_path,destination):
    source=json.loads(Path(spec_path).read_text());audio=json.loads(Path(audio_path).read_text())
    result=compile_plan(source,audio);dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('spec',type=Path);p.add_argument('audio_info',type=Path);p.add_argument('destination',type=Path)
    a=p.parse_args(); print(json.dumps(write_plan(a.spec,a.audio_info,a.destination),indent=2))