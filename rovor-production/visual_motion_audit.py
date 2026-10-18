#!/usr/bin/env python3
"""Read-only whole-film motion audit from *decoded pixel frames*.

Flags nearly unchanged stretches and major cuts; does not assign creative
approval, diagnose performance, or confuse quiet acting holds with errors.
FFmpeg decodes small grayscale frames at a uniform rate; no video is modified.
"""
from __future__ import annotations
import argparse, json, subprocess, math, hashlib
from pathlib import Path
import numpy as np

W,H=240,135
SAMPLE_FPS=2
FRAME_BYTES=W*H

def ffprobe(path):
 cmd=['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_frames,duration','-show_entries','format=duration','-of','json',str(path)]
 data=json.loads(subprocess.check_output(cmd,text=True));s=data['streams'][0]
 return dict(dimensions=[int(s['width']),int(s['height'])],duration=float(data['format']['duration']),fps=s['r_frame_rate'],reported_frames=s.get('nb_frames'))

def decoded_features(path,portrait=False,sample_fps=SAMPLE_FPS):
 """Normalize landscape/portrait to equal 32,400px sample areas for fair review."""
 if not Path(path).is_file():raise FileNotFoundError(path)
 width,height=(H,W) if portrait else (W,H)
 probe=ffprobe(path)
 expected=(1080,1920) if portrait else (1920,1080)
 if probe['dimensions'] != list(expected):raise ValueError('format mismatch with requested orientation')
 if probe['fps']!='60/1':raise ValueError('not exact 60fps')
 cmd=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-i',str(path),
      '-vf',f'fps={sample_fps},scale={width}:{height}:flags=area,format=gray',
      '-f','rawvideo','-pix_fmt','gray','-']
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 values=[];prev=None;i=0;sz=width*height
 try:
  while True:
   chunk=proc.stdout.read(sz)
   if not chunk:break
   if len(chunk)!=sz:raise ValueError('partial decoded frame')
   arr=np.frombuffer(chunk,dtype=np.uint8).astype(np.int16)
   if prev is not None:
    diff=np.abs(arr-prev)
    vals=dict(time=i/sample_fps,mae=round(float(np.mean(diff)),3),changed_fraction=round(float(np.mean(diff>10)),5),changed_pixels=int(np.count_nonzero(diff>10)))
    values.append(vals)
   prev=arr;i+=1
 finally:
  proc.stdout.close()
  status=proc.wait()
 if status:raise RuntimeError(f'ffmpeg decode exited {status}')
 return probe,values,i

def _window_summary(pairs,start,end):
 rows=[p for p in pairs if start<=p['time']<end]
 if not rows:return None
 changed=np.array([x['changed_fraction'] for x in rows]);maes=np.array([x['mae'] for x in rows]);
 return dict(start_sec=round(start,3),end_sec=round(end,3),pairs=len(rows),
             median_changed_fraction=round(float(np.median(changed)),5),
             p75_changed_fraction=round(float(np.percentile(changed,75)),5),
             median_mae=round(float(np.median(maes)),3),
             nearly_still_sample_fraction=round(float(np.mean(changed<.012)),3),
             sharp_transition_count=int(np.sum(changed>.20)))

def report(path,portrait=False,window=5.0):
 if window<=0 or not math.isfinite(window):raise ValueError('bad window')
 probe,pairs,n=decoded_features(path,portrait)
 duration=probe['duration'];chunks=[]
 for x in range(math.ceil(duration/window)):
  chunk=_window_summary(pairs,x*window,min((x+1)*window,duration))
  if chunk:chunks.append(chunk)
 flagged=[x for x in chunks if x['median_changed_fraction'] <.008 and x['nearly_still_sample_fraction']>=.6]
 return dict(status='TECHNICAL_MOTION_SCREEN_ONLY_NOT_CREATIVE_APPROVAL',path=Path(path).name,
             video_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),orientation='portrait' if portrait else 'landscape',
             source_duration_sec=round(duration,3),frames_decoded_for_motion=n,pairs_compared=len(pairs),sample_rate_fps=SAMPLE_FPS,
             pixel_sample_area=FRAME_BYTES,method='uniform ffmpeg grayscale decodes; adjacent half-second pairs, no audio inference',
             windows=chunks,low_motion_windows=flagged,
             caution='Low motion may be intentional acting holds; high motion can be cheap graphic slides. Artistic review essential.',
             studio_art_approved=False)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('video',type=Path);p.add_argument('--portrait',action='store_true');p.add_argument('--out',type=Path)
 args=p.parse_args();r=report(args.video,args.portrait)
 if args.out:
  args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k not in ['windows']},indent=2))
if __name__=='__main__': main()