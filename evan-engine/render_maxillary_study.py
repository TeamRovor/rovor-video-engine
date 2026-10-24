"""Long contiguous narration A/B for continuous painted/FV construction."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from continuous_fv_cartoon_head import ContinuousFVCartoonHead
from maxillary_cartoon_head import MaxillaryCartoonHead
from cartoon_head import TRIANGLES,area
from speech_planner import planned_weights
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=489);p.add_argument('--end',type=int,default=693);a=p.parse_args()
 plan=json.loads(a.plan.read_text());old=ContinuousFVCartoonHead();new=MaxillaryCartoonHead();a.frames.mkdir(parents=True,exist_ok=True);rows=[];tri=[ids for ids in TRIANGLES if max(ids)<32]
 for i in range(a.start,a.end):
  t=i/48;x=old.at(t,plan);y=new.at(t,plan);xx=np.array(x);yy=np.array(y);w=planned_weights(t,plan,plan['fallbackCues']);fv=float(w[7])
  outside=np.ones((512,512),bool);outside[295:400,160:320]=False
  np.testing.assert_array_equal(xx[:290],yy[:290]);np.testing.assert_array_equal(xx[outside],yy[outside])
  alpha_delta=int(np.max(abs(xx[:,:,3].astype(int)-yy[:,:,3].astype(int))));assert alpha_delta<=1
  minimum=min(area(new.last_painted_target,ids) for ids in tri) if new.painted_rim is not None else None
  if minimum is not None:assert minimum>0
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
  d.text((35,20),'Upper lip / rigid incisor plane and lower opening TEST',font=font(26),fill='#253c49')
  d.text((35,65),'Previous continuous lip response',font=font(21),fill='#48636d');d.text((680,65),'Upper-jaw parent / experimental',font=font(21),fill='#48636d');im.paste(x,(55,95),x);im.paste(y,(700,95),y)
  d.text((35,625),f'Original voice / {t:.4f}s / F/V weight {fv:.4f} / native 512px heads',font=font(22),fill='#48636d')
  d.text((35,670),'Same source teeth, voice, timing, skin and chin. Placement study, not redrawn facial anatomy.',font=font(20),fill='#48636d');im.save(a.frames/f'{i:06}.png')
  if i in [546,548,550,552,554,564,566,569,571,630,631,632,633,634,637,638,646,648,649,650,651,653]:
   x.save(a.frames.parent/f'Old-{i}.png');y.save(a.frames.parent/f'Candidate-{i}.png')
  rows.append(dict(sourceFrame=i,time=t,fvWeight=fv,oldPainted=old.painted_rim is not None,newPainted=new.painted_rim is not None,minimumOralTriangleArea2=minimum,maxAlphaDifference=alpha_delta,changedPixels=int(np.any(xx!=yy,axis=2).sum())))
  if len(rows)%12==0:print(f'{a.start}: {len(rows)}',flush=True)
 code=Path(__file__).resolve().parent;sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 a.audit.write_text(json.dumps(dict(sourceStart=a.start,sourceEndExclusive=a.end,fps=48,width=1280,height=720,rows=rows,continuousFVSamples=new.continuous_fv_samples,continuousFVFallbacks=new.continuous_fv_fallbacks,dentalFallbacks=new.dental_fallbacks,upper290RowsExact=True,outsideOralROIExact=True,planSha256=sha(a.plan),codeSha256={n:sha(code/n) for n in ['maxillary_cartoon_head.py','continuous_fv_cartoon_head.py','render_maxillary_study.py']},timingChanged=False,defaultChanged=False,readyForPromotion=False),indent=2)+'\n')
