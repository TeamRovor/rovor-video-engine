"""Decode and inspect every 60fps frame time, dimensions, audio samples for V12.

Provides engineering evidence only; explicit flags for artistic/word timing.
"""
from pathlib import Path
import json,hashlib,subprocess,math,sys,argparse
import numpy as np
from estimate_desk_v12 import SOURCE_SHA, START_FRAME, END_FRAME, FRAME_COUNT
BASE=Path(__file__).parent

def run(args):return subprocess.check_output(args,stderr=subprocess.DEVNULL)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def aud(p,at,duration=.7):
 args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-ss',str(at),'-i',str(p),'-t',str(duration),'-vn','-ac','1','-ar','16000','-f','f32le','pipe:1']
 return np.frombuffer(run(args),dtype='<f4')
def corr(x,y):
 n=min(len(x),len(y));a=x[:n]-x[:n].mean();b=y[:n]-y[:n].mean()
 return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-10))
def verify(movie,view,full=False):
 assert sha(BASE/'original.mp3')==SOURCE_SHA
 data=json.loads(run(['ffprobe','-v','error','-show_streams','-of','json',str(movie)]))
 v=next(x for x in data['streams'] if x['codec_type']=='video')
 resolution=(1920,1080) if view=='landscape' else (1080,1920)
 assert (v['width'],v['height'])==resolution
 assert v['r_frame_rate']=='60/1'
 times=[float(x.split(',')[0]) for x in run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(movie)]).decode().splitlines() if x.strip()]
 count=9377 if full else FRAME_COUNT
 assert len(times)==count,(len(times),count)
 maxerror=max(abs(t-i/60) for i,t in enumerate(times))
 assert maxerror<.00035,maxerror
 windows=[(1.5,1.5),(28.9,28.9),(29.35,29.35),(30.6,30.6),(33.9,33.9),(35.4,35.4),(37.1,37.1),(40.9,40.9),(41.65,41.65),(92.9,92.9),(110.8,110.8),(155.0,155.0)] if full else [(0.45,29.2+0.45),(2.5,29.2+2.5),(6.8,29.2+6.8),(9.7,29.2+9.7),(11.45,29.2+11.45)]
 checks=[]
 for pos,orig in windows:
  c=corr(aud(movie,pos),aud(BASE/'original.mp3',orig))
  checks.append(dict(sourceSecond=orig,clipSecond=pos,correlation=c,needsManualListening=c<.995))
 return dict(view=view,durationSeconds=count/60,resolution=resolution,fps=60,decodedFrames=count,framePtsMaxError=maxerror,videoSha256=sha(movie),sourceAudioSha256=SOURCE_SHA,voiceComparisons=checks,minimumCorrelation=min(x['correlation'] for x in checks),originalSourceInterval=[0,count/60] if full else [START_FRAME/60,END_FRAME/60],originalSpeechModified=False,wordAlignmentCertified=False,visualApproval=False,publicationApproved=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--movie',required=True);p.add_argument('--view',choices=['landscape','portrait'],required=True);p.add_argument('--full',action='store_true');p.add_argument('--out',required=True);a=p.parse_args();res=verify(a.movie,a.view,a.full);Path(a.out).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:res[k] for k in ['view','decodedFrames','framePtsMaxError','minimumCorrelation']}))