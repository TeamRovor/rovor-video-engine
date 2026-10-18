#!/usr/bin/env python3
"""Export original narration [132,144.8) with frame-authored original SVG V7, no synthesized voice."""
import argparse,multiprocessing as mp,subprocess,time,hashlib,json
from pathlib import Path
from quote_story_v7 import render_frame,SOURCE,SHA,SOURCE_START,SOURCE_END,FPS
ROOT=Path(__file__).resolve().parent
pview=False
def init(p):
 global pview;pview=p
def frame(i):
 return render_frame(SOURCE_START+i/FPS,pview,native=True).tobytes()
def render(portrait):
 assert SOURCE.is_file() and hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
 w,h=(1080,1920) if portrait else (1920,1080)
 n=round((SOURCE_END-SOURCE_START)*FPS)
 label='Portrait' if portrait else 'Landscape'
 out=ROOT/f'V7_Source132to144p8_{label}_1080p60_WIP.mp4'
 assert not out.exists(),f'avoid overwriting prior review: {out}'
 command=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y',
  '-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(FPS),'-i','pipe:0',
  '-i',str(SOURCE),'-filter_complex',f'[1:a]atrim=start={SOURCE_START}:end={SOURCE_END},asetpts=PTS-STARTPTS[a]',
  '-map','0:v:0','-map','[a]','-frames:v',str(n),'-pix_fmt','yuv420p',
  '-c:v','libx264','-crf','21','-preset','veryfast','-threads','2','-c:a','aac','-b:a','192k',
  '-movflags','+faststart',str(out)]
 t0=time.time();proc=subprocess.Popen(command,stdin=subprocess.PIPE)
 try:
  with mp.Pool(processes=3,initializer=init,initargs=(portrait,)) as pool:
   for i,pixels in enumerate(pool.imap(frame,range(n),chunksize=2),1):
    proc.stdin.write(pixels)
    if i%120==0:print(label,'frame',i,'/',n,'elapsed',round(time.time()-t0,1),flush=True)
  proc.stdin.close();status=proc.wait(timeout=180)
  if status:raise RuntimeError('ffmpeg '+str(status))
 except BaseException:
  try:proc.stdin.close()
  except:pass
  proc.kill();proc.wait();out.unlink(missing_ok=True)
  raise
 stats=dict(label=label,source_start=SOURCE_START,source_end=SOURCE_END,
    original_audio_sha256=SHA,duration_seconds=SOURCE_END-SOURCE_START,frames=n,
    fps=FPS,resolution=[w,h],file=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
    elapsed_sec=round(time.time()-t0,2),creative_approval=False,words_aligned=False)
 (ROOT/f'V7_segment_{label}_render.json').write_text(json.dumps(stats,indent=2))
 print('FINISHED',json.dumps(stats),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--portrait',action='store_true');args=ap.parse_args();render(args.portrait)