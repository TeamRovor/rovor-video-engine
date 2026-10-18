#!/usr/bin/env python3
"""Private review-only 60fps original audio segment renderer, no brand/artist approval."""
import argparse,hashlib,json,multiprocessing as mp,subprocess,time
from pathlib import Path
from mechanic_story_v9 import START,END,FPS,START_FRAME,END_FRAME,ORIGINAL,SOURCE_SHA,frame_at
ROOT=Path(__file__).resolve().parent
pview=False
def init(flag):
 global pview;pview=flag
def pix(i):
 return frame_at((START_FRAME+i)/FPS,pview).tobytes()
def run(portrait):
 assert ORIGINAL.is_file() and hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==SOURCE_SHA
 w,h=(1080,1920) if portrait else (1920,1080);n=END_FRAME-START_FRAME
 tag='Portrait' if portrait else 'Landscape'
 out=ROOT/f'V9B_Mechanic_{tag}_{START_FRAME}to{END_FRAME}_60fps_WIP.mp4'
 if out.exists(): raise ValueError('refuse overwrite '+str(out))
 command=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(FPS),'-i','pipe:0',
   '-i',str(ORIGINAL),'-filter_complex',f'[1:a]atrim=start={START}:end={END},asetpts=PTS-STARTPTS[a]',
   '-map','0:v','-map','[a]','-frames:v',str(n),'-c:v','libx264','-preset','veryfast','-crf','21',
   '-pix_fmt','yuv420p','-threads','1','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
 t0=time.time();proc=subprocess.Popen(command,stdin=subprocess.PIPE)
 try:
  with mp.Pool(2,initializer=init,initargs=(portrait,)) as pool:
   for i,rgb in enumerate(pool.imap(pix,range(n),chunksize=2),1):
    proc.stdin.write(rgb)
    if i%120==0:print(tag,'rendered',i,n,'elapsed',round(time.time()-t0,1),flush=True)
  proc.stdin.close();status=proc.wait(timeout=120)
  if status:raise RuntimeError('FFmpeg return '+str(status))
 except BaseException:
  try:proc.stdin.close()
  except Exception: pass
  proc.kill();proc.wait();out.unlink(missing_ok=True);raise
 stats={'source_start_frame':START_FRAME,'source_end_exclusive':END_FRAME,'source_audio_sha256':SOURCE_SHA,'source_audio_original':True,'frames_expected':n,'width':w,'height':h,'fps':FPS,'seconds':n/FPS,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'elapsed_seconds':round(time.time()-t0,1),'artist_approved':False,'word_aligned':False}
 (ROOT/f'V9_{tag}_render.json').write_text(json.dumps(stats,indent=2)+'\n')
 print(tag,'done',round(time.time()-t0,2),flush=True)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--portrait',action='store_true');flags=a.parse_args();run(flags.portrait)