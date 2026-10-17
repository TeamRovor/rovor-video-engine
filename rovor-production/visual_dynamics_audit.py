"""Read-only decoded-video diagnostic for static talking-head composition.

This is an engineering heuristic, not artistic review. Frame changes alone
cannot certify coherent storytelling, humor, acting, or perfect lip sync.
"""
import argparse,json,math
from pathlib import Path
import cv2,numpy as np

def summarize(frames,times,duration):
    if len(frames)!=len(times) or len(frames)<2:
        raise ValueError('Two aligned decoded frame samples required')
    changes=[]
    for i in range(1,len(frames)):
        a,b=frames[i-1],frames[i]
        if a.ndim!=3 or a.shape!=b.shape:raise ValueError('Inconsistent frame geometry')
        w=a.shape[1]
        # Evan stands mostly on left: measure changes away from his mouth/hand.
        x=a[:,int(w*.50):].astype(np.int16)
        y=b[:,int(w*.50):].astype(np.int16)
        d=np.abs(x-y)
        changes.append(dict(timeSec=round(times[i],3),
                            meanAbsoluteChange=round(float(d.mean()),4),
                            fractionChangedOver32=round(float(np.mean(np.max(d,axis=2)>32)),5)))
    substantial=[x for x in changes if x['meanAbsoluteChange']>=9 and x['fractionChangedOver32']>=.12]
    expected=max(1,math.ceil(duration/15))
    problems=[]
    if len(substantial)<expected:
        problems.append(f'Insufficient substantial right-side visual changes ({len(substantial)} detected; {expected} diagnostic minimum)')
    keyframes=[0.]+[x['timeSec'] for x in substantial]+[duration]
    max_idle=max(b-a for a,b in zip(keyframes,keyframes[1:]))
    if duration>=12 and max_idle>12:
        problems.append(f'No substantial right-side change for {max_idle:.1f} seconds')
    return dict(status='VISUAL_REVIEW_REQUIRED' if problems else 'STRUCTURAL_MOTION_PRESENT',
                publicationApproved=False,isEntertainmentCertified=False,
                substantialChanges=len(substantial),sampleCount=len(frames),
                maxIdleSeconds=round(max_idle,2),problems=problems,
                note='Motion structure cannot certify original art, story, timing, acting or entertaining quality.')

def audit_video(path,interval=1.0):
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened():raise ValueError('Cannot decode video')
    try:
        fps=cap.get(cv2.CAP_PROP_FPS);count=cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not fps or fps<=0 or not count or count<2:raise ValueError('Invalid FPS or frame count')
        duration=count/fps
        frames=[];times=[]
        for t in np.arange(0,duration,interval):
            cap.set(cv2.CAP_PROP_POS_MSEC,float(t)*1000)
            ok,img=cap.read()
            if not ok:raise ValueError(f'Decode failed at {t:.2f} seconds')
            frames.append(cv2.resize(img,(320,180),interpolation=cv2.INTER_AREA))
            times.append(float(t))
        return dict(video=Path(path).name,durationSec=round(duration,5),
                    samplingIntervalSec=interval,**summarize(frames,times,duration))
    finally:cap.release()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args()
    result=audit_video(a.video)
    if a.report:
        a.report.parent.mkdir(parents=True,exist_ok=True)
        a.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    # Return success for diagnostic reporting even when video requires review.

if __name__=='__main__':main()
