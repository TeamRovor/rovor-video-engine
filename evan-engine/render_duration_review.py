"""Same-recording native-head duration-sensitive jaw and contact teeth review."""
import argparse,json
from pathlib import Path
import cv2
from render_lingual_review import Review
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from duration_cartoon_head import DurationCartoonHead

if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('frames',type=Path)
    p.add_argument('--start',type=int,default=402);p.add_argument('--end',type=int,default=450);p.add_argument('--heading',default='“a favicon” · same recording and phoneme timing');a=p.parse_args()
    review=Review(json.loads(a.plan.read_text()),a.wav,heads=[CorrespondentFVCartoonHead(),DurationCartoonHead()],titles=['BEFORE: full short-vowel excursion','STUDY: duration-sensitive jaw / teeth'],heading=a.heading,start=a.start,end=a.end)
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):
        review.frame(i).save(a.frames/f'{i-a.start:06}.jpg',quality=97)
        if (i-a.start)%24==0:print(f'frames {i-a.start+1}/{a.end-a.start}',flush=True)
    print(json.dumps({'contourFallbacks':review.heads[1].contour_fallbacks,'fvCorrespondenceSamples':review.heads[1].fv_correspondence_samples,'fvCorrespondenceFallbacks':review.heads[1].fv_correspondence_fallbacks,'dentalSamples':review.heads[1].dental_samples,'dentalFallbacks':review.heads[1].dental_fallbacks}))
