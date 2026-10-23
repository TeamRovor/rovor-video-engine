#!/usr/bin/env python3
"""Reproducible, read-only video-version delta QA for local review clips.

Requires ffmpeg and ffprobe. Processes explicitly supplied local files, never
modifies originals, never uploads media, and never claims artistic approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _execute(argv: list[str], *, limit=140_000_000) -> bytes:
    try:
        p = subprocess.run(argv, check=True, capture_output=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"decoder failed: {type(exc).__name__}") from None
    if len(p.stdout) > limit:
        raise ValueError("decoded output over bounded limit")
    return p.stdout


def inspect(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise ValueError("video source missing or redirected")
    data = json.loads(_execute(["ffprobe", "-v", "error", "-show_streams",
                                "-show_format", "-of", "json", str(path)], limit=1_000_000))
    vs = next((s for s in data['streams'] if s['codec_type'] == 'video'), None)
    if not vs:
        raise ValueError("no video stream")
    return {"filename":path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "width":vs['width'], "height":vs['height'], "nominal_fps":vs['r_frame_rate'],
            "average_fps":vs['avg_frame_rate'],"frames":int(vs['nb_frames']),
            "duration_seconds":float(vs.get('duration', data['format']['duration']))}


def decode_frames(path: Path, *, width=256, height=144) -> list[bytes]:
    if not (16 <= width <= 640 and 16 <= height <= 360):
        raise ValueError("review dimensions outside safe limit")
    # Sampling is deterministic at full-second presentation timestamps.
    raw = _execute(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path),
        "-vf",f"fps=1,scale={width}:{height}:flags=area", "-an", "-sn", "-dn",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"])
    stride = width * height * 3
    if not raw or len(raw) % stride:
        raise ValueError("invalid raw decoded frames")
    return [raw[i:i+stride] for i in range(0,len(raw),stride)]


def frame_mae(a: bytes, b: bytes) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("mismatched decoded frame lengths")
    return sum(abs(x-y) for x,y in zip(a,b)) / len(a)


def compare(a: list[bytes], b: list[bytes], *, threshold=0.1) -> dict:
    if len(a) != len(b):
        raise ValueError("sample counts differ; review timeline before treating as unchanged")
    if not 0 < threshold < 255:
        raise ValueError("threshold must be positive and below 255")
    diffs = [round(frame_mae(x,y), 5) for x,y in zip(a,b)]
    changed = [i for i,d in enumerate(diffs) if d >= threshold]
    groups=[]
    for i in changed:
        if groups and i==groups[-1][-1]+1:
            groups[-1].append(i)
        else:
            groups.append([i])
    return {"samples_at_1fps":len(a), "threshold_mae_8bit":threshold,
            "near_identical_samples":len(a)-len(changed),
            "fraction_near_identical":round((len(a)-len(changed))/len(a),4),
            "changed_seconds":changed,
            "changed_intervals_inclusive":[[g[0],g[-1]] for g in groups],
            "max_pixel_mae":max(diffs) if diffs else None}


def decoded_audio_hash(path:Path) -> dict:
    pcm=_execute(["ffmpeg","-nostdin","-v","error","-i",str(path),
                  "-map","0:a:0","-ac","1","-ar","16000",
                  "-f","s16le","pipe:1"],limit=100_000_000)
    return {"pcm_sha256":hashlib.sha256(pcm).hexdigest(),"pcm_sample_count":len(pcm)//2}


def run(before:Path, after:Path, *, threshold=0.1, audio=True) -> dict:
    first,second=inspect(before),inspect(after)
    if first['width']!=second['width'] or first['height']!=second['height']:
        raise ValueError("different video dimensions; compare matched orientations")
    delta=compare(decode_frames(before), decode_frames(after), threshold=threshold)
    out={"status":"technical_comparison_only_not_artistic_approval",
         "before":first,"after":second,"frame_delta":delta}
    if audio:
        x,y=decoded_audio_hash(before),decoded_audio_hash(after)
        out['audio']={"first":x,"second":y,
                      "exact_decoded_pcm_match":x==y}
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',required=True,type=Path)
    p.add_argument('--after',required=True,type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--threshold',type=float,default=0.1)
    p.add_argument('--skip-audio',action='store_true')
    a=p.parse_args(argv)
    result=run(a.before,a.after,threshold=a.threshold,audio=not a.skip_audio)
    rendered=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if a.out:
        a.out.write_text(rendered,encoding='utf-8')
    else:
        print(rendered,end='')
    return 0

if __name__=='__main__':
    sys.exit(main())