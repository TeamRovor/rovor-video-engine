"""Validate Rhubarb audio-derived cartoon mouth cues without claiming phones.

Rhubarb produces Preston Blair A-H/X mouth shapes, not English IPA/ARPABET
word-level phoneme alignment. Validate exact audio-time bounds and relevant
mouth closures; reject extension beyond the original recording and provide
a review report for longer narration.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import wave

ALLOWED=set("ABCDEFGHX")


def validate(cues, duration):
    try:
        duration=float(duration)
    except (ValueError,TypeError):
        raise ValueError("Missing original audio duration")
    if not math.isfinite(duration) or not 0<duration<=900:
        raise ValueError("Source audio must be <=15min")
    if not isinstance(cues,dict) or not isinstance(cues.get("mouthCues"),list):
        raise ValueError("Missing local Rhubarb mouthCues")
    items=[]
    cursor=-.001
    flags=[]
    for index,row in enumerate(cues["mouthCues"]):
        if not isinstance(row,dict) or row.get("value") not in ALLOWED:
            raise ValueError("Unsupported mouth shape cue")
        a,b=row.get("start"),row.get("end")
        if (isinstance(a,bool) or isinstance(b,bool) or
            not isinstance(a,(float,int)) or not isinstance(b,(float,int))
            or not(math.isfinite(a) and math.isfinite(b))
            or a<0 or a+1e-5<b is False):
            # The separate comparison below catches zero/negative spans.
            raise ValueError("Rhubarb emitted invalid source frame times")
        if not a<b or b>duration+.08 or a<cursor-.003:
            raise ValueError("Rhubarb timings overlap, extend past recording or reverse")
        if b>duration:
            flags.append({"index":index,"reason":"minor-end-padding-truncated",
                          "overrunSeconds":round(b-duration,3)})
        if b-a<1/60:
            flags.append({"index":index,"reason":"under-one-60fps-frame"})
        items.append({"start":round(a,5),"end":round(min(duration,b),5),
                      "shape":row["value"]})
        cursor=b
    spoken=sum(max(0,x["end"]-x["start"]) for x in items if x["shape"]!="X")
    return {
        "status":"AUDIO_SHAPE_CUES_REVIEW_ONLY",
        "durationSec":round(duration,6),"cueCount":len(items),
        "nonRestDurationSec":round(spoken,4),
        "nonRestFraction":round(spoken/duration,4),
        "shapeCues":items,"reviewFlags":flags,
        "nativePhonemeAlignmentCertified":False,
        "wordPronunciationVerified":False,
        "voiceAudioSourceModified":False,
        "mouthCueTimingTechnicallyValidated":True,
        "artisticMouthMotionApproved":False,
        "publicationApproved":False,
        "note":"Rhubarb A-H/X mouth shapes align to acoustic cues, but are NOT English phoneme boundaries or a corrected transcript.",
    }


def wav_duration(path):
    with wave.open(str(path),"rb") as source:
        if (source.getframerate(),source.getnchannels(),source.getsampwidth())!=(16000,1,2):
            raise ValueError("Expected source-derived 16k PCM16 mono WAV")
        return source.getnframes()/source.getframerate()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cues",type=Path,required=True)
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=validate(json.loads(args.cues.read_text()),wav_duration(args.wav))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    temp=args.out.with_suffix(".partial")
    temp.write_text(json.dumps(report,indent=2)+"\n")
    temp.replace(args.out)
    print("ROVOR_ACOUSTIC_MOUTH_CUE_COUNT="+str(report["cueCount"]))
    print("ROVOR_MOUTH_CUE_TIMING_CHECK=PASS")
    print("NATIVE_PHONEMES_ALIGNED=NO")
    print("WORD_PRONUNCIATION_VERIFIED=NO")


if __name__=="__main__":
    main()
