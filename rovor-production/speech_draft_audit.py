"""Auditable Whisper draft segmentation; NOT forced phoneme alignment.

Consumes local whisper.cpp JSON and immutable original WAV evidence. Flags
potential hallucinations, omissions, repeated phrases and chapter cuts through
recognized speech. It NEVER assumes ASR is a verified script, never fabricates
missing words, and never declares audio-driven mouth phonemes approved.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import re
import wave
from collections import Counter

TOKENS=re.compile(r"[a-z]+(?:'[a-z]+)?",re.I)


def _time(value,description):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError("Non-finite or missing "+description)
    return float(value)


def extract(whisper,duration):
    if not isinstance(whisper,dict) or not isinstance(whisper.get("transcription"),list):
        raise ValueError("Expected local whisper.cpp transcription array")
    items=[]
    previous_start=-1.
    for idx,row in enumerate(whisper["transcription"]):
        if not isinstance(row,dict):
            raise ValueError("Malformed ASR segment")
        offsets=row.get("offsets")
        if not isinstance(offsets,dict):
            raise ValueError("Missing measured ASR segment offsets")
        begin=_time(offsets.get("from"),"segment start")/1000.
        end=_time(offsets.get("to"),"segment end")/1000.
        if not 0<=begin<end<=duration+.09 or begin<previous_start-.001:
            raise ValueError("Invalid or reordered ASR segment relative to unmodified audio")
        previous_start=begin
        text=row.get("text","")
        if not isinstance(text,str):
            raise ValueError("ASR text must be a string")
        spoken=" ".join(text.split())
        if not spoken:
            continue
        words=TOKENS.findall(spoken.lower())
        flags=[]
        if not words:
            flags.append("non-word-transcription")
        if items and begin < items[-1]["endSeconds"]-.08:
            flags.append("asr-timestamp-overlap")
        if end-begin>32:
            flags.append("segment-longer-than-32sec")
        if len(words)>60:
            flags.append("implausibly-many-words-in-segment")
        if len(words)>0 and (end-begin)/len(words)<.055:
            flags.append("suspect-high-word-density")
        if len(words)>3 and len(set(words))<=2:
            flags.append("repetitive-possible-hallucination")
        items.append({"index":idx,"startSeconds":round(begin,3),"endSeconds":round(min(end,duration),3),
                      "text":spoken,"wordCount":len(words),"reviewFlags":flags})
    return items


def energy_flags(segments,waveform):
    if waveform is None:return
    values=[]
    with Path(waveform).open(newline="") as f:
        r=csv.DictReader(f)
        if not {"time_sec","rms_dbfs"}.issubset(r.fieldnames or []):
            raise ValueError("Invalid original recording waveform CSV")
        prior=-1.
        for row in r:
            t=_time(float(row["time_sec"]),"waveform time")
            v=_time(float(row["rms_dbfs"]),"waveform level")
            if t<=prior:raise ValueError("Unsorted waveform measurements")
            prior=t
            values.append((t,v))
    if not values:raise ValueError("Empty original recording waveform")
    # A genuinely near-silent entire recognized segment suggests a whisper
    # hallucination. Quiet fricatives/word gaps are NOT reliable silence proof.
    import bisect
    times=[x[0] for x in values]
    for item in segments:
        a=bisect.bisect_left(times,item["startSeconds"]+.03)
        b=bisect.bisect_right(times,item["endSeconds"]-.03)
        region=[db for _,db in values[a:b]]
        if len(region)>18 and sum(x<-48 for x in region)/len(region)>.93:
            item["reviewFlags"].append("asr-text-mostly-below-48dbfs")


def audit(whisper,duration,chapters=None,waveform=None):
    duration=_time(duration,"source duration")
    if not 0<duration<=900:
        raise ValueError("Invalid original recording duration")
    rows=extract(whisper,duration)
    energy_flags(rows,waveform)
    repeated=Counter(" ".join(TOKENS.findall(x["text"].lower())) for x in rows)
    for item in rows:
        phrase=" ".join(TOKENS.findall(item["text"].lower()))
        if len(phrase)>=20 and repeated[phrase]>=3:
            item["reviewFlags"].append("same-long-phrase-repeated-three-times")
    cuts=[]
    packages=[]
    if chapters is not None:
        if (not isinstance(chapters,dict) or chapters.get("kind")!="PREPRODUCTION-ONLY"
            or chapters.get("recordingDurationSeconds") is None
            or abs(chapters["recordingDurationSeconds"]-duration)>.03):
            raise ValueError("Chapter plan doesn't match original narration")
        for chapter in chapters["chapters"]:
            a=chapter["sourceAudioStartSeconds"]
            b=chapter["sourceAudioEndSeconds"]
            inside=[x["index"] for x in rows if x["startSeconds"]<b and x["endSeconds"]>a]
            crossing=[x["index"] for x in rows if x["startSeconds"]<b-.03 and x["endSeconds"]>b+.03]
            if crossing and b<duration-.03:
                cuts.append({"chapter":chapter["chapter"],"cutSeconds":b,
                             "ASRSegmentsCrossingBoundary":crossing,
                             "status":"EDITORIAL-LISTEN-AND-RETIME-REQUIRED"})
            packages.append({"chapter":chapter["chapter"],"startSeconds":a,
                             "endSeconds":b,"ASRSegmentIndices":inside,
                             "wordTimingExact":False,"phonemeTimingCertified":False,
                             "scriptEditorReviewRequired":True})
    gaps=[]
    cursor=0.
    for segment in rows:
        if segment["startSeconds"]-cursor>2:
            gaps.append({"fromSec":round(cursor,3),"toSec":segment["startSeconds"],
                         "type":"unrecognized-audio-or-silence-needs-listening"})
        cursor=max(cursor,segment["endSeconds"])
    if duration-cursor>2:
        gaps.append({"fromSec":round(cursor,3),"toSec":round(duration,3),
                     "type":"unrecognized-audio-or-silence-needs-listening"})
    warning_count=sum(len(x["reviewFlags"]) for x in rows)+len(cuts)+len(gaps)
    return {
        "schemaVersion":1,"status":"DRAFT-ASR-REVIEW-REQUIRED",
        "durationSeconds":duration,"segmentCount":len(rows),
        "totalDraftWordCount":sum(x["wordCount"] for x in rows),
        "segments":rows,"longAsrGaps":gaps,"chapterBoundaryConcerns":cuts,
        "chapterIndex":packages,"reviewFlagsCount":warning_count,
        "transcriptHumanVerified":False,"timingHumanVerified":False,
        "wordBoundariesAcousticForced":False,"phonemeBoundariesCertified":False,
        "canDriveFinalMouthAnimation":False,"studioApproval":False,
        "notes":["English spoken words require checking against the original recording.",
                 "Whisper segment timestamps are NOT phoneme timings or verified word boundaries.",
                 "Chapter cuts crossing a segment are candidates for listening, not automatic word splits.",
                 "Never fill silent portions with invented words or mouth movements."],
    }


def _wav_seconds(path):
    with wave.open(str(path),"rb") as f:
        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):
            raise ValueError("Original audio evidence must be 16kHz mono PCM16")
        return f.getnframes()/f.getframerate()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--whisper",type=Path,required=True)
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--chapters",type=Path)
    p.add_argument("--waveform",type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=audit(json.loads(args.whisper.read_text()),_wav_seconds(args.wav),
                 json.loads(args.chapters.read_text()) if args.chapters else None,
                 args.waveform)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    partial=args.out.with_suffix(args.out.suffix+".partial")
    partial.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    partial.replace(args.out)
    print("ROVOR_WHISPER_SEGMENTS="+str(result["segmentCount"]))
    print("ROVOR_DRAFT_WORDS="+str(result["totalDraftWordCount"]))
    print("ROVOR_ASR_REVIEW_FLAGS="+str(result["reviewFlagsCount"]))
    print("ROVOR_TRANSCRIPT_HUMAN_VERIFIED=NO")
    print("ROVOR_PHONEME_ALIGNMENT_CERTIFIED=NO")


if __name__=="__main__":main()
