"""Same-audio bounded-sample comparison; this is renderer QA, not new art."""
import argparse,json
from pathlib import Path
import cv2
from render_lingual_review import Review
from anchored_cartoon_head import AnchoredCartoonHead
from bounded_cartoon_head import BoundedCartoonHead

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--start',type=int,default=393);p.add_argument('--end',type=int,default=489);a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[AnchoredCartoonHead(),BoundedCartoonHead()],titles=['BEFORE: cubic sample overshoot','QA: valid samples before blending'],heading='“missing a favicon” · same art / audio · subtle edge correction',start=a.start,end=a.end)
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):review.frame(i).save(a.frames/f'{i-a.start:06}.jpg',quality=97)
