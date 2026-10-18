"""Chapter preparation for unmodified 30-900 second Rovor narrations.

Optimizes *candidate* chapter cuts using measured speech energy, at native
60fps frame boundaries. This is NOT forced word/phone alignment, a screenplay,
illustration generation, or proof of creativity. No synthetic padding, audio
repeats, fake narration, cloud calls, or added paid dependencies.
"""
import argparse
import csv
import json
import math
from pathlib import Path

FPS = 60
MIN_VIDEO_SECONDS = 30
MAX_AUDIO_SECONDS = 900
TARGET_CHAPTER_SECONDS = 55
MIN_CHAPTER_SECONDS = 30
MAX_CHAPTER_SECONDS = 70
SILENCE_DBFS = -44


def _valid_duration(duration):
    try:
        duration = float(duration)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid recording duration") from exc
    if not math.isfinite(duration) or not MIN_VIDEO_SECONDS <= duration <= MAX_AUDIO_SECONDS:
        raise ValueError("Unmodified narration must be at least 30 seconds and at most 15 minutes")
    return duration


def read_energy(csv_path, duration):
    """Read the existing 10 ms waveform evidence without loading decoded audio."""
    duration = _valid_duration(duration)
    csv_path = Path(csv_path)
    values = []
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"time_sec", "rms_dbfs"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Waveform CSV missing time_sec/rms_dbfs")
        prior = -1.
        for row in reader:
            time = float(row["time_sec"])
            db = float(row["rms_dbfs"])
            if not math.isfinite(time) or not math.isfinite(db):
                raise ValueError("Non-finite waveform timestamp or energy")
            if time < 0 or time <= prior or time > duration + .01:
                raise ValueError("Out-of-order or out-of-bounds waveform sample")
            if db > 10 or db < -180:
                raise ValueError("Invalid waveform dBFS value")
            values.append((time, db))
            prior = time
    if not values or values[0][0] > .02 or duration - values[-1][0] > .04:
        raise ValueError("Waveform does not cover the full narration")
    return values


def _candidate_frames(total, here, energy, fps, minimum, maximum, target):
    remaining = total - here
    if remaining <= maximum:
        return None
    low = here + minimum
    high = min(here + maximum, total - minimum)
    if low > high:
        raise ValueError("Cannot fit another >=30-second chapter")
    ideal = min(high, max(low, here + target))
    # Only select boundaries where observations actually exist. No energy
    # inference is made for missing windows or unknown acoustic phones.
    observations = {}
    for sec, db in energy:
        frame = int(round(sec * fps))
        if low <= frame <= high:
            old = observations.get(frame)
            observations[frame] = db if old is None else min(old, db)

    in_window = [(frame,db) for frame,db in observations.items()
                 if abs(frame - ideal) <= 11*fps]
    silent = [(frame,db) for frame,db in in_window if db <= SILENCE_DBFS]
    if silent:
        # Favor a silence near the desired chapter length, then quieter energy.
        frame,db = min(silent,key=lambda row:(abs(row[0]-ideal),row[1]))
        return (frame,"low-energy-candidate",round(db,2))
    # A quiet dip is NOT automatically a safe phonetic edit point.
    # Any fallback boundary stays editorially unapproved.
    return (ideal,"timing-only-REQUIRES-LISTENING",None)


def plan(duration, energy, fps=FPS, target_seconds=TARGET_CHAPTER_SECONDS,
         min_seconds=MIN_CHAPTER_SECONDS, max_seconds=MAX_CHAPTER_SECONDS):
    duration = _valid_duration(duration)
    if fps != 60 or isinstance(fps,bool):
        raise ValueError("Production chapter frame rate must be 60fps")
    if not 30 <= min_seconds <= target_seconds <= max_seconds <= 120:
        raise ValueError("Invalid chapter size constraints")
    if not isinstance(energy, list) or not energy:
        raise ValueError("Waveform evidence is mandatory; no blind chapter splits")
    for sec,db in energy:
        if not (math.isfinite(sec) and math.isfinite(db)):
            raise ValueError("Non-finite energy evidence")
    count = math.ceil(duration*fps-1e-9)
    minimum = math.ceil(min_seconds*fps)
    maximum = int(max_seconds*fps)
    target = round(target_seconds*fps)
    frames = 0
    chapters = []
    while frames < count:
        nxt = _candidate_frames(count,frames,energy,fps,minimum,maximum,target)
        if nxt is None:
            end=count
            cut="end-of-original-recording"
            db=None
        else:
            end,cut,db=nxt
        if end <= frames or end - frames < minimum:
            raise ValueError("Too-short or non-progressing production chapter")
        chapter_number=len(chapters)+1
        source_start=frames/fps
        source_end=min(duration,end/fps)
        chapters.append({
            "chapter": chapter_number,
            "startFrame": frames,
            "endFrameExclusive": end,
            "decodedFramesTarget": end-frames,
            "timelineStartSeconds": round(source_start,6),
            "timelineEndSeconds": round(end/fps,6),
            "sourceAudioStartSeconds": round(source_start,6),
            "sourceAudioEndSeconds": round(source_end,6),
            "sourceAudioIsOriginal": True,
            "visualPlanStatus": "UNWRITTEN",
            "originalSceneAssetsVerified": False,
            "phonemeTimingCertified": False,
            "boundaryAfter": {
                "type": cut,
                "rmsDbfsAtCandidate": db,
                "requiresAudibleWordBoundaryReview": nxt is not None,
            },
            "minStoryBeats": max(4,math.ceil((end-frames)/fps/9)),
            "artDirectionRequirement": "Original illustrated actions and scene-dependent character acting; static talking-head not accepted",
        })
        frames=end
    if frames != count or chapters[0]["startFrame"] != 0:
        raise ValueError("Chapter output does not cover entire original audio")
    for previous,current in zip(chapters,chapters[1:]):
        if previous["endFrameExclusive"] != current["startFrame"]:
            raise ValueError("Chapter gap/overlap detected")
    return {
        "schemaVersion": 1,
        "kind": "PREPRODUCTION-ONLY",
        "recordingDurationSeconds": round(duration,6),
        "totalTimelineFrames": count,
        "fps": 60,
        "minimumUserVideoSeconds": 30,
        "minimumChapterSeconds": min_seconds,
        "artisticApproval": False,
        "speechTranscriptVerified": False,
        "phonemeAlignmentCertified": False,
        "originalNarrationModified": False,
        "chapterCount": len(chapters),
        "chapters": chapters,
        "notes": [
            "Cuts are candidate edit points from energy measurements, not word boundaries.",
            "Listen and inspect transcript/phoneme alignment near all chapter boundaries before rendering.",
            "Chapters are work units; the deliverable remains the complete >=30-second original narration.",
            "Use existing Evan artwork as source of truth; do not automatically invent finished scene assets.",
        ]
    }


def make_plan(duration, waveform, destination):
    rows = read_energy(waveform,duration)
    result = plan(duration,rows)
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temp=destination.with_suffix(destination.suffix+".partial")
    temp.write_text(json.dumps(result,indent=2)+"\n")
    temp.replace(destination)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration",type=float,required=True)
    parser.add_argument("--waveform",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    result=make_plan(args.duration,args.waveform,args.out)
    print("LONGFORM_CHAPTER_PREPARATION=PASS")
    print("CHAPTER_COUNT="+str(result["chapterCount"]))
    print("TIMELINE_FRAMES="+str(result["totalTimelineFrames"]))
    print("EDITORIAL_APPROVAL=NO")


if __name__=="__main__":
    main()
