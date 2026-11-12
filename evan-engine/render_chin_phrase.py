"""Native head comparison of independent chin anchors across a spoken phrase."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
from independent_chin_cartoon_head import IndependentChinCartoonHead,chin_weights,CHIN_ANCHORS
from duration_cartoon_head import duration_jaw_weights
from render_cartoon_head_study import font
from cartoon_head import TRIANGLES
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=648);p.add_argument('--end',type=int,default=792);a=p.parse_args();plan=json.loads(a.plan.read_text());old=DrawnDentalCartoonHead();new=IndependentChinCartoonHead();a.frames.mkdir(parents=True,exist_ok=True);rows=[];ids=np.asarray(TRIANGLES)
 code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();hashes={n:sha(code/n) for n in ['independent_chin_cartoon_head.py','drawn_dental_cartoon_head.py','duration_cartoon_head.py','render_chin_phrase.py']};parent=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 for i in range(a.start,a.end):
  t=i/48;x=old.at(t,plan);y=new.at(t,plan);jaw=duration_jaw_weights(t,plan);slow=chin_weights(t,plan);oldtarget=old.target_points(jaw);newtarget=new.target_points(slow);skin=old.skin_target(jaw,oldtarget.copy());skin[CHIN_ANCHORS]=newtarget[CHIN_ANCHORS];tri=skin[ids];v1=tri[:,1]-tri[:,0];v2=tri[:,2]-tri[:,0]
  # Integrated mouth-region pixels include the face under antialias edges.
  d=np.any(np.asarray(x)!=np.asarray(y),axis=2);oral_changes=int(d[305:375,180:300].sum())
  im=Image.new('RGB',(1280,720),'#f3eee2');draw=ImageDraw.Draw(im);draw.text((35,20),'Chin follow-through / original voice and mouth timing',font=font(27),fill='#253c49');draw.text((35,65),'Current chin follows oral contacts',font=font(20),fill='#48636d');draw.text((680,65),'Independent eased chin anchors — STUDY',font=font(20),fill='#48636d');im.paste(x,(55,95),x);im.paste(y,(700,95),y)
  words=[w['word'] for w in plan['words'] if w['start']<=t<w['end']];draw.text((35,625),f'Original recording {t:.4f}s | '+(' '.join(words) or '(pause)'),font=font(22),fill='#48636d');draw.text((35,670),'Same source art / no phoneme retiming / lips remain fast',font=font(19),fill='#48636d');im.save(a.frames/f'{i:06}.png')
  rows.append(dict(frame=i,time=t,oldChinY=float(oldtarget[46,1]),newChinY=float(newtarget[46,1]),changedHeadPixels=int(d.sum()),mouthRegionChangedPixels=oral_changes,minimumSkinTriangleArea2=float(np.min(v1[:,0]*v2[:,1]-v1[:,1]*v2[:,0]))))
  if len(rows)%24==0:print(f'{a.start}: {len(rows)}/{a.end-a.start}',flush=True)
 report=dict(start=a.start,end=a.end,completed=len(rows),fps=48,parentCommit=parent,planSha256=sha(a.plan),codeSha256=hashes,artworkChanged=False,phonemeTimingChanged=False,animationReady=False,dentalMorphFallbacks=new.dental_morph_fallbacks,fvFallbacks=new.fv_correspondence_fallbacks,dentalFallbacks=new.dental_fallbacks,roundedFallbacks=new.contour_fallbacks,rows=rows,limits='Three existing face-skin mesh anchors only, not an independently drawn jaw/mandible. Mouth-region count includes underlying face at lip antialias edges; no perceptual/listening acceptance.')
 a.audit.write_text(json.dumps(report,indent=2)+'\n')
