"""Independently verify actual decoded frames/timing/audio against ORIGINAL MP3."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import numpy as np
from mechanic_story_v9 import ORIGINAL,SOURCE_SHA,FPS,START,END,START_FRAME,END_FRAME

def capture(cmd):return subprocess.check_output(cmd,stderr=subprocess.PIPE)
def audio_samples(p,start,length=.6):
 return np.frombuffer(capture(['ffmpeg','-v','error','-nostdin','-ss',f'{start:.8f}','-i',str(p),'-t',str(length),'-ac','1','-ar','16000','-f','f32le','pipe:1']),dtype='<f4').astype(np.float64)
def match(x,y,offset_range=100):
 n=min(len(x),len(y));L=n-2*offset_range-10
 assert L>100
 x=x[offset_range:offset_range+L];x-=x.mean();nx=np.linalg.norm(x)
 best=(-2.,0)
 for lag in range(-offset_range,offset_range+1):
  yseg=y[offset_range+lag:offset_range+lag+L];yseg=yseg-yseg.mean()
  corr=float(np.dot(x,yseg)/(nx*np.linalg.norm(yseg)+1e-18))
  if corr>best[0]:best=(corr,lag)
 return {'correlation':round(best[0],6),'lag_samples':best[1],'rms':round(float(np.std(x)),6)}
def verify(path,portrait=False,full=False):
 assert ORIGINAL.is_file() and hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==SOURCE_SHA
 p=Path(path);n=END_FRAME if full else END_FRAME-START_FRAME
 offset=0 if full else START
 w,h=(1080,1920) if portrait else (1920,1080)
 meta=json.loads(capture(['ffprobe','-v','error','-show_entries','stream=codec_type,width,height,avg_frame_rate,nb_frames','-of','json',str(p)]))
 video=next(s for s in meta['streams'] if s['codec_type']=='video')
 audio=next(s for s in meta['streams'] if s['codec_type']=='audio')
 assert (video['width'],video['height'])==(w,h)
 assert video['avg_frame_rate']=='60/1'
 assert int(video['nb_frames'])==n
 rows=capture(['ffprobe','-v','error','-select_streams','v','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(p)]).decode().splitlines()
 pts=np.array([float(r.split(',')[0]) for r in rows if r and r[0].isdigit()]);assert len(pts)==n
 maxerr=float(np.max(np.abs(pts-np.arange(n)/FPS)));assert maxerr<.0004,maxerr
 # Compare pre- and post-seam for full film, and internal cuts for short insert.
 times=[1.,17.,50.,96.,114.,130.,132.,143.9,144.3,144.78,144.85,146.2,149.7,150.54,153.1,155.2] if full else [.15,.8,2.4,4.7,5.70,5.82,7.8,9.2,10.8]
 checks=[]
 for sec in times:
  if sec>n/FPS-.7:continue
  a=audio_samples(ORIGINAL,sec+offset);b=audio_samples(p,sec)
  checks.append({'output_second':sec,'source_second':sec+offset,**match(a,b)})
 failures=[c for c in checks if c['rms']>.025 and (c['correlation']<.99 or abs(c['lag_samples'])>1)]
 return {'status':'TECHNICALLY_VALID_DECODED_NOT_CREATIVE_APPROVAL','name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
  'resolution':[w,h],'fps':FPS,'decoded_frames':n,'source_frame_interval':[0,n] if full else [START_FRAME,END_FRAME],
  'max_pts_error_sec':maxerr,'source_original_sha256':SOURCE_SHA,'sample_comparisons':checks,'flagged_audio_windows':failures,
  'word_aligned':False,'art_approved':False,'publication_approved':False}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('video',type=Path);ap.add_argument('--portrait',action='store_true');ap.add_argument('--full',action='store_true');ap.add_argument('--out',type=Path);args=ap.parse_args()
 r=verify(args.video,args.portrait,args.full)
 if args.out:args.out.write_text(json.dumps(r,indent=2)+'\n')
 print(json.dumps({k:v for k,v in r.items() if k not in {'sample_comparisons','flagged_audio_windows'}},indent=2));print('flagged_audio_windows',len(r['flagged_audio_windows']))