"""Same-recording native-head broad cavity artwork review."""
import argparse,json
from pathlib import Path
import cv2
from render_lingual_review import Review
from light_lip_cartoon_head import LightLipCartoonHead
from broad_cavity_cartoon_head import BroadCavityCartoonHead

if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--start',type=int,default=120);p.add_argument('--end',type=int,default=240);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[LightLipCartoonHead(),BroadCavityCartoonHead()],titles=['BEFORE: baked broad-mouth floor','STUDY: separate broad cavity / rim'],heading='“little globe … your logo” · identical audio and phone timing',start=a.start,end=a.end)
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):
        review.frame(i).save(a.frames/f'{i-a.start:06}.jpg',quality=97)
        if (i-a.start)%24==0:print(f'frames {i-a.start+1}/{a.end-a.start}',flush=True)
    print(json.dumps({'contourFallbacks':review.heads[1].contour_fallbacks}))
