"""Rebuild an exact-frame video segment with one continuous original narration.

Frame-accurate cross-format replacement for any 60fps episode. Video-only cuts
are stitched at frame boundaries; the untouched source MP3 supplies ONE audio
track. This preflight does not establish creative or phoneme approval.
"""
import argparse,hashlib,json,subprocess,os,shutil
from pathlib import Path
FPS=60

def sha256(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for part in iter(lambda:f.read(1<<20),b''):h.update(part)
 return h.hexdigest()
def metadata(p):
 raw=subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)])
 streams=json.loads(raw)['streams']; v=next(s for s in streams if s['codec_type']=='video')
 return dict(width=v['width'],height=v['height'],fps=v['avg_frame_rate'],frames=int(v.get('nb_frames') or 0))
def preflight(existing,insert,voice,view,start_frame,end_frame,expected_sha):
 a=metadata(existing);b=metadata(insert)
 assert view in ('landscape','portrait')
 dims=(1920,1080) if view=='landscape' else (1080,1920)
 if (a['width'],a['height'])!=dims or (b['width'],b['height'])!=dims:raise ValueError('Dimension mismatch')
 if a['fps']!='60/1' or b['fps']!='60/1':raise ValueError('FPS mismatch')
 if not 0<=start_frame<end_frame<a['frames']:raise ValueError('Out-of-range cut')
 if b['frames']!=end_frame-start_frame:raise ValueError('Insert covers wrong number of actual frames')
 if sha256(voice)!=expected_sha:raise ValueError('Wrong original narration fingerprint')
 return a,b

def splice(existing,insert,voice,out,view,start_frame,end_frame,expected_sha):
 a,b=preflight(existing,insert,voice,view,start_frame,end_frame,expected_sha)
 if out.exists():raise FileExistsError('Refuse to overwrite previously verified review')
 f=f'[0:v]trim=start_frame=0:end_frame={start_frame},setpts=PTS-STARTPTS[p];'
 f+=f'[1:v]trim=start_frame=0:end_frame={end_frame-start_frame},setpts=PTS-STARTPTS[i];'
 f+=f'[0:v]trim=start_frame={end_frame}:end_frame={a["frames"]},setpts=PTS-STARTPTS[q];'
 f+='[p][i][q]concat=n=3:v=1:a=0[v];'
 f+=f'[2:a]atrim=start=0:end={a["frames"]/FPS:.9f},asetpts=PTS-STARTPTS[a]'
 args=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y',
       '-i',str(existing),'-i',str(insert),'-i',str(voice),'-filter_complex',f,
       '-map','[v]','-map','[a]','-frames:v',str(a['frames']),
       '-c:v','libx264','-preset','ultrafast','-crf','21','-threads','4',
       '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(out)]
 try:subprocess.run(args,check=True)
 except BaseException:
  out.unlink(missing_ok=True);raise
 return dict(originalSha256=sha256(existing),insertSha256=sha256(insert),voiceSourceSha256=expected_sha,outputSha256=sha256(out),orientation=view,firstFrameReplaced=start_frame,afterLastFrameReplaced=end_frame,expectedFrames=a['frames'],expectedDuration=a['frames']/FPS,publicationApproved=False)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--existing',type=Path,required=True);p.add_argument('--insert',type=Path,required=True);p.add_argument('--voice',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--view',choices=['landscape','portrait'],required=True);p.add_argument('--first',type=int,required=True);p.add_argument('--last',type=int,required=True);p.add_argument('--sha',required=True);p.add_argument('--manifest',type=Path,required=True);a=p.parse_args()
 o=splice(a.existing,a.insert,a.voice,a.out,a.view,a.first,a.last,a.sha);a.manifest.write_text(json.dumps(o,indent=2)+'\n');print(json.dumps(o,indent=2))