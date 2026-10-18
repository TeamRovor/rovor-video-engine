"""Same-audio comparison of mouth-driven skin versus anchored cheek paint."""
import argparse,json
from pathlib import Path
import cv2
from render_lingual_review import Review
from separated_cartoon_head import SeparatedCartoonHead
from anchored_cartoon_head import AnchoredCartoonHead

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--start',type=int,default=120);p.add_argument('--end',type=int,default=240);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[SeparatedCartoonHead(),AnchoredCartoonHead()],titles=['BEFORE: cheek pulled with mouth','STUDY: skin anchored / jaw moving'],heading='“little globe … your logo” · identical mouth controls and audio',start=a.start,end=a.end)
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-a.start:06}.jpg',quality=97)
