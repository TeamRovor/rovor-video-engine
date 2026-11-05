"""Same-audio rooted-tongue baseline versus independent eased-jaw study."""
import argparse,json
from pathlib import Path
import cv2
from render_lingual_review import Review
from lingual_cartoon_head import LingualCartoonHead
from separated_cartoon_head import SeparatedCartoonHead

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--start',type=int,default=120);p.add_argument('--end',type=int,default=240);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[LingualCartoonHead(),SeparatedCartoonHead()],titles=['BEFORE: tongue drives wide jaw','STUDY: tongue / eased jaw separated'],heading='“little globe … your logo” · same recording and phone timing',start=a.start,end=a.end)
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-a.start:06}.jpg',quality=97)
