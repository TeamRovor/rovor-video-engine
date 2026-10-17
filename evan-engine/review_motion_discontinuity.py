"""Decode a short review window and report frame-to-frame hand-motion discontinuities.

Pure visual evidence. It never edits the source artwork or phoneme timing, and
its scores are NOT a substitute for artistic/acting review. Use the same crop
and time window when comparing a proposed acting change with its baseline.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np


def measure_frames(frames, fps=60, start=0.0, threshold=20):
    """Analyze consecutive RGB frames with no optical smoothing or interpolation."""
    frames=np.asarray(frames)
    if frames.ndim!=4 or frames.shape[-1]!=3 or frames.dtype!=np.uint8:
        raise ValueError('Frames must be a uint8 array in N,H,W,3 RGB order')
    if len(frames)<2 or fps<=0:raise ValueError('At least two frames and positive fps required')
    delta=np.abs(np.diff(frames.astype(np.int16),axis=0))
    mae=delta.mean(axis=(1,2,3));fraction=(delta>threshold).mean(axis=(1,2,3))
    jumps=[{'timeSeconds':round(start+(i+1)/fps,6), 'meanAbsRgb':round(float(v),6),
            'fractionChannelsOverThreshold':round(float(fraction[i]),6)}
           for i,v in enumerate(mae)]
    return {'frames':len(frames),'fps':fps,'startSeconds':start,'pixelThreshold':threshold,
            'integratedMeanAbsRgb':round(float(mae.sum()),6),
            'peakMeanAbsRgb':round(float(mae.max()),6),
            'topJumps':sorted(jumps,key=lambda row:row['meanAbsRgb'],reverse=True)[:8]}


def decode_crop(video, ffmpeg, start, frames, fps, crop):
    x,y,w,h=crop
    if min(x,y)<0 or min(w,h)<=0:raise ValueError('Invalid region')
    cmd=[ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-ss',str(start),
         '-i',str(video),'-map','0:v:0','-an','-fps_mode','passthrough',
         '-vf',f'crop={w}:{h}:{x}:{y}', '-frames:v',str(frames),
         '-pix_fmt','rgb24','-f','rawvideo','-']
    result=subprocess.run(cmd,check=True,capture_output=True)
    expected=frames*h*w*3
    if len(result.stdout)!=expected:
        raise ValueError(f'Expected {expected} RGB bytes; decoded {len(result.stdout)}')
    return np.frombuffer(result.stdout,dtype=np.uint8).reshape(frames,h,w,3)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--start',type=float,default=2.15)
    p.add_argument('--frames',type=int,default=21)
    p.add_argument('--crop',default='550,430,550,560',help='x,y,width,height')
    p.add_argument('--fps',type=int,default=60)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    try: crop=tuple(map(int,a.crop.split(',')))
    except ValueError as e: p.error('Expected four integer crop coordinates')
    if len(crop)!=4:p.error('Expected x,y,width,height')
    raw=decode_crop(a.video,a.ffmpeg,a.start,a.frames,a.fps,crop)
    result={'video':a.video.name,'sha256':hashlib.sha256(a.video.read_bytes()).hexdigest(),
            'crop':list(crop), **measure_frames(raw,a.fps,a.start)}
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
