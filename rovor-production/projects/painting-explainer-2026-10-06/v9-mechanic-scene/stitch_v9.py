#!/usr/bin/env python3
"""Join unchanged V7 [0,8688) with new V9 [8688,9377), original one-piece narration.
No publication/creative approval, no overwrite of earlier review movies.
"""
import argparse,subprocess,hashlib,json,time
from pathlib import Path
from mechanic_story_v9 import ORIGINAL,SOURCE_SHA,START,END,FPS,START_FRAME,END_FRAME
ROOT=Path(__file__).resolve().parent
OLDER=ROOT.parent/'rovor_v7'
def stitch(portrait=False):
 assert ORIGINAL.is_file() and hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()==SOURCE_SHA
 tag='Portrait' if portrait else 'Landscape'
 old=OLDER/f'First144p8s_{tag}_1080p60_V7_STORY_REVIEW_WIP.mp4'
 new=ROOT/f'V9B_Mechanic_{tag}_{START_FRAME}to{END_FRAME}_60fps_WIP.mp4'
 target=ROOT/f'First156p283s_{tag}_1080p60_V9_STORY_WIP.mp4'
 assert old.is_file() and new.is_file(),(old,new)
 assert not target.exists(),'Refusing to overwrite '+str(target)
 graph=(f'[0:v]trim=start_frame=0:end_frame={START_FRAME},setpts=PTS-STARTPTS[v0];'
        f'[1:v]trim=start_frame=0:end_frame={END_FRAME-START_FRAME},setpts=PTS-STARTPTS[v1];'
        '[v0][v1]concat=n=2:v=1:a=0[combined];'
        f'[2:a]atrim=start=0:end={END},asetpts=PTS-STARTPTS[a]')
 command=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-i',str(old),'-i',str(new),'-i',str(ORIGINAL),
  '-filter_complex',graph,'-map','[combined]','-map','[a]','-frames:v',str(END_FRAME),'-r','60',
  '-c:v','libx264','-crf','22','-preset','veryfast','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','224k',
  '-movflags','+faststart',str(target)]
 t0=time.time();subprocess.run(command,check=True)
 result={'orientation':tag,'v7_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'v9_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),
  'original_audio_sha256':SOURCE_SHA,'source_end_frame':END_FRAME,'expected_decoded_frames':END_FRAME,
  'source_original_audio_unmodified':True,'new_interval_frame':[START_FRAME,END_FRAME],
  'file_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
  'seconds_elapsed':round(time.time()-t0,2),'artistic_approval':False,'word_alignment_certified':False}
 (ROOT/f'V9_{tag}_stitch.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--portrait',action='store_true');v=ap.parse_args();stitch(v.portrait)