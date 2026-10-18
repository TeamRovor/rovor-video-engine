"""Explicit, non-periodic original-Evan acting controls for long-form dialogue.

Uses the controls CartoonBody.layers actually supports. Shots can stage
purposeful anticipation, main gesture and settle on independent frames. There
is NO automatic fake eyeline control, no standing puppet oscillation, and no
phoneme claims; mouth shapes continue to use the speech plan separately.
"""
import argparse
import bisect
import json
import math
from pathlib import Path

RATE=60
LIMITS={
 "left.shoulder":12,"left.elbow":30,"left.wrist":12,
 "right.shoulder":12,"right.elbow":30,"right.wrist":12,
 "head":2.5,"body_roll":1.5,"brow_left":5,"brow_right":5,
}
HANDS=("open","relaxed","point")
DEFAULT_HAND="open"


def validate(config):
    if not isinstance(config,dict) or config.get("schemaVersion")!=1 or config.get("sourceRig")!="original-evan-layered":
        raise ValueError("Original Evan control-plan schema required")
    duration=config.get("durationSec")
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or not 30<=duration<=900:
        raise ValueError("Only >=30s real-source narration schedules supported")
    end=math.ceil(duration*RATE-1e-9)
    tracks=config.get("channels")
    if not isinstance(tracks,dict) or not tracks or not set(tracks)<=set(LIMITS):
        raise ValueError("Unsupported original rig actuator")
    normalized={}
    for name,keys in tracks.items():
        if not isinstance(keys,list) or len(keys)<2:
            raise ValueError("Every controlled joint needs at least start/end poses")
        results=[]
        prev=-1
        for row in keys:
            if not isinstance(row,dict):
                raise ValueError("Joint keyframe must be an object")
            frame=row.get("frame")
            value=row.get("degrees")
            ease=row.get("interpolation","ease")
            if isinstance(frame,bool) or not isinstance(frame,int) or not 0<=frame<=end or frame<=prev:
                raise ValueError("Acting keyframes must have distinct sorted frame indices")
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>LIMITS[name]:
                raise ValueError("Acting exceeds safe original-art joint limits")
            if ease not in ("ease","linear","hold"):
                raise ValueError("Unknown acting interpolation")
            results.append((frame,float(value),ease))
            prev=frame
        if results[0][0]!=0 or results[-1][0]!=end:
            raise ValueError("Acting must cover full unpadded narration timeline")
        normalized[name]=results
    hand=config.get("rightHandKeys",[{"frame":0,"pose":DEFAULT_HAND}])
    if not isinstance(hand,list) or not hand:
        raise ValueError("Explicit right hand events required")
    sequence=[]
    prev=-1
    for row in hand:
        if not isinstance(row,dict) or row.get("pose") not in HANDS or not isinstance(row.get("frame"),int):
            raise ValueError("Unsupported right-hand original art plate")
        t=row["frame"]
        if isinstance(t,bool) or not 0<=t<=end or t<=prev:
            raise ValueError("Hand poses require sorted in-bounds frames")
        sequence.append((t,row["pose"]))
        prev=t
    if sequence[0][0]!=0:
        raise ValueError("Hand choice at source frame zero required")
    return duration,end,normalized,sequence


class EvanPerformance:
    def __init__(self,config):
        self.duration,self.end,self.tracks,self.hands=validate(config)
        self.frames={k:[p[0] for p in v] for k,v in self.tracks.items()}
        self.hand_frames=[p[0] for p in self.hands]

    def at_frame(self,frame):
        if isinstance(frame,bool) or not isinstance(frame,int) or not 0<=frame<=self.end:
            raise ValueError("Requested original-audio frame outside acting timeline")
        result={}
        for name,keys in self.tracks.items():
            idx=bisect.bisect_right(self.frames[name],frame)-1
            before=keys[idx]
            if idx==len(keys)-1:
                v=before[1]
            else:
                after=keys[idx+1]
                u=(frame-before[0])/(after[0]-before[0])
                if before[2]=="hold":u=0.
                elif before[2]=="ease":u=u*u*(3-2*u)
                v=before[1]+u*(after[1]-before[1])
            result[name]=v
        by_side={}
        for side in ("left","right"):
            by_side[side]=tuple(result.get(side+"."+part,0.) for part in ("shoulder","elbow","wrist"))
        which=self.hands[max(0,bisect.bisect_right(self.hand_frames,frame)-1)][1]
        return {
            "left":by_side["left"],"right":by_side["right"],
            "head":result.get("head",0.),
            "body_roll":result.get("body_roll",0.),
            "brow_left":result.get("brow_left",0.),
            "brow_right":result.get("brow_right",0.),
            "right_hand":which
        }

    def at_seconds(self,seconds):
        if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds):
            raise ValueError("Invalid frame time")
        return self.at_frame(round(seconds*RATE))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("acting_json",type=Path)
    ap.add_argument("--sample-frame",type=int,default=0)
    a=ap.parse_args()
    result=EvanPerformance(json.loads(a.acting_json.read_text()))
    print(json.dumps(result.at_frame(a.sample_frame),indent=2))
    print("ACTING_RIG=ORIGINAL_EVAN")
    print("ARTISTIC_APPROVAL=NO")


if __name__=="__main__":main()
