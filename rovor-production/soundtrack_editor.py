"""Offline editorial SFX/music decisions for Rovor narration-driven cartoons.

Nothing is mixed or published by this module. It selects only actual licensed
files from the private catalog and only when a specific visual story event
supports their placement. Silence is the default, not an error.

Use:
 python soundtrack_editor.py storyboard.json AudioLibrary/catalog.json --out cues.json
"""
import argparse
import json
import math
from pathlib import Path

FPS = 60
MIN_DURATION = 30.0
MAX_DURATION = 900.0
MIN_SFX_SEPARATION_SEC = 1.5
SFX_GAIN_DB_UNDER_SPEECH = -24.0
SFX_GAIN_DB_NO_SPEECH = -15.0
MUSIC_GAIN_DB_UNDER_SPEECH = -30.0
MUSIC_GAIN_DB_NO_SPEECH = -22.0
MUSIC_VOCALS_WITH_SPEECH = False
SAFE_TAGS = {"browser-click","tab-switch","typing","object-impact","paper",
             "foley","footsteps","transition","logo-reveal","interface",
             "whoosh","notification","comic-reaction","environment",
             "button","background-ambience"}


def fnum(value, label):
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid "+label) from exc
    if not math.isfinite(v):
        raise ValueError("Non-finite "+label)
    return v


def safe_shots(plan):
    if not isinstance(plan,dict):
        raise ValueError("Storyboard must be a JSON object")
    seconds=fnum(plan.get("durationSec"),"durationSec")
    if not MIN_DURATION <= seconds <= MAX_DURATION:
        raise ValueError("Sound design uses real audio >=30 and <=900 seconds")
    shots=plan.get("shots")
    if not isinstance(shots,list) or not shots:
        raise ValueError("Narration-matched storyboard shots required")
    expected=0.
    for idx,shot in enumerate(shots):
        if not isinstance(shot,dict):
            raise ValueError(f"Shot {idx+1} invalid")
        start=fnum(shot.get("start"),"shot start")
        end=fnum(shot.get("end"),"shot end")
        if start < 0 or start>=end or abs(start-expected)>0.018:
            raise ValueError("Storyboard shot gap/overlap")
        expected=end
    if abs(expected-seconds)>.018:
        raise ValueError("Storyboard doesn't cover full original narration")
    return seconds,shots


def speech_intervals(storyboard, duration):
    """Assume continuous dialogue unless verified non-speech intervals supplied."""
    segs=storyboard.get("verifiedSpeechIntervals")
    if segs is None:
        return [(0.,duration)],"unknown-assume-continuous-dialogue"
    if not isinstance(segs,list):
        raise ValueError("verifiedSpeechIntervals should be a list")
    result=[]
    for seg in segs:
        if not isinstance(seg,dict):
            raise ValueError("Invalid speech interval")
        a=fnum(seg.get("start"),"speech start")
        b=fnum(seg.get("end"),"speech end")
        if a<0 or a>=b or b>duration+.02:
            raise ValueError("Speech interval out of narration")
        result.append((a,b))
    if any(result[i][1]>result[i+1][0] for i in range(len(result)-1)):
        raise ValueError("Speech interval list overlaps/out of order")
    if not storyboard.get("speechIntervalsHumanReviewed"):
        # A transcript/ASR draft is not proof of silence or safe sound openings.
        return [(0.,duration)],"unreviewed-speech-intervals-assume-continuous"
    return result,"human-reviewed-timed-speech"


def intersects(intervals,begin,end):
    return any(a<end and b>begin for a,b in intervals)


def catalog_assets(catalog):
    if not isinstance(catalog,dict) or catalog.get("schemaVersion")!=1:
        raise ValueError("Missing verified audio-library catalog")
    if catalog.get("approvedForAutomatedPublishing") is True:
        raise ValueError("Catalog cannot automatically confer publishing approval")
    output={}
    for row in catalog.get("assets",[]):
        if not isinstance(row,dict):
            raise ValueError("Invalid catalog record")
        key=row.get("assetId")
        if not isinstance(key,str) or not key or key in output:
            raise ValueError("Invalid or duplicate licensed assetId")
        if row.get("category") not in ("sound-effect","background-music"):
            raise ValueError("Invalid audio category")
        if row.get("ownerConfirmedRights") is not True:
            raise ValueError("Catalog record missing owner-confirmed rights")
        d=fnum(row.get("durationSeconds"),"asset duration")
        if d<=0 or not isinstance(row.get("eventTags"),list):
            raise ValueError("Catalog asset missing audio description")
        output[key]=row
    return output


def choose_asset(assets,category,tag,*,instrumental_only=False, max_duration=None):
    if not isinstance(tag,str) or not tag.strip() or len(tag)>48:
        raise ValueError("Missing precise auditory event or music mood")
    candidates=[]
    for a in assets.values():
        if a["category"]!=category:
            continue
        if instrumental_only and a.get("vocalContent")!="instrumental":
            continue
        if max_duration is not None and a["durationSeconds"]>max_duration:
            continue
        tags=[str(x).strip().lower() for x in a["eventTags"]]
        if tag.lower() not in tags and tag.lower()!=str(a.get("mood","")).lower():
            continue
        # Prefer recorded/artistic cues that are short and specific. Stable tie.
        candidates.append((a["durationSeconds"],a["assetId"],a))
    return min(candidates)[2] if candidates else None


def propose(storyboard,catalog):
    duration, shots = safe_shots(storyboard)
    assets=catalog_assets(catalog)
    speech,evidence=speech_intervals(storyboard,duration)
    effects=[]
    music=[]
    skipped=[]
    missing=[]
    last_sfx=-999.
    last_music=None
    for i,shot in enumerate(shots,1):
        start=fnum(shot["start"],"start")
        end=fnum(shot["end"],"end")
        scene_name=shot.get("scene","scene-"+str(i))
        direction=shot.get("soundDirection") or {}
        if not isinstance(direction,dict):
            raise ValueError(f"Shot {i}: invalid soundDirection")
        if direction.get("intentionalSilence") is True:
            skipped.append({"shot":i,"reason":"Story requests silence: no music and no effects"})
            continue

        # Sound effects never originate from text heuristics alone. A director-
        # annotated physical event is required to place a cue.
        events=direction.get("physicalEvents",[])
        if not isinstance(events,list):
            raise ValueError(f"Shot {i}: invalid physicalEvents")
        for event in events:
            if not isinstance(event,dict):
                raise ValueError(f"Shot {i}: malformed event")
            event_at=fnum(event.get("atSec"),"effect timing")
            tag=event.get("eventTag")
            purpose=event.get("visualAction")
            if not isinstance(tag,str) or tag not in SAFE_TAGS:
                raise ValueError(f"Shot {i}: unknown event category")
            if not isinstance(purpose,str) or len(purpose.strip())<12:
                raise ValueError(f"Shot {i}: effect lacks actual illustrated action")
            if not (start<=event_at<end) or event_at>=duration:
                raise ValueError(f"Shot {i}: effect outside matching visual action")
            if event_at-last_sfx<MIN_SFX_SEPARATION_SEC:
                skipped.append({"shot":i,"timeSec":event_at,
                                "reason":"Avoid repetitive/fatiguing SFX stacking"})
                continue
            item=choose_asset(assets,"sound-effect",tag,max_duration=12)
            if item is None:
                missing.append({"shot":i,"eventTag":tag,"timeSec":event_at,
                                "neededFor":"original on-screen action: "+purpose})
                continue
            has_voice=intersects(speech,event_at,event_at+min(item["durationSeconds"],1.))
            # Nonessential effects remain a proposal, and stay very quiet
            # when speech is present; normal narration takes precedence.
            if has_voice and event.get("overDialogue")!="quiet-underlay":
                skipped.append({"shot":i,"timeSec":event_at,
                                "reason":"No explicit approval to put SFX under dialogue"})
                continue
            gain=SFX_GAIN_DB_UNDER_SPEECH if has_voice else SFX_GAIN_DB_NO_SPEECH
            effects.append({"timeFrame":round(event_at*FPS),"atSec":round(round(event_at*FPS)/FPS,6),
                            "assetId":item["assetId"],"type":"sound-effect",
                            "gainDbProposal":gain,"underDialogue":has_voice,"shot":i,
                            "scene":scene_name,"syncsWithVisibleAction":purpose,
                            "approvalRequired":True})
            last_sfx=event_at

        music_tag=direction.get("musicMood")
        if music_tag in (None,"none","silence"):
            if music_tag in ("none","silence"):
                skipped.append({"shot":i,"reason":"No music by scene direction"})
            continue
        if not isinstance(music_tag,str) or len(music_tag)>48:
            raise ValueError("Invalid musical mood")
        over_voice=intersects(speech,start,end)
        item=choose_asset(assets,"background-music",music_tag,
                          instrumental_only=over_voice)
        if item is None:
            missing.append({"shot":i,"musicMood":music_tag,
                            "neededFor":"licensed instrumental underscore" if over_voice else "licensed background music"})
            continue
        if over_voice and item.get("vocalContent")!="instrumental":
            skipped.append({"shot":i,"reason":"Vocal music competes with narration"})
            continue
        bed={"startFrame":round(start*FPS),"endFrameExclusive":round(end*FPS),
             "startSec":start,"endSec":end,"assetId":item["assetId"],
             "type":"background-music","gainDbProposal":MUSIC_GAIN_DB_UNDER_SPEECH
             if over_voice else MUSIC_GAIN_DB_NO_SPEECH,
             "underDialogue":over_voice,"mood":music_tag,"shot":i,
             "fadeInMsProposal":350,"fadeOutMsProposal":500,
             "approvalRequired":True,"loopingNeedsEditorCheck":end-start>item["durationSeconds"]}
        # Merge adjacent matching beds to avoid audible clip restarts.
        if last_music is not None and (last_music["assetId"]==bed["assetId"]
                and last_music["endFrameExclusive"]==bed["startFrame"]
                and last_music["underDialogue"]==bed["underDialogue"]):
            last_music["endFrameExclusive"]=bed["endFrameExclusive"]
            last_music["endSec"]=bed["endSec"]
            last_music["loopingNeedsEditorCheck"]|=bed["loopingNeedsEditorCheck"]
            continue
        music.append(bed)
        last_music=bed
    return {
        "schemaVersion":1,
        "status":"EDITORIAL_AUDIO_CUE_PROPOSALS",
        "sourceNarrationSeconds":duration,
        "fps":FPS,
        "speechEvidence":evidence,
        "effectCues":effects,
        "musicBeds":music,
        "missingAssets":missing,
        "skippedForClarity":skipped,
        "noAutomaticPublishing":True,
        "mixApproved":False,
        "lipSyncUnaffected":True,
        "rules":["No effect without matching visible event and precise timestamp.",
                 "Silence is intentional: don't add music automatically.",
                 "No vocal music under narration.",
                 "Under-speech music/effects remain quiet and ducked; mastering requires listening.",
                 "Do not assume waveform dips are speech-free unless reviewed.",
                 "No uploading or mixing private audio without review approval.",
                 "Music is not proof of scene quality; Evan narration is always first."],
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("storyboard",type=Path)
    ap.add_argument("catalog",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    data=propose(json.loads(args.storyboard.read_text()),
                 json.loads(args.catalog.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    temp=args.out.with_suffix(args.out.suffix+".partial")
    temp.write_text(json.dumps(data,indent=2)+"\n")
    temp.replace(args.out)
    print("ROVOR_SFX_PROPOSED="+str(len(data["effectCues"])))
    print("ROVOR_MUSIC_BEDS_PROPOSED="+str(len(data["musicBeds"])))
    print("ROVOR_AUDIO_ASSETS_MISSING="+str(len(data["missingAssets"])))
    print("AUDIO_MIX_APPROVED=NO")


if __name__ == "__main__":
    main()
