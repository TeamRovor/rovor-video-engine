"""Strict technical QA for V11 original-voice source-locked insert.

Visual artistic quality is not certified by media integrity or motion scores.
"""
import argparse,hashlib,json,subprocess,math
from pathlib import Path
import numpy as np
SOURCE=Path(__file__).parent/'original_evan.mp3'
SOURCE_SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'

def call(*args):return subprocess.check_output(args,stderr=subprocess.DEVNULL)
def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def wav(path,start=None,duration=None):
 args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(path)]
 if start is not None:args+=['-ss',str(start)]
 if duration is not None:args+=['-t',str(duration)]
 args+=['-vn','-ac','1','-ar','16000','-f','f32le','pipe:1']
 return np.frombuffer(call(*args),dtype='<f4').copy()
def corr(a,b):
 size=min(len(a),len(b));a=a[:size];b=b[:size]
 if size==0:return 0.
 a=a-a.mean();b=b-b.mean();return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)+1e-8))
def verify(video,view):
 assert sha(SOURCE)==SOURCE_SHA
 meta=json.loads(call('ffprobe','-v','error','-show_streams','-of','json',str(video)))
 stream=next(x for x in meta['streams'] if x['codec_type']=='video')
 size=(1920,1080) if view=='landscape' else (1080,1920)
 assert (stream['width'],stream['height'])==size
 assert stream['avg_frame_rate']=='60/1'
 lines=call('ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(video)).decode().splitlines()
 pts=[float(v.split(',')[0]) for v in lines if v.strip()]
 assert len(pts)==360,(len(pts),view)
 deviation=max(abs(t-i/60) for i,t in enumerate(pts))
 assert deviation<.00035,deviation
 a=wav(video)
 b=wav(SOURCE,108,6)
 window_results=[]
 for sec in (0.6,2.6,4.9):
  i=round(sec*16000);length=round(.65*16000)
  rv=corr(a[i:i+length],b[i:i+length])
  window_results.append(dict(local_second=sec,correlation=rv))
 return dict(view=view,video=str(video),sha256=sha(video),sourceSha256=SOURCE_SHA,
   sourceIntervalSeconds=[108,114],decodedFrames=len(pts),fps=60,
   dimensions=list(size),maximumPtsErrorSec=deviation,audioSampleCount=len(a),
   sourceSamples=len(b),audioCorrelationWindows=window_results,
   noCertifiedPhonemes=True,creativeApproved=False,publicationApproved=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--view',required=True,choices=('portrait','landscape'));p.add_argument('--file',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=verify(a.file,a.view);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))