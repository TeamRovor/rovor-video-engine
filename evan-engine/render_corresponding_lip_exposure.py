"""Voiced comparison of a source jaw-layer exposure, not accepted lip sync."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from corresponding_lip_exposure import CorrespondingLipExposure
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=714);p.add_argument('--end',type=int,default=774);a=p.parse_args();a.frames.mkdir(parents=True,exist_ok=True);plan=json.loads(a.plan.read_text());rig=CorrespondingLipExposure();rows=[]
 for i in range(a.start,a.end):
  old,new,row=rig.at(i/48,plan);x=np.array(old);y=np.array(new);np.testing.assert_array_equal(x[:288],y[:288]);row.update(sourceFrame=i,time=i/48)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((30,20),'DRAWN LIP EDGE / CAVITY / review-only test',font=font(27),fill='#253c49');d.text((30,65),'Previous overlap / pale lip gap',font=font(22),fill='#48636d');d.text((680,65),'Source-matched edge + painted cavity',font=font(22),fill='#48636d');im.paste(old,(55,95),old);im.paste(new,(700,95),new)
  d.text((30,625),f'Original voice / {i/48:.4f}s / lip and chin controls retained / native 512px heads',font=font(21),fill='#48636d');d.text((30,668),'Same artwork, voice and timing. Registration + cavity backing; not a finished facial rig.',font=font(20),fill='#48636d');im.save(a.frames/f'{i:06}.png');rows.append(row)
  if i in [714,738,741,742,746,773]:old.save(a.frames.parent/f'Old-{i}.png');new.save(a.frames.parent/f'Candidate-{i}.png')
  if len(rows)%10==0:print(f'{a.start}: {len(rows)}',flush=True)
 a.audit.write_text(json.dumps(dict(sourceStart=a.start,sourceEndExclusive=a.end,fps=48,rows=rows,upper288RowsExact=True,timingChanged=False,defaultProfileChanged=False,reviewToolLoaded=True,animationReady=False,carrier='existing upper face with authored front cheek ownership',source='unchanged jaw-overlap-v1/Jaw.png plus existing painted cavity',sourceCorrespondence=rig.correspondence,planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest()),indent=2)+'\n')
