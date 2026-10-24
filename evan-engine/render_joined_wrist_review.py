"""Native-size wrist-join comparison with identical compact index/acting cues."""
import argparse,json
from pathlib import Path
import cv2
from render_compact_index_review import Review,START,END,FPS
from compact_cartoon_scene import CompactCartoonSceneBody,compact_controls
from joined_cartoon_wrist import JoinedWristSceneBody
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=START);p.add_argument('--end',type=int,default=END);a=p.parse_args()
    r=Review(json.loads(a.plan.read_text()),a.wav,bodies=[CompactCartoonSceneBody(),JoinedWristSceneBody()],titles=['BEFORE: separate wrist surfaces','AFTER: continuous wrist skin'],heading='Wrist join · same art sources, audio and acting',control_functions=[compact_controls,compact_controls]);a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):r.frame(i).save(a.frames/f'{i-START:06}.jpg',quality=97)
