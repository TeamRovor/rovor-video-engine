"""Confirm that editorial sound effects coincide with *visible* physical action.

Tags and scripts alone are insufficient. A sound effect must name one real
illustrated prop or a supported original Evan control and demonstrate
frame-local actuation in both portrait and landscape.

This is an engineering timing gate, never proof of story quality or audio mix.
"""
from directed_scene import check,interpolate
from performance_tracks import EvanPerformance
import math


def motion_distance(before,after):
    return (abs(before["x"]-after["x"])+abs(before["y"]-after["y"])+
            .33*abs(before["scale"]-after["scale"])+
            .007*abs(before["rotation"]-after["rotation"])+
            .55*abs(before["opacity"]-after["opacity"]))


def actor_change(actor,first,last,channels):
    if actor is None or not channels:
        return 0.
    a,b=actor.at_frame(first),actor.at_frame(last)
    difference=0.
    for channel in channels:
        if channel in ("left","right"):
            difference+=sum(abs(x-y) for x,y in zip(a[channel],b[channel]))/15
        elif channel in ("head","body_roll","brow_left","brow_right"):
            difference+=abs(a[channel]-b[channel])/8
        elif channel=="right_hand":
            difference+=1. if a[channel]!=b[channel] else 0.
        else:
            raise ValueError("Nonexistent original Evan sound-action control")
    return difference


def verify(config,registry,artroot,cues,performance=None,prepared=None):
    prepared=prepared if prepared is not None else check(config,registry,artroot)
    if not isinstance(cues,dict) or cues.get("status")!="EDITORIAL_AUDIO_CUE_PROPOSALS":
        raise ValueError("Authentic SFX/music editorial cue sheet required")
    if cues.get("mixApproved") is not False or cues.get("noAutomaticPublishing") is not True:
        raise ValueError("Production sound must remain review-only")
    if (cues.get("fps")!=60 or abs(cues.get("sourceNarrationSeconds",-1)-
                                  prepared["durationSec"])>.00001):
        raise ValueError("Cue timing doesn't match original narration")
    actor=EvanPerformance(performance) if performance else None
    if actor and abs(actor.duration-prepared["durationSec"])>.025:
        raise ValueError("Character-performance and narration duration disagree")
    records=[]
    shots=prepared["scenes"]
    for cue in cues.get("effectCues",[]):
        if not isinstance(cue,dict):
            raise ValueError("Invalid SFX cue")
        num=cue.get("shot")
        when=cue.get("timeFrame")
        aid=cue.get("animatedAssetId")
        if isinstance(num,bool) or not isinstance(num,int) or not 1<=num<=len(shots):
            raise ValueError("SFX refers to a nonexistent shot")
        shot=shots[num-1]
        if isinstance(when,bool) or not isinstance(when,int) or not shot["startFrame"]<=when<shot["endFrameExclusive"]:
            raise ValueError("SFX outside the illustrated shot")
        if not isinstance(aid,str) or not aid:
            raise ValueError("SFX requires a named actually-animated source object")
        before=max(shot["startFrame"],when-11)
        after=min(shot["endFrameExclusive"],when+12)
        if before==after:
            raise ValueError("SFX has no meaningful surrounding motion")
        evidence=[]
        for view in ("landscape","portrait"):
            elements=shot["compositions"][view]["elements"]
            matched=[row for row in elements if row["assetId"]==aid]
            if len(matched)!=1:
                raise ValueError("SFX object must appear exactly once in each composition")
            row=matched[0]
            if aid=="original-evan-rig":
                channels=cue.get("syncActorChannels",[])
                if not isinstance(channels,list) or not channels:
                    raise ValueError("Actor SFX must declare which real joints/hand move")
                delta=actor_change(actor,before,after,channels)
                threshold=.045
            else:
                delta=motion_distance(interpolate(row["keys"],before),
                                      interpolate(row["keys"],after))
                threshold=.008
            if delta<threshold:
                raise ValueError("Sound effect has no visible synchronized motion in "+view)
            evidence.append(round(delta,5))
        records.append({"timeFrame":when,"shot":num,"assetId":aid,
                        "verifiedMotion":dict(zip(("landscape","portrait"),evidence)),
                        "creativeApproval":False})
    return {"status":"PHYSICAL_AUDIO_CUE_TIMING_EVIDENCE",
            "verifiedEffects":len(records),"evidence":records,
            "musicArrangementApproved":False,
            "creativeSyncApproved":False,
            "mixRendered":False,"published":False}
