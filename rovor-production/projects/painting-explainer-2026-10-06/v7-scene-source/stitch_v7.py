#!/usr/bin/env python3
"""V7 review 0–144.8s, immutable previous 0–132 V6 and new native 132–144.8 V7.
Single continuously encoded original source narration. No edits to any prior files.
"""
import hashlib,subprocess,json,time,argparse,os
from pathlib import Path
from quote_story_v7 import SOURCE,SHA,FPS,SOURCE_END
ROOT=Path(__file__).resolve().parent
OLDER=Path(os.environ.get('ROVOR_V6_DIR', str(ROOT.parent/'rovor_v6'))) 
def make(portrait=False):
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SHA
 label='Portrait' if portrait else 'Landscape'
 old=OLDER/f'First132s_{label}_1080p60_V6_VECTOR_ARTWORK_WIP.mp4'
 new=ROOT/f'V7_Source132to144p8_{label}_1080p60_WIP.mp4'
 target=ROOT/f'First144p8s_{label}_1080p60_V7_STORY_REVIEW_WIP.mp4'
 assert old.exists() and new.exists(),(old,new)
 assert not target.exists(),f'do not overwrite: {target}'
 total=round(SOURCE_END*FPS)
 graph=('''[0:v]trim=start=0:end=132,setpts=PTS-STARTPTS[before];'''
        '''[1:v]trim=start=0:end=12.8,setpts=PTS-STARTPTS[after];'''
        '''[before][after]concat=n=2:v=1:a=0[v];'''
        f'''[2:a]atrim=start=0:end={SOURCE_END},asetpts=PTS-STARTPTS[a]''')
 command=['ffmpeg','-hide_banner','-nostdin','-loglevel','error','-y',
   '-i',str(old),'-i',str(new),'-i',str(SOURCE),'-filter_complex',graph,
   '-map','[v]','-map','[a]','-frames:v',str(total),'-r','60',
   '-pix_fmt','yuv420p','-c:v','libx264','-preset','veryfast','-threads','2','-crf','22',
   '-c:a','aac','-b:a','224k','-movflags','+faststart',str(target)]
 t=time.time();subprocess.run(command,check=True)
 out=dict(label=label,original_sha256=SHA,source_seconds=[0,SOURCE_END],
          original_v6_unmodified=True,added_v7_source_seconds=[132,SOURCE_END],
          fps=FPS,expected_frames=total,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
          elapsed=round(time.time()-t,1),file=str(target),artistic_approval=False)
 (ROOT/f'V7_full_{label}_stitch.json').write_text(json.dumps(out,indent=2))
 print('FINISHED',json.dumps(out),flush=True)
if __name__=='__main__':
 pa=argparse.ArgumentParser();pa.add_argument('--portrait',action='store_true');args=pa.parse_args();make(args.portrait)