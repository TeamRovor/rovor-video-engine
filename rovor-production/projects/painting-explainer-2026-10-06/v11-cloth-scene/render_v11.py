"""Render independent landscape and portrait native 1080p60 MP4 action excerpts.
Neither this renderer nor its tests asserts final creative approval.
"""
from __future__ import annotations
import hashlib,subprocess,sys,time,io,argparse
from pathlib import Path
import cairosvg
from PIL import Image
from fabric_protection_v11 import svg_frame,SOURCE_SHA,FPS
BASE=Path(__file__).parent
SOURCE=BASE/'original_evan.mp3'

def render(view:str,out:Path):
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Unapproved source audio')
    if view not in ('landscape','portrait'):raise ValueError('Unknown orientation')
    dims=(1920,1080) if view=='landscape' else (1080,1920)
    cmd=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
         '-f','rawvideo','-pix_fmt','rgb24','-s',f'{dims[0]}x{dims[1]}','-r','60','-i','pipe:0',
         '-i',str(SOURCE),'-filter_complex','[1:a]atrim=start=108:end=114,asetpts=PTS-STARTPTS[a]',
         '-map','0:v:0','-map','[a]','-frames:v','360','-c:v','libx264','-preset','ultrafast','-crf','21',
         '-threads','3','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    start=time.monotonic()
    try:
        for i in range(360):
            svg=svg_frame(i/60,view)
            png=cairosvg.svg2png(bytestring=svg.encode(),output_width=dims[0],output_height=dims[1])
            image=Image.open(io.BytesIO(png)).convert('RGB')
            proc.stdin.write(image.tobytes())
            if i%60==59:print(f'{view}: {i+1}/360 frames ({time.monotonic()-start:.1f}s)',flush=True)
        proc.stdin.close();ret=proc.wait(timeout=40)
        if ret:raise RuntimeError(f'FFmpeg returned {ret}')
    except BaseException:
        try:proc.stdin.close()
        except Exception:pass
        proc.kill();proc.wait();out.unlink(missing_ok=True)
        raise
    print(f'FINISHED {view}: {out} {out.stat().st_size} bytes',flush=True)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--view',choices=('landscape','portrait'),required=True);a.add_argument('--out',type=Path,required=True)
    args=a.parse_args();render(args.view,args.out)