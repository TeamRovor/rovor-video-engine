"""Turn director-chosen story moments into deliberate original-Evan acting.

A bounded FK blocking assistant, not generic random hand waves. The director
must specify the visually meaningful event and exact narration frame.
Each moment has anticipation, a purposeful pose, a hold and recovery.
It only uses the real available hand art and joint channels.

The result is an opt-in performance_tracks.py JSON for existing CartoonBody,
NOT studio-quality approval or a substitute for missing leg/finger/3D art.
"""
import argparse
import json
import math
from pathlib import Path
from performance_tracks import LIMITS,EvanPerformance

FPS=60
PRESETS={
 "notice":{
    "head":-1.7,"brow_left":2.2,"brow_right":1.5,
    "right.shoulder":-1.3,"right.elbow":-3.5,"body_roll":-.35
 },
 "present":{
    "right.shoulder":-6.0,"right.elbow":-15.0,"right.wrist":4.5,
    "head":-.75,"brow_left":1.0,"body_roll":.3
 },
 "recoil":{
    "right.shoulder":5.5,"right.elbow":13,"right.wrist":-3.5,
    "left.shoulder":-4.0,"left.elbow":7.0,
    "head":1.8,"brow_left":-2.0,"brow_right":-1.5,"body_roll":-1.0
 },
 "compare":{
    "left.shoulder":4.5,"left.elbow":-10.0,
    "right.shoulder":-3.0,"right.elbow":-10.0,
    "head":-.8,"brow_left":1.2,"brow_right":1.5
 },
 "emphasize":{
    "right.shoulder":-4.0,"right.elbow":-12.0,"right.wrist":3.0,
    "head":-1.0,"brow_left":1.0,"body_roll":.55
 },
 "punchline":{
    "right.shoulder":3.2,"right.elbow":8.0,
    "left.shoulder":2.2,"left.elbow":7.0,
    "head":1.4,"brow_left":-2.8,"brow_right":-2.2,"body_roll":.75
 }
}
HAND={"present":"point","recoil":"relaxed","emphasize":"point","punchline":"relaxed"}


def number(value,minimum,maximum,label):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not minimum<=value<=maximum:
        raise ValueError("Out-of-range "+label)
    return value


def build(spec):
    if not isinstance(spec,dict) or spec.get("schemaVersion")!=1:
        raise ValueError("Director moment sheet required")
    if spec.get("sourceRig")!="original-evan-layered":
        raise ValueError("Original character artwork is required")
    duration=number(spec.get("durationSec"),30,900,"source narration duration")
    end=math.ceil(duration*FPS-1e-9)
    moments=spec.get("moments")
    if not isinstance(moments,list) or not moments:
        raise ValueError("Actual authored story moments required")
    if len(moments)>math.ceil(duration/3):
        raise ValueError("Too many gestures: prioritize distinct narrative actions")
    normalized=[]
    cursor=-1
    for m in moments:
        if not isinstance(m,dict):
            raise ValueError("Malformed director story beat")
        key=m.get("kind")
        if key not in PRESETS:
            raise ValueError("Unknown original Evan acting vocabulary")
        purpose=m.get("visualPurpose")
        if not isinstance(purpose,str) or len(purpose.strip())<18:
            raise ValueError("Missing specific original narrated visual motivation")
        at=m.get("atFrame")
        if isinstance(at,bool) or not isinstance(at,int) or not 0<=at<end:
            raise ValueError("An acting beat must have an exact source frame")
        intensity=number(m.get("intensity",.7),.2,1.0,"expressive intensity")
        anticipate=m.get("anticipateFrames",10)
        action=m.get("actionFrames",13)
        hold=m.get("holdFrames",10)
        settle=m.get("settleFrames",20)
        for name,value,lo,hi in (("anticipateFrames",anticipate,6,24),
                                  ("actionFrames",action,8,32),
                                  ("holdFrames",hold,4,48),
                                  ("settleFrames",settle,12,45)):
            if isinstance(value,bool) or not isinstance(value,int) or not lo<=value<=hi:
                raise ValueError("Invalid authored "+name)
        start=at-anticipate-action
        prep=at-action
        release=at+hold
        finish=release+settle
        if start<0 or finish>end:
            raise ValueError("Acting beat exceeds original narration; no artificial padding")
        if start<cursor+8:
            raise ValueError("Gestures overlap or have no intentional resting break")
        cursor=finish
        normalized.append({"kind":key,"purpose":purpose,
                           "intensity":intensity,"start":start,"anticipation":prep,
                           "impact":at,"release":release,"end":finish})
    channels={}
    names=sorted({channel for m in normalized for channel in PRESETS[m["kind"]]})
    for name in names:
        keys=[{"frame":0,"degrees":0.}]
        last=0
        for moment in normalized:
            target=PRESETS[moment["kind"]].get(name,0.)*moment["intensity"]
            if abs(target)>LIMITS[name]:
                raise ValueError("Original drawn joint safety limit")
            if moment["start"]!=last:
                keys.append({"frame":moment["start"],"degrees":0.,"interpolation":"hold"})
            else:
                # A consecutive curve may share its previous ending keyframe.
                pass
            if moment["start"]==0:
                raise ValueError("First original frame cannot contain anticipation")
            keys.extend([
                {"frame":moment["anticipation"],"degrees":-.16*target},
                {"frame":moment["impact"],"degrees":target},
                {"frame":moment["release"],"degrees":target},
                {"frame":moment["end"],"degrees":0.},
            ])
            last=moment["end"]
        if last!=end:
            keys.append({"frame":end,"degrees":0.})
        channels[name]=keys

    hands=[{"frame":0,"pose":"open"}]
    last_hand=0
    for moment in normalized:
        pose=HAND.get(moment["kind"])
        if not pose:continue
        at=moment["impact"]-3
        if at<=last_hand or at>=moment["end"]:
            raise ValueError("Hand plate change has no safe frame")
        hands.append({"frame":at,"pose":pose})
        hands.append({"frame":moment["end"],"pose":"open"})
        last_hand=moment["end"]
    out={"schemaVersion":1,"sourceRig":"original-evan-layered",
         "durationSec":duration,"channels":channels,"rightHandKeys":hands,
         "storyBeatCount":len(normalized),
         "storyBeats":normalized,
         "handArtwork":"original-open-relaxed-point",
         "phonemeTimingCertified":False,"actingArtistApproved":False,
         "continuousIdleWiggling":False}
    # Verify generated tracks satisfy the actual runtime, not a made-up rig.
    EvanPerformance(out)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("moments",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    output=build(json.loads(a.moments.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    partial=a.output.with_suffix(".partial")
    partial.write_text(json.dumps(output,indent=2)+"\n")
    partial.replace(a.output)
    print("ORIGINAL_EVAN_NARRATIVE_ACTING_BEATS="+str(output["storyBeatCount"]))
    print("UNPROMPTED_IDLE_WIGGLING=NO")
    print("ACTING_ARTIST_APPROVAL=NO")


if __name__=="__main__":
    main()
