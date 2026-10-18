"""Frame-accurate integration of original Evan art, chapters, acting and audio.

Generates production work-unit specs, NOT a rendered cartoon. Rejects missing
art, anonymous acting, under-30s audio and unsynchronized sound effects.
"""
import argparse
import json
import math
from pathlib import Path
from original_art_story_gate import inspect_storyboard
from soundtrack_editor import propose


def frame(sec):
    if isinstance(sec,bool) or not isinstance(sec,(float,int)) or not math.isfinite(sec):
        raise ValueError("Non-finite scene time")
    n=round(sec*60)
    if abs(n-sec*60)>.001:raise ValueError("Scene not aligned to a 60fps frame")
    return n


def prepare(chapters,storyboard,registry,artroot,catalog,analysis):
    length=analysis.get("durationSec")
    if not analysis.get("eligibleForProduction") or not isinstance(length,(int,float)) or not 30<=length<=900:
        raise ValueError("Real narration must last >=30 seconds")
    count=math.ceil(length*60-1e-9)
    if chapters.get("kind")!="PREPRODUCTION-ONLY" or chapters.get("fps")!=60:
        raise ValueError("Validated original-audio chapter plan required")
    if (chapters.get("totalTimelineFrames")!=count or
        abs(chapters.get("recordingDurationSeconds",0)-length)>.00001 or
        abs(storyboard.get("durationSec",0)-length)>.00001):
        raise ValueError("Narration, chapter and storyboard timings disagree")
    digest=analysis.get("audioSha256")
    if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Original narration hash required")
    audited=inspect_storyboard(storyboard,registry,artroot)
    if not audited["valid"]:
        raise ValueError("Storyboard source art unavailable: "+"; ".join(audited["problems"][:3]))
    shots=[]
    cur=0
    for idx,s in enumerate(storyboard["shots"],1):
        a=frame(s["start"])
        # Real source audio is not necessarily an exact 60fps multiple. The
        # final frame is a partial source-audio frame, never synthetic silence.
        b=count if idx==len(storyboard["shots"]) else frame(s["end"])
        if a!=cur or b<=a:raise ValueError("Scene frame discontinuity")
        cur=b
        camera=s.get("cameraMotion")
        if not isinstance(camera,dict) or camera.get("mode") not in (
                "tracked","dolly","pan","truck","cut","locked-purposeful"):
            raise ValueError("Specific camera composition required")
        if s.get("kind") in ("action","reaction","object-demo","metaphor"):
            acting=s.get("actorPerformance")
            if not isinstance(acting,dict) or acting.get("sourceRig")!="original-evan-layered":
                raise ValueError("Original layered Evan rig performance required")
            for key in ("bodyAction","facialReaction","eyelineTarget"):
                if not isinstance(acting.get(key),str) or len(acting[key])<12:
                    raise ValueError("Missing real actor direction: "+key)
            ids=acting.get("rigControlIds")
            allowed={"left","right","head","body_roll","brow_left","brow_right","right_hand"}
            if not isinstance(ids,list) or not ids or any(not isinstance(x,str) or x not in allowed for x in ids):
                raise ValueError("Unsupported original Evan rig control")
            if s.get("kind") in ("action","object-demo") and not (set(ids)&{"left","right","body_roll"}):
                raise ValueError("Physical action must animate a real arm or torso control")
        shots.append({"shot":idx,"kind":s["kind"],"startFrame":a,
                      "endFrameExclusive":b,"originalArt":s["originalAssetIds"],
                      "camera":camera,"acting":s.get("actorPerformance")})
    if cur!=count:raise ValueError("Missing final scene frames")
    units=[]
    cur=0
    for c in chapters["chapters"]:
        a,b=c["startFrame"],c["endFrameExclusive"]
        if a!=cur or b<=a or b>count or c.get("sourceAudioIsOriginal") is not True:
            raise ValueError("Chapter gap or non-original audio")
        cur=b
        pieces=[{"shot":s["shot"],"first":max(a,s["startFrame"]),
                 "lastExclusive":min(b,s["endFrameExclusive"])}
                for s in shots if max(a,s["startFrame"])<min(b,s["endFrameExclusive"])]
        if not pieces or pieces[0]["first"]!=a or pieces[-1]["lastExclusive"]!=b:
            raise ValueError("Chapter scene missing")
        if any(x["lastExclusive"]!=y["first"] for x,y in zip(pieces,pieces[1:])):
            raise ValueError("Chapter visual gap")
        units.append({"chapter":c["chapter"],"startFrame":a,"endFrameExclusive":b,
                      "expectedFrames":b-a,"sceneParts":pieces,"rendered":False})
    if cur!=count or len(units)!=chapters["chapterCount"]:
        raise ValueError("Missing final chapter frames")
    cues=propose(storyboard,catalog)
    for fx in cues["effectCues"]:
        s=shots[fx["shot"]-1]
        if not s["startFrame"]<=fx["timeFrame"]<s["endFrameExclusive"]:
            raise ValueError("SFX isn't on its illustrated action frame")
    return {"status":"SCENE-JOBS-PREPARED-NO-FRAMES-RENDERED",
            "fps":60,"durationSec":length,"totalFrames":count,
            "sourceAudioSha256":digest,"originalNarrationChanged":False,
            "landscape":[1920,1080],"portrait":[1080,1920],
            "chapters":units,"shots":shots,"soundCues":cues,
            "originalArtworkVerified":True,
            "rigControlsResolved":False,"phonemesCertified":False,
            "framesRendered":False,"creativeApproved":False}


def main():
    p=argparse.ArgumentParser()
    for name in ("chapters","storyboard","registry","catalog","analysis","output"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    read=lambda path:json.loads(path.read_text())
    output=prepare(read(a.chapters),read(a.storyboard),read(a.registry),
                   a.registry.parent,read(a.catalog),read(a.analysis))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    partial=a.output.with_suffix(".partial")
    partial.write_text(json.dumps(output,indent=2)+"\n")
    partial.replace(a.output)
    print("ROVOR_SCENE_WORK_UNITS="+str(len(output["chapters"])))
    print("ROVOR_FRAMES_TO_RENDER="+str(output["totalFrames"]))
    print("ACTUAL_VIDEO_RENDERED=NO")


if __name__=="__main__":main()
