#!/usr/bin/env python3
"""Independent full decoded-video timing and original-narration sync checks.
Audio offsets measured by direct sample-level lag. Artistic/readability approval never inferred.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess
import numpy as np
from quote_story_v7 import SOURCE,SHA,FPS,SOURCE_START,SOURCE_END

def run(cmd):return subprocess.check_output(cmd,stderr=subprocess.PIPE)
def probe(path):
 return json.loads(run(['ffprobe','-v','error','-show_entries','format=duration:stream=index,codec_type,width,height,avg_frame_rate,nb_frames,duration','-of','json',str(path)]))
def audio_window(src,start,dur=.7):
 return np.frombuffer(run(['ffmpeg','-v','error','-nostdin','-ss',f'{start:.5f}','-i',str(src),'-t',str(dur),'-vn','-ac','1','-ar','16000','-f','f32le','pipe:1']),dtype='<f4').astype(np.float64)
def corr_lag(a,b,shift=120):
 n=min(len(a),len(b)); l=max(100,n-2*shift-20); a=a[shift:shift+l];a=a-a.mean()
 norm=np.linalg.norm(a);best=(-1e9,0)
 for lag in range(-shift,shift+1):
  x=b[shift+lag:shift+lag+l];x=x-x.mean()
  c=float(np.dot(a,x)/(norm*np.linalg.norm(x)+1e-20))
  if c>best[0]:best=c,lag
 return {'correlation':round(best[0],7),'lag_samples':best[1],'source_rms':round(float(np.std(a)),7)}
def verify(movie,portrait,full=False):
 movie=Path(movie); assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
 dur=SOURCE_END if full else SOURCE_END-SOURCE_START
 offset=0 if full else SOURCE_START
 frames=round(dur*FPS);w,h=(1080,1920) if portrait else (1920,1080)
 info=probe(movie);v=next(s for s in info['streams'] if s['codec_type']=='video')
 a=next(s for s in info['streams'] if s['codec_type']=='audio')
 assert (v['width'],v['height'])==(w,h),v
 assert v['avg_frame_rate']=='60/1',v
 assert int(v['nb_frames'])==frames,(v['nb_frames'],frames)
 lines=run(['ffprobe','-v','error','-select_streams','v','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(movie)]).decode().splitlines()
 pts=np.array([float(s.split(',')[0]) for s in lines if s and s[0].isdigit()],float)
 assert len(pts)==frames,(len(pts),frames)
 err=float(np.abs(pts-np.arange(frames)/FPS).max());assert err<.0005,err
 times=([1,17,50,80,113.5,131.25,131.9,132.1,132.5,136,139.5,143.5]
        if full else [.65,1.2,3,4.7,5.8,7.1,9.3,11.1,12.1])
 checks=[]
 for t in times:
  a0=audio_window(SOURCE,t+offset);a1=audio_window(movie,t)
  r=corr_lag(a0,a1);checks.append({'movie_sec':t,'original_source_sec':t+offset,**r})
 # Frames/pts are hard requirements; note any lossy AAC correlation weaknesses explicitly.
 flagged=[c for c in checks if c['source_rms']>.025 and (c['correlation']<.99 or abs(c['lag_samples'])>1)]
 return {'status':'TECHNICAL_TIMELINE_VERIFIED_ART_NOT_APPROVED',
  'movie':str(movie),'sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),
  'portrait':portrait,'size':[w,h],'source_original_sha256':SHA,
  'covered_original_source':[offset,offset+dur],'fps':60,'decoded_frames':len(pts),
  'max_frame_pts_error_seconds':err,'source_word_alignment_certified':False,
  'artistic_approval':False,'voice_flags':flagged,'voice_checks':checks}
if __name__=='__main__':
 pa=argparse.ArgumentParser();pa.add_argument('movie',type=Path);pa.add_argument('--portrait',action='store_true');pa.add_argument('--full',action='store_true');pa.add_argument('--output',type=Path);arg=pa.parse_args()
 out=verify(arg.movie,arg.portrait,arg.full)
 if arg.output:arg.output.write_text(json.dumps(out,indent=2))
 print(json.dumps(out,indent=2))