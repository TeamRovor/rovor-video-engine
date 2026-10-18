"""Bridge actual WAV + Rhubarb A-H/X to original Evan's painted mouth rig.

This produces an AUDIO-BASED FALLBACK PLAN and never labels approximate
cartoon mouth poses as phone or word boundaries. The renderer's original
painted face and existing English articulation path are unchanged. When a
corrected transcript and two-pass phoneme alignment exist, they supersede
this temporary fallback without altering the underlying recording.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import wave
from speech_planner import audio_envelope,planned_weights

ROOT=Path(__file__).resolve().parent.parent
if str(ROOT/"rovor-production") not in sys.path:
    sys.path.insert(0,str(ROOT/"rovor-production"))
from lip_cue_audit import validate


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for piece in iter(lambda:f.read(1048576),b""):
            h.update(piece)
    return h.hexdigest()


def build(wav,rhubarb_json):
    wav=Path(wav)
    with wave.open(str(wav),"rb") as f:
        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):
            raise ValueError("Original Evan narration needs 16kHz mono PCM16")
        duration=f.getnframes()/f.getframerate()
    audited=validate(rhubarb_json,duration)
    if not audited["shapeCues"]:
        raise ValueError("No actual audio-derived mouth cues to animate")
    fallback=[{"start":cue["start"],"end":cue["end"],"value":cue["shape"]}
              for cue in audited["shapeCues"]]
    result={
        "version":3,
        "kind":"ROVOR_ORIGINAL_EVAN_ACOUSTIC_MOUTH_FALLBACK",
        "sourceNarrationSha256":digest(wav),
        "audio":audio_envelope(wav),
        "durationSec":duration,
        "script":"",
        "coverage":0.,
        "words":[],
        "phonemes":[],
        "gestures":[],
        "fallbackCues":fallback,
        "alignment":{"status":"rhubarb-shape-fallback","phoneConfidence":None},
        "phonemeTimingVerified":False,
        "pronunciationVerified":False,
        "machineWordAnchorsUsed":False,
        "isProductionEligibleByDuration":duration>=30,
        "actualIllustrationFramesRendered":False,
        "creativeApproval":False,
        "warnings":["Rhubarb's A-H/X cues represent acoustic cartoon mouth SHAPES, not English phonemes.",
                    "A verified script and phoneme alignment are still required for certified pronunciation.",
                    "Original Evan painting is preserved; this only supplies weights to existing rig."]
    }
    for t in (0.,duration*.2,duration*.5,min(duration,round(duration*60-1)/60)):
        weights=planned_weights(t,result,result["fallbackCues"])
        if len(weights)!=9 or abs(sum(weights)-1)>1e-5:
            raise ValueError("Rhubarb cues did not map to valid painted mouth weights")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--wav",type=Path,required=True)
    p.add_argument("--rhubarb",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result=build(args.wav,json.loads(args.rhubarb.read_text()))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    tmp=args.out.with_suffix(args.out.suffix+".partial")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    tmp.replace(args.out)
    print("ROVOR_RENDERABLE_ACOUSTIC_MOUTH_FALLBACK=YES")
    print("NATIVE_SOURCE_AUDIO_HASH="+result["sourceNarrationSha256"])
    print("ROVOR_MOUTH_CUES="+str(len(result["fallbackCues"])))
    print("PRODUCTION_ELIGIBLE_DURATION="+str(result["isProductionEligibleByDuration"]).upper())
    print("PHONEME_CERTIFIED=NO")


if __name__=="__main__":
    main()
