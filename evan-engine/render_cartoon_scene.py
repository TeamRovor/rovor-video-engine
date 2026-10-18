"""Narrated favicon scene through its real pause; no automatic approval/deploy."""
import argparse,json
from pathlib import Path
import cv2
from PIL import ImageDraw
from cartoon_scene import CartoonSceneBody,CartoonMaterialSceneBody
from render_cartoon_gesture_study import frame as base_frame
from render_cartoon_head_study import font

FPS=48;FRAME_COUNT=489

def frame(body,plan,t):
    im=base_frame(body,plan,t,review_labels=False);d=ImageDraw.Draw(im)
    favicon=next(w for w in plan['words'] if w['word']=='favicon')
    if t>=favicon['start']:
        d.ellipse((783,360,822,399),outline='#ba684b',width=3)
        d.text((685,603),'That globe can mean a missing favicon.',font=font(22),fill='#48636d')
    else:d.text((685,603),'A small detail that represents your brand.',font=font(22),fill='#48636d')
    return im
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--material',action='store_true');p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=FRAME_COUNT);a=p.parse_args()
    plan=json.loads(a.plan.read_text());body=CartoonMaterialSceneBody() if a.material else CartoonSceneBody();a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(body,plan,i/FPS).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=a.end,fps=FPS)))
