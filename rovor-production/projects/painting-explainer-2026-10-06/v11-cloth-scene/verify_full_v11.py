"""Check every video timestamp for V11 full review and source-voice windows.
Technical checks never approve acting, phoneme boundaries or publishing.
"""
from pathlib import Path
import subprocess,hashlib,json,math
import numpy as np
SOURCE=Path(__file__).parent/'original_evan.mp3'
SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'

def run(*argv):return subprocess.check_output(argv,stderr=subprocess.DEVNULL)
def hash_file(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def meta(p):
 d=json.loads(run('ffprobe','-v','error','-show_streams','-of','json',str(p)))
 return d['streams']
def audio(p,length):
 return np.frombuffer(run('ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(p),'-t',str(length),'-vn','-ar','16000','-ac','1','-f','f32le','pipe:1'),dtype='<f4').copy()
def verify(p,view):
 assert hash_file(SOURCE)==SHA
 video=next(s for s in meta(p) if s['codec_type']=='video')
 assert video['avg_frame_rate']=='60/1'
 expected=(1920,1080) if view=='landscape' else (1080,1920)
 assert (video['width'],video['height'])==expected
 raw=run('ffprobe','-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp_time','-of','csv=p=0',str(p))
 times=[float(line.split(',')[0]) for line in raw.decode().splitlines() if line.strip()]
 assert len(times)==9377,(len(times),view)
 deviation=max(abs(t-i/60) for i,t in enumerate(times))
 assert deviation<.0004,(view,deviation)
 a=audio(p,9377/60); b=audio(SOURCE,9377/60)
 checks=[]
 for t in (1.2,27,59.8,90.8,106.5,107.8,108.35,110.75,113.5,114.8,135.8,150.5,155.15):
  lo=round(t*16000);hi=lo+round(.6*16000)
  v=a[lo:hi].copy();s=b[lo:hi].copy();n=min(len(v),len(s));v=v[:n]-v[:n].mean();s=s[:n]-s[:n].mean()
  correlation=float(np.dot(v,s)/(np.linalg.norm(v)*np.linalg.norm(s)+1e-9))
  checks.append(dict(sourceSecond=t,correlation=correlation))
 return dict(sourceSha256=SHA,sha256=hash_file(p),view=view,resolution=list(expected),fps=60,decodedFrames=len(times),lastDecodedTimestamp=times[-1],maxPtsErrorSec=deviation,originalNarrationReEncodedAAC=True,originalAudioSeconds=len(b)/16000,decodedAudioSeconds=len(a)/16000,sourceChecks=checks,minimumSourceCorrelation=min(x['correlation'] for x in checks),sourceInterval=[0,9377/60],phoneAlignmentCertified=False,studioArtApproved=False,publicationApproved=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--view',choices=['landscape','portrait'],required=True);p.add_argument('--file',required=True);p.add_argument('--out',required=True);x=p.parse_args();obj=verify(Path(x.file),x.view);Path(x.out).write_text(json.dumps(obj,indent=2)+'\n');print(json.dumps({key:obj[key] for key in ('view','decodedFrames','maxPtsErrorSec','minimumSourceCorrelation')},indent=2))