"""Lossless-ish scene cue -> Moho switch handoff with explicit uncertain accuracy.

Never calls an aligner or changes the original acoustic estimates. Continuous
six-channel controls are still the preferred expressive rig input. This module
is a portable legacy Rhubarb switch bridge, not a promise of flawless lip-sync.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

SHAPES = frozenset('XABCDEFGH')


def _time(v, label):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError(label + ' must be finite seconds')
    return float(v)


def validate_scene(scene):
    duration = _time(scene.get('duration'), 'duration')
    if duration <= 0 or duration > 3600:
        raise ValueError('Scene duration out of bounds')
    cues = scene.get('mouthCues')
    if not isinstance(cues, list) or not cues:
        raise ValueError('Missing mouth cues')
    normalized = []
    previous = 0.0
    for n, cue in enumerate(cues):
        a = _time(cue.get('start'), 'cue start')
        b = _time(cue.get('end'), 'cue end')
        shape = cue.get('value')
        if a < 0 or b <= a or b > duration + .050:
            raise ValueError('Invalid cue duration at index %s' % n)
        if shape not in SHAPES:
            raise ValueError('Unknown switch layer name: %r' % shape)
        if abs(a - previous) > .025:
            raise ValueError('Audio cue topology has a gap/overlap >25ms: %s' % n)
        normalized.append((a,b,shape))
        previous = b
    if abs(previous-duration) > .050:
        raise ValueError('Audio cue tail and scene duration mismatch >50ms')
    return duration,normalized


def _wav_signature(path):
    with wave.open(str(path), 'rb') as audio:
        channels=audio.getnchannels();width=audio.getsampwidth()
        rate=audio.getframerate();frames=audio.getnframes()
    if width!=2 or channels!=1 or rate<8000:
        raise ValueError('Audio bridge expects exact decoded PCM16 mono WAV')
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return dict(wavSha256=h.hexdigest(),durationSec=frames/rate,sampleRate=rate,channels=channels)


def sample_switches(scene, fps=24, wav=None):
    """One-based Moho keys; sample frame centers, coalesce repeated positions.

    Integer-frame switches have 1/fps resolution and may mask short phonemes;
    no output here certifies detailed audio/phone correctness.
    """
    if isinstance(fps, bool) or not isinstance(fps,int) or fps not in (24,25,30,48,60):
        raise ValueError('Unsupported timeline fps')
    duration,cues=validate_scene(scene)
    info=_wav_signature(wav) if wav else None
    if info and abs(info['durationSec']-duration)>.050:
        raise ValueError('Scene and decoded take duration disagree >50ms')
    total_frames=math.ceil(duration*fps)
    sampled=[];j=0
    for index in range(total_frames):
        t=min(duration-1e-8,(index+.5)/fps)
        while j+1<len(cues) and t >= cues[j][1]:j+=1
        value=cues[j][2]
        if not sampled or sampled[-1]['shape']!=value:
            sampled.append(dict(frame=index+1,shape=value,sceneTimeSec=round(index/fps,6)))
    short=[dict(start=a,end=b,shape=s) for a,b,s in cues if b-a<1/fps]
    warnings=[]
    if short:warnings.append('%d cues shorter than one frame; frame-quantization can drop them' % len(short))
    if not info:warnings.append('No original PCM16 WAV provided: audio identity not checked')
    report={
       'format':'MohoSwitch1','status':'engineering-handoff-unreviewed',
       'sourceCueFamily':'Rhubarb-v3-switch','phoneBoundariesVerified':False,
       'later18FlaggedRegionsReviewed':False,'productionReady':False,
       'fps':fps,'sceneDurationSec':duration,'frames':total_frames,
       'sourceCueCount':len(cues),'switchKeyCount':len(sampled),
       'subframeCueCount':len(short),'sourceAudio':info,'warnings':warnings,
       'notes':'Switch values are coarse visual approximations, not phoneme boundaries; no Moho project was edited.'
    }
    return sampled,report


def export(scene_path,output_dir,wav=None,fps=24):
    scene=json.loads(Path(scene_path).read_text())
    keys,report=sample_switches(scene,fps,wav)
    target=Path(output_dir);target.mkdir(parents=True,exist_ok=True)
    contents='MohoSwitch1\n'+''.join(f"{k['frame']} {k['shape']}\n" for k in keys)
    (target/'evan-v3-unreviewed.dat').write_text(contents)
    (target/'voice-switch-evidence.json').write_text(json.dumps({'keys':keys,**report},indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wav',type=Path);p.add_argument('--fps',type=int,default=24)
    a=p.parse_args();print(json.dumps(export(a.scene,a.output,a.wav,a.fps),indent=2))