"""Voiced aperture-response comparison; existing artwork and timing retained."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from aperture_response_cartoon_head import ApertureResponseCartoonHead
from painted_contour_cartoon_head import PaintedContourCartoonHead
from cartoon_head import TRIANGLES,area
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);a=p.parse_args()
 plan=json.loads(a.plan.read_text());old=PaintedContourCartoonHead();new=ApertureResponseCartoonHead();a.frames.mkdir(parents=True,exist_ok=True);rows=[]
 oral_tri=[ids for ids in TRIANGLES if max(ids)<32];source_min=min(area(new.painted_points,ids) for ids in oral_tri);assert source_min>0
 for i in range(714,774):
  t=i/48;x=old.at(t,plan);y=new.at(t,plan);xx=np.array(x);yy=np.array(y)
  np.testing.assert_array_equal(xx[:290],yy[:290])
  outside=np.ones((512,512),bool);outside[300:390,170:305]=False
  np.testing.assert_array_equal(xx[outside],yy[outside])
  alpha_delta=int(np.max(abs(xx[:,:,3].astype(int)-yy[:,:,3].astype(int))));assert alpha_delta<=1
  minimum=min(area(new.last_painted_target,ids) for ids in oral_tri) if new.painted_rim is not None else None
  if minimum is not None:assert minimum>0
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
  d.text((35,20),'Mouth response / remove the second aperture-closing gate',font=font(26),fill='#253c49')
  d.text((35,65),'Prior painted mouth response',font=font(21),fill='#48636d');d.text((680,65),'Direct inner/outer lips / TEST',font=font(21),fill='#48636d')
  im.paste(x,(55,95),x);im.paste(y,(700,95),y)
  d.text((35,625),f'Original voice / source {t:.4f}s / native 512px heads',font=font(22),fill='#48636d')
  d.text((35,670),'Same artwork, voice, phone timing and chin. Authored mouth response; anatomy still experimental.',font=font(20),fill='#48636d')
  im.save(a.frames/f'{i:06}.png')
  if i in [734,738,740,741,742,743,745,750]:
   x.save(a.frames.parent/f'Old-{i}.png');y.save(a.frames.parent/f'Candidate-{i}.png')
  def heights(head):
   o=head.last_painted_target;l,r=o[8],o[0];c=l[1]+(o[:32,0]-l[0])*(r[1]-l[1])/(r[0]-l[0]);return [float(np.ptp(o[:16,1]-c[:16])),float(np.ptp(o[16:32,1]-c[16:32]))]
  rows.append(dict(oldOuterInnerHeights=heights(old),newOuterInnerHeights=heights(new),sourceFrame=i,time=t,painted=new.painted_rim is not None,minimumOralTriangleArea2=minimum,maxAlphaDifference=alpha_delta,changedPixels=int(np.any(xx!=yy,axis=2).sum())))
  if len(rows)%12==0:print(len(rows),flush=True)
 a.audit.write_text(json.dumps(dict(sourceStart=714,sourceEndExclusive=774,fps=48,width=1280,height=720,sourceMinimumArea2=source_min,paintedSamples=new.painted_samples,sourceLandmarks=new.painted_points.tolist(),upper290RowsExact=True,outsideOralROIExact=True,maxAlphaDifference=max(r['maxAlphaDifference'] for r in rows),defaultChanged=False,timingChanged=False,readyForPromotion=False,rows=rows,planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest()),indent=2)+'\n')
