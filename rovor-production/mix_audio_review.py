"""Non-destructive Rovor soundtrack audition mix.

Maintains original narration on disk, decodes it once via local FFmpeg, and
renders proposal-only WAV mixing approved-source original SFX/instrumental
assets. No publications, no paid providers, no lip-sync certification.

Use:
  python3 mix_audio_review.py NARRATION.mp3 cues.json OUTPUT.wav --ffmpeg FFMPEG_PATH

Designed for 30-900-second input; streaming one second at a time so 9-minute
recordings don't consume huge amounts of memory. No song is looped automatically.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave
import numpy as np
from audio_library import ROOT, scan, CATEGORIES, sha256

RATE=48000
SAMPLES_PER_FRAME=RATE//60
BLOCK_FRAMES=RATE
MAX_DURATION=900.
MIN_DURATION=30.
MIX_PEAK_CEILING=.985


def _number(v,name):
    try:
        v=float(v)
    except (TypeError,ValueError) as e:
        raise ValueError(name+" must be numeric") from e
    if not math.isfinite(v):
        raise ValueError(name+" is not finite")
    return v


def _decode_track(ffmpeg,path):
    result=subprocess.run([str(ffmpeg),"-nostdin","-hide_banner","-loglevel","error",
                           "-i",str(path),"-map","0:a:0","-vn","-ac","2",
                           "-ar",str(RATE),"-f","s16le","pipe:1"],
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          timeout=180,check=True)
    if not result.stdout or len(result.stdout)%4!=0:
        raise ValueError("Empty/nonstereo sound asset: "+path.name)
    return np.frombuffer(result.stdout,dtype="<i2").reshape(-1,2).astype(np.float32)/32768.


def _validated_assets(cues,catalog,root,ffmpeg):
    if cues.get("status")!="EDITORIAL_AUDIO_CUE_PROPOSALS" or cues.get("mixApproved") is not False:
        raise ValueError("Only unapproved editorial cue proposals may be rendered for preview")
    if cues.get("noAutomaticPublishing") is not True:
        raise ValueError("Audio preview cannot authorize release")
    available={r["assetId"]:r for r in catalog["assets"]}
    referred=set()
    for group in ("effectCues","musicBeds"):
        for row in cues.get(group,[]):
            if not isinstance(row,dict) or row.get("assetId") not in available:
                raise ValueError("Cue refers to nonexistent, unlicensed or unverified sound")
            referred.add(row["assetId"])
    decoded={}
    for key in sorted(referred):
        meta=available[key]
        name=meta["filename"]
        if Path(name).name!=name or Path(name).is_absolute():
            raise ValueError("Unsafe media catalog filename")
        path=Path(root)/CATEGORIES[meta["category"]]/name
        if not path.is_file() or path.is_symlink() or sha256(path)!=meta["sha256"]:
            raise ValueError("Media missing or changed since catalog scan")
        decoded[key]=_decode_track(ffmpeg,path)
    return available,decoded


def _gain(row,expected):
    if row.get("type")!=expected:
        raise ValueError("Wrong cue type")
    db=_number(row.get("gainDbProposal"),"gainDbProposal")
    if not -70<=db<=-12:
        raise ValueError("Unsafe cue gain (all mix cues must be background level)")
    return 10**(db/20)


def _prepare(cues,decoded):
    effects=[]
    beds=[]
    for e in cues.get("effectCues",[]):
        gain=_gain(e,"sound-effect")
        frame=e.get("timeFrame")
        if isinstance(frame,bool) or not isinstance(frame,int) or frame<0:
            raise ValueError("Invalid SFX 60fps frame position")
        samples=decoded[e["assetId"]]
        effects.append((frame*SAMPLES_PER_FRAME,samples,gain))
    for bed in cues.get("musicBeds",[]):
        gain=_gain(bed,"background-music")
        start=bed.get("startFrame")
        end=bed.get("endFrameExclusive")
        if (isinstance(start,bool) or not isinstance(start,int) or
                isinstance(end,bool) or not isinstance(end,int) or
                start<0 or end<=start):
            raise ValueError("Invalid background-music frame range")
        length=(end-start)*SAMPLES_PER_FRAME
        source=decoded[bed["assetId"]]
        if length>len(source):
            raise ValueError("Loop or music extension requires deliberate editor review; refusing auto-loop")
        fadein=max(0,round(_number(bed.get("fadeInMsProposal",0),"fadeInMs")*RATE/1000))
        fadeout=max(0,round(_number(bed.get("fadeOutMsProposal",0),"fadeOutMs")*RATE/1000))
        if fadein>length//2 or fadeout>length//2:
            raise ValueError("Music fade is too long for the selected scene")
        beds.append((start*SAMPLES_PER_FRAME,end*SAMPLES_PER_FRAME,
                     source,gain,fadein,fadeout))
    return effects,beds


def _add_cues(out,offset,effects,beds):
    stop=offset+len(out)
    for start,source,gain in effects:
        a=max(start,offset)
        b=min(start+len(source),stop)
        if a<b:
            out[a-offset:b-offset]+=source[a-start:b-start]*gain
    for start,end,source,gain,fadein,fadeout in beds:
        a=max(start,offset)
        b=min(end,stop)
        if a>=b:continue
        idx=np.arange(a-start,b-start,dtype=np.int64)
        env=np.ones(len(idx),dtype=np.float32)
        if fadein:
            np.minimum(env,idx/fadein,out=env)
        if fadeout:
            np.minimum(env,(end-start-idx)/fadeout,out=env)
        out[a-offset:b-offset]+=source[idx]*gain*env[:,None]


def mix_review(narration,cues_path,output,*,root=ROOT,ffmpeg):
    narration=Path(narration).expanduser()
    output=Path(output).expanduser()
    cues=json.loads(Path(cues_path).read_text())
    duration=_number(cues.get("sourceNarrationSeconds"),"narration duration")
    if not MIN_DURATION<=duration<=MAX_DURATION:
        raise ValueError("Full >=30-second original narration is required")
    if cues.get("fps")!=60:
        raise ValueError("Cue timing must use 60fps")
    if not narration.is_file() or narration.is_symlink() or narration.stat().st_size<128:
        raise ValueError("Source narration missing or symlinked")
    if output.exists() or output.with_suffix(".partial.wav").exists():
        raise FileExistsError("Never overwrite an existing mixed preview")
    output.parent.mkdir(parents=True,exist_ok=True)
    catalog=scan(root)
    available,decoded=_validated_assets(cues,catalog,root,ffmpeg)
    effects,beds=_prepare(cues,decoded)
    # Ensure all editorial cues stay within the observed source-timeline length.
    max_samples=math.ceil(duration*RATE)
    if any(start>=max_samples for start,_,_ in effects):
        raise ValueError("Effect cue outside original narration")
    if any(end>max_samples+RATE//60 for _,end,*_ in beds):
        raise ValueError("Music cue outside original narration")
    process=subprocess.Popen([
        str(ffmpeg),"-nostdin","-hide_banner","-loglevel","error",
        "-i",str(narration),"-map","0:a:0","-vn","-ar",str(RATE),
        "-ac","2","-f","s16le","pipe:1"
    ],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    temp=output.with_suffix(".partial.wav")
    offset=0
    overall_peak=0.
    sumsq=0.
    try:
        with wave.open(str(temp),"wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            while True:
                raw=process.stdout.read(BLOCK_FRAMES*4)
                if not raw:break
                if len(raw)%4:
                    raise ValueError("Truncated decoded narration PCM")
                voice=np.frombuffer(raw,dtype="<i2").reshape(-1,2).astype(np.float32)/32768
                out=voice.copy()
                _add_cues(out,offset,effects,beds)
                peak=float(np.max(np.abs(out)))
                if peak>MIX_PEAK_CEILING:
                    raise ValueError("Overpeak in audition; reduce track levels before mixing")
                overall_peak=max(overall_peak,peak)
                sumsq+=float(np.sum(out.astype(np.float64)**2))
                pcm=np.rint(out*32767).clip(-32768,32767).astype("<i2")
                wav.writeframesraw(pcm.tobytes())
                offset+=len(out)
                if offset>(MAX_DURATION+1)*RATE:
                    raise ValueError("Source narration longer than 15min")
        code=process.wait(timeout=30)
        if code:
            err=process.stderr.read().decode("utf-8",errors="replace")[:400]
            raise ValueError("FFmpeg narration decoding failed: "+err)
        actual=offset/RATE
        if abs(actual-duration)>.07:
            raise ValueError("Original narration and storyboard length mismatch")
        temp.replace(output)
    except Exception:
        process.kill()
        process.wait()
        if temp.exists():temp.unlink()
        raise
    report={
        "status":"AUDIO_REVIEW_ONLY_NOT_A_FINAL_SOUNDTRACK",
        "durationSeconds":round(actual,6),
        "sampleRate":RATE,
        "channels":2,
        "samplesPerChannel":offset,
        "audioSha256":sha256(output),
        "sourceNarrationSha256":sha256(narration),
        "narrationSourceUnchanged":True,
        "peakDbfs":round(20*math.log10(max(overall_peak,1e-8)),2),
        "overallRmsDbfs":round(20*math.log10(max(math.sqrt(sumsq/(2*offset)),1e-8)),2),
        "effectCount":len(effects),
        "musicBedCount":len(beds),
        "requiredAttributions":cues.get("requiredAttributions",[]),
        "publicationApproved":False,
        "lipSyncCertified":False,
        "creativeMixApproved":False,
        "clip":str(output),
        "notes":"Output is an editorial mix audition. Recheck voice intelligibility, cue timing, dynamic range and attribution with the actual animation before release."
    }
    report_path=output.with_suffix(".mix-review.json")
    report_path.write_text(json.dumps(report,indent=2)+"\n")
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("narration",type=Path)
    ap.add_argument("cues",type=Path)
    ap.add_argument("output",type=Path)
    ap.add_argument("--root",type=Path,default=ROOT)
    ap.add_argument("--ffmpeg",type=Path,required=True)
    args=ap.parse_args()
    result=mix_review(args.narration,args.cues,args.output,root=args.root,ffmpeg=args.ffmpeg)
    print("ROVOR_SOUNDTRACK_REVIEW=RENDERED")
    print("NARRATION_UNCHANGED=YES")
    print("DURATION="+str(result["durationSeconds"]))
    print("PUBLICATION_APPROVED=NO")


if __name__=="__main__":
    main()
