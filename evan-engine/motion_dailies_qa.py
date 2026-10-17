"""Rendered frame QA: catch frozen shots, black frames and unexplained jumps.

Pure diagnostic: motion metrics cannot judge appeal, true acting or lip sync.
Frame evidence MUST be inspected by an animator before any release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def analyze_frames(directory,cut_frames=(),max_frames=2400,size=(160,90)):
    directory=Path(directory)
    paths=sorted(directory.glob('*.png'))
    if len(paths)<2 or len(paths)>max_frames:
        raise ValueError('Need a bounded nonempty frame sequence')
    if len(set(p.name for p in paths))!=len(paths):raise ValueError('Duplicate sequence names')
    old=None;differences=[];black=[];holds=[]
    for i,p in enumerate(paths):
        with Image.open(p) as im:
            frame=np.asarray(im.convert('RGB').resize(size),dtype=np.float32)/255.
        brightness=float(frame.mean())
        if brightness<.015:black.append(i)
        if old is not None:
            delta=float(np.mean(np.abs(frame-old)))
            differences.append(delta)
        old=frame
    cut_frames=set(cut_frames)
    for n in cut_frames:
        if not isinstance(n,int) or n<1 or n>=len(paths):raise ValueError('Cut outside frames')
    unfrozen=[(i+1,d) for i,d in enumerate(differences) if i+1 not in cut_frames]
    vals=[d for _,d in unfrozen]
    median=float(np.median(vals)) if vals else 0.
    jumps=[i for i,d in unfrozen if d>max(.14,12*max(median,.005))]
    run=0
    for i,change in enumerate(differences,start=1):
        if change<.0005 and i not in cut_frames:
            run+=1
            if run==12:holds.append({'throughFrame':i,'frozenFrameCount':run})
        else:run=0
    return {'status':'diagnostic-not-animation-approval','frameCount':len(paths),
            'meanFrameChange':float(np.mean(differences)),'medianNonCutChange':median,
            'blackFrameIndices':black,'unexplainedJumpFrameIndices':jumps,'longNearIdenticalRuns':holds,
            'declaredCutFrames':sorted(cut_frames), 'artisticApproval':False,
            'notes':['Long held poses may be artistically justified; the static threshold is a review cue',
                     'Metrics do not measure appealing drawings, accurate speech contact or storytelling']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('frames',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--cuts',default='',help='Comma separated 0-based cut frame indices')
    a=p.parse_args();cuts=[int(x) for x in a.cuts.split(',') if x.strip()]
    result=analyze_frames(a.frames,cuts);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))