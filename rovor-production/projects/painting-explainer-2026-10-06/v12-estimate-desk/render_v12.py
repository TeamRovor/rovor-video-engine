"""Native vector 1080p, source-locked dual-format experimental film insert."""
import os,sys,subprocess,time,io,argparse,hashlib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import cairosvg
from PIL import Image
from estimate_desk_v12 import frame,FRAME_COUNT,FPS,START_FRAME,END_FRAME,SOURCE_SHA
BASE=Path(__file__).parent
SOURCE=BASE/'original.mp3'

def raster_one(args):
    k,view,w,h=args
    return cairosvg.svg2png(bytestring=frame(k/FPS,view).encode('utf8'),output_width=w,output_height=h)

def render(view,out):
 if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:raise ValueError('Wrong source narration')
 w,h=(1920,1080) if view=='landscape' else (1080,1920)
 cmd=['ffmpeg','-nostdin','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r','60','-i','pipe:0','-i',str(SOURCE),'-filter_complex',f'[1:a]atrim=start={START_FRAME/FPS}:end={END_FRAME/FPS},asetpts=PTS-STARTPTS[a]','-map','0:v:0','-map','[a]','-frames:v',str(FRAME_COUNT),'-c:v','libx264','-preset','ultrafast','-crf','20','-threads','4','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 t=time.monotonic()
 try:
  with ProcessPoolExecutor(max_workers=6) as pool:
   jobs=((k,view,w,h) for k in range(FRAME_COUNT))
   for k,pic in enumerate(pool.map(raster_one,jobs,chunksize=3)):
    im=Image.open(io.BytesIO(pic)).convert('RGB')
    proc.stdin.write(im.tobytes())
    if (k+1)%120==0:print(f'{view} {k+1}/{FRAME_COUNT} in {time.monotonic()-t:.1f}s',flush=True)
  proc.stdin.close();code=proc.wait(timeout=120)
  if code:raise RuntimeError(f'ffmpeg exit {code}')
 except BaseException:
  try:proc.stdin.close()
  except Exception:pass
  proc.kill();proc.wait();out.unlink(missing_ok=True);raise
 print(f'DONE {view} {out.stat().st_size} bytes')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--view',choices=['landscape','portrait'],required=True);p.add_argument('--out',required=True);a=p.parse_args();render(a.view,Path(a.out))