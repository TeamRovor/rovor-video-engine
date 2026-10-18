"""Verify complete original Evan 1080p60 video without loading 9 minutes of audio.

Checks every decoded video frame and its PTS, true frame count, dimensions,
audio duration and localized matching to the immutable original voice at
distributed checkpoints. This is a technical integrity gate ONLY: it does
not certify phonemes, art direction, narrative quality, or publication.
Uses installed local FFmpeg, numpy, streaming memory bounds, no paid API.
"""
import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
import subprocess
import wave
import numpy as np

FPS=60
SAMPLE_RATE=16000
AUDIO_TOLERANCE_SEC=.075
MAX_AUDIO_LAG_SEC=.03


def duration_wav(wav):
    with wave.open(str(wav),"rb") as f:
        if (f.getnchannels(),f.getsampwidth(),f.getframerate())!=(1,2,SAMPLE_RATE):
            raise ValueError("Original narrator reference must be 16kHz PCM16 mono")
        n=f.getnframes()
    duration=n/SAMPLE_RATE
    if not 0<duration<=900:
        raise ValueError("Source narration must be within 15 minutes")
    return n,duration


def _read_video_frames(ffmpeg,video,size,expected,rate=FPS):
    command=[str(ffmpeg),"-nostdin","-hide_banner","-loglevel","error",
             "-xerror","-i",str(video),"-map","0:v:0",
             "-fps_mode","passthrough","-f","framemd5","pipe:1"]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             text=True,bufsize=1)
    count=0
    timebase=None
    dimensions=None
    prior_pts=-1
    try:
        for raw in process.stdout:
            line=raw.strip()
            if line.startswith("#tb 0:"):
                timebase=Fraction(line.split(":",1)[1].strip())
            elif line.startswith("#dimensions 0:"):
                dims=line.split(":",1)[1].strip()
                dimensions=tuple(map(int,dims.split("x")))
            elif line and not line.startswith("#"):
                parts=[x.strip() for x in line.split(",")]
                if len(parts)<6:
                    raise ValueError("Malformed frame checksum row")
                if timebase is None:
                    raise ValueError("No video stream timebase from FFmpeg")
                pts=int(parts[2])
                duration=int(parts[3])
                position=float(pts*timebase)
                if pts<=prior_pts or duration<=0:
                    raise ValueError("Non-monotonic or zero-duration decoded video frames")
                if abs(position-count/rate)>.0015:
                    raise ValueError(f"Video timestamp discontinuity at frame {count}: {position:.5f}")
                prior_pts=pts
                count+=1
                if count>expected:
                    raise ValueError("Unexpected extra video frames")
        error=process.stderr.read()
        ret=process.wait(timeout=25)
        if ret:
            raise ValueError("Video decode failed: "+error[-350:])
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
    if dimensions!=tuple(size):
        raise ValueError("Wrong decoded video dimensions "+str(dimensions))
    if count!=expected:
        raise ValueError(f"Truncated video: expected {expected}, decoded {count}")
    return {"decodedFrames":count,"decodedDimensions":list(size),
            "decodedPtsMonotonicAndAt60Fps":True}


def _decode_window(ffmpeg,source,start,seconds):
    command=[str(ffmpeg),"-nostdin","-hide_banner","-loglevel","error",
             "-ss",f"{start:.6f}","-i",str(source),
             "-map","0:a:0","-vn","-t",f"{seconds:.6f}",
             "-ac","1","-ar",str(SAMPLE_RATE),
             "-f","s16le","pipe:1"]
    res=subprocess.run(command,capture_output=True,check=True,timeout=120)
    if len(res.stdout)%2:
        raise ValueError("Truncated PCM16 audio stream")
    return np.frombuffer(res.stdout,dtype="<i2").astype(np.float32)/32768.


def _audio_length_samples(ffmpeg,video):
    command=[str(ffmpeg),"-nostdin","-hide_banner","-loglevel","error",
             "-xerror","-i",str(video),"-map","0:a:0","-vn",
             "-ac","1","-ar",str(SAMPLE_RATE),"-f","s16le","pipe:1"]
    process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    count=0
    try:
        while True:
            raw=process.stdout.read(128*1024)
            if not raw:
                break
            count+=len(raw)
            if count%2:
                raise ValueError("Incomplete PCM sample")
            if count>int((900+1)*SAMPLE_RATE*2):
                raise ValueError("Unexpected extra narration beyond 15 minutes")
        err=process.stderr.read()
        if process.wait(timeout=25):
            raise ValueError("Video audio decode failed: "+err.decode("utf-8","replace")[-400:])
    finally:
        if process.poll() is None:
            process.kill();process.wait()
        process.stdout.close()
        process.stderr.close()
    return count//2


def _correlate_window(reference,actual,limit):
    width=min(len(reference),len(actual))
    if width<SAMPLE_RATE*.65:
        raise ValueError("Audio comparison window too short")
    x=np.asarray(actual[:width],dtype=np.float64)
    y=np.asarray(reference[:width],dtype=np.float64)
    x-=np.mean(x);y-=np.mean(y)
    if np.sqrt(np.mean(y*y))<.0018:
        return None
    n=1<<(2*width-1).bit_length()
    cross=np.fft.irfft(np.fft.rfft(x,n)*np.conj(np.fft.rfft(y,n)),n)
    lags=np.arange(-limit,limit+1)
    lag=int(lags[np.argmax(cross[lags%n])])
    if lag>=0:
        a=x[lag:];b=y[:len(a)]
    else:
        b=y[-lag:];a=x[:len(b)]
    nrm=float(np.linalg.norm(a)*np.linalg.norm(b))
    correlation=float(np.dot(a,b)/nrm) if nrm else 0.
    return {"lagSamples":lag,"correlation":round(correlation,6)}


def _distributed_audio_checks(ffmpeg,video,wav,voice_duration):
    positions=[max(0.,(voice_duration-1.35)*i/11) for i in range(12)]
    tested=[]
    quiet=0
    for at in positions:
        window=min(1.35,voice_duration-at)
        if window<1.0:
            continue
        reference=_decode_window(ffmpeg,wav,at,window)
        actual=_decode_window(ffmpeg,video,at,window)
        match=_correlate_window(reference,actual,round(SAMPLE_RATE*MAX_AUDIO_LAG_SEC))
        if match is None:
            quiet+=1
            continue
        if abs(match["lagSamples"])>round(SAMPLE_RATE*.018):
            raise ValueError(f"Audio out of sync near {at:.2f}s: {match['lagSamples']} samples")
        if match["correlation"]<.96:
            raise ValueError(f"Narration content differs near {at:.2f}s: {match['correlation']}")
        tested.append({"fromSec":round(at,3),**match})
    if len(tested)<min(3,max(1,int(voice_duration//4))):
        raise ValueError("Not enough audible narration windows to verify voice integrity")
    return tested,quiet


def verify(ffmpeg,video,wav,size=(1920,1080),minimum_seconds=30):
    video=Path(video)
    if video.is_symlink() or not video.is_file() or not video.stat().st_size:
        raise ValueError("Missing actual rendered video")
    if size not in ((1920,1080),(1080,1920),(320,180)):
        raise ValueError("Unexpected unapproved canvas size")
    source_samples,voice_duration=duration_wav(wav)
    if voice_duration<minimum_seconds:
        raise ValueError("Video shorter than user's 30-second minimum")
    expected=math.ceil(voice_duration*FPS-1e-9)
    frames=_read_video_frames(ffmpeg,video,size,expected)
    audio_samples=_audio_length_samples(ffmpeg,video)
    if abs(audio_samples-source_samples)>AUDIO_TOLERANCE_SEC*SAMPLE_RATE:
        raise ValueError(f"Final audio duration differs from untouched narration by {(audio_samples-source_samples)/SAMPLE_RATE:.4f}s")
    checks,silent=_distributed_audio_checks(ffmpeg,video,wav,voice_duration)
    h=hashlib.sha256()
    with video.open("rb") as f:
        for piece in iter(lambda:f.read(2**20),b""):
            h.update(piece)
    return {
        "status":"FULL_VIDEO_TECHNICAL_INTEGRITY_VERIFIED_NOT_ARTISTIC_APPROVAL",
        "frameRate":FPS,**frames,
        "sourceAudioSeconds":round(voice_duration,6),
        "finalAudioSeconds":round(audio_samples/SAMPLE_RATE,6),
        "sourceAudioPreserved":True,"voiceWindowsVerified":len(checks),
        "quietWindowsNotUsedAsProof":silent,
        "voiceAgreement":checks,"sha256":h.hexdigest(),
        "sourcePhonemesCertified":False,"creativeApproval":False,
        "readyForPublicRelease":False,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg",type=Path,required=True)
    parser.add_argument("--video",type=Path,required=True)
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--portrait",action="store_true")
    parser.add_argument("--report",type=Path)
    a=parser.parse_args()
    report=verify(a.ffmpeg,a.video,a.source,
                  size=(1080,1920) if a.portrait else (1920,1080))
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.report.with_suffix(a.report.suffix+".partial")
        tmp.write_text(json.dumps(report,indent=2)+"\n")
        tmp.replace(a.report)
    print("ROVOR_COMPLETE_VIDEO_INTEGRITY=PASS")
    print("ROVOR_VERIFIED_FRAMES="+str(report["decodedFrames"]))
    print("ROVOR_VERIFIED_AUDIO_WINDOWS="+str(report["voiceWindowsVerified"]))
    print("CREATIVE_APPROVAL=NO")


if __name__=="__main__":
    main()
