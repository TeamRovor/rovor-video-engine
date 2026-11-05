"""Three real-voice AO contexts, full native heads and geometry provenance."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from independent_chin_cartoon_head import IndependentChinCartoonHead
from rounded_duration_cartoon_head import RoundedDurationCartoonHead,rounded_duration_jaw_weights
from duration_cartoon_head import duration_jaw_weights
from rounded_cartoon_head import rounding_identity
from cartoon_head import TRIANGLES
from render_cartoon_head_study import font
RANGES=[(706,772,'Super small detail'),(872,920,'way / more / finished'),(968,1008,'up / all / the time')]
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--section',type=int,choices=[0,1,2],required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());old=IndependentChinCartoonHead();new=RoundedDurationCartoonHead();new.capture_rounding=True;a.frames.mkdir(parents=True,exist_ok=True);rows=[];ids=np.asarray(TRIANGLES);code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();hashes={n:sha(code/n) for n in ['duration_cartoon_head.py','rounded_duration_cartoon_head.py','render_rounded_duration.py']};parent=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();lo,hi,label=RANGES[a.section];offset=sum(b-a for a,b,_ in RANGES[:a.section])
 for i in range(lo,hi):
  t=i/48;x=old.at(t,plan);new.last_rounding=None;y=new.at(t,plan);g0=duration_jaw_weights(t,plan);g1=rounded_duration_jaw_weights(t,plan);shape=rounding_identity(t,plan);target0=old.target_points(g0,shape);new._rounded_reference=g0
  try:target1=new.target_points(g1,shape)
  finally:new._rounded_reference=None
  np.testing.assert_array_equal(target0[:,0],target1[:,0]);np.testing.assert_array_equal(target0[[0,8]],target1[[0,8]]);np.testing.assert_array_equal(target0[32:],target1[32:]);oral=new.oral_target(target1,new.last_rounding['newAperture']);tri=oral[ids];v1=tri[:,1]-tri[:,0];v2=tri[:,2]-tri[:,0];minimum=float(np.min(v1[:,0]*v2[:,1]-v1[:,1]*v2[:,0]));difference=np.any(np.asarray(x)!=np.asarray(y),axis=2)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((35,20),'Short rounded vowel height / original voice and timing',font=font(27),fill='#253c49');d.text((35,65),'Current rounded opening',font=font(20),fill='#48636d');d.text((680,65),'Conservative AO height — STUDY',font=font(20),fill='#48636d');im.paste(x,(55,95),x);im.paste(y,(700,95),y);d.text((35,625),f'{label} | original source {t:.4f}s',font=font(21),fill='#48636d');d.text((35,670),'Same rounding / mouth corners / contact weights / chin track',font=font(19),fill='#48636d');index=offset+i-lo;im.save(a.frames/f'{index:06}.png');rows.append(dict(frame=index,sourceFrame=i,time=t,**new.last_rounding,changedHeadPixels=int(difference.sum()),minimumOralTriangleArea2=minimum))
  if len(rows)%24==0:print(f'{a.section}: {len(rows)}/{hi-lo}',flush=True)
 report=dict(section=a.section,start=lo,end=hi,completed=len(rows),ranges=RANGES,fps=48,parentCommit=parent,codeSha256=hashes,planSha256=sha(a.plan),artworkChanged=False,phonemeTimingChanged=False,animationReady=False,fallbacks=dict(dentalMorph=new.dental_morph_fallbacks,fv=new.fv_correspondence_fallbacks,dental=new.dental_fallbacks,rounded=new.contour_fallbacks),rows=rows,limits='Authored75%minimum AO excursion; original uncertain aligner boundaries retained. Peak/step metrics are controls, not perceptual/physiological/synchronization acceptance.')
 a.audit.write_text(json.dumps(report,indent=2)+'\n')
