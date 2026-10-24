"""Voiced comparison of a source jaw-layer exposure, not accepted lip sync."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from current_contact_exposure import CurrentContactExposure
from contact_crown_audit import CrownCaptureHead,crown_continuation,crown_coverage
from jaw_overlap_exposure import upper_ownership
from lip_surface_correspondence import source_mesh
from layered_cartoon_head import over,straight
from cartoon_body import ROOT
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=840);p.add_argument('--end',type=int,default=888);a=p.parse_args();a.frames.mkdir(parents=True,exist_ok=True);plan=json.loads(a.plan.read_text());rig=CurrentContactExposure();rig.head=CrownCaptureHead();rig.jaw=np.array(Image.open(ROOT/'fv-redraw-v1/Contact-Jaw-Candidate.png').convert('RGBA')).astype('float32');rig.jaw[:,:,:3]*=rig.jaw[:,:,3:4]/255;rig.source_points,_=source_mesh(rig.jaw);rows=[]
 for i in range(a.start,a.end):
  _,old,row=rig.at(i/48,plan)
  ownership=upper_ownership(rig.last_target);plane=crown_continuation(rig.head.audit_crown,ownership,row['fv']);base=np.zeros_like(plane)
  for part in rig.last_parts.values():base=over(base,part)
  new=old if row['fv']<=0 else Image.fromarray(np.rint(straight(over(base,plane))).astype('uint8'))
  if row['fv']>0:row.update(crown_coverage(rig.head.audit_crown,ownership))
  row.update(counterfactual=True,continuationAlphaArea=float(plane[:,:,3].sum()/255))
  x=np.array(old);y=np.array(new);np.testing.assert_array_equal(x[:288],y[:288]);row.update(sourceFrame=i,time=i/48)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((30,20),'TOOTH OWNERSHIP / counterfactual material test',font=font(27),fill='#253c49');d.text((30,65),'Existing four-plane jaw candidate',font=font(22),fill='#48636d');d.text((680,65),'Removed crown material continued in front',font=font(22),fill='#48636d');im.paste(old,(55,95),old);im.paste(new,(700,95),new)
  d.text((30,625),f'Original voice / {i/48:.4f}s / lip and chin controls retained / native 512px heads',font=font(21),fill='#48636d');d.text((30,668),'Same artwork, voice and timing. Ownership ablation only: lower-lip occlusion and anatomy remain unaccepted.',font=font(20),fill='#48636d');im.save(a.frames/f'{i:06}.png');rows.append(row)
  if i in [840,848,850,851,854,855,856,887]:old.save(a.frames.parent/f'Old-{i}.png');new.save(a.frames.parent/f'Candidate-{i}.png')
  if len(rows)%10==0:print(f'{a.start}: {len(rows)}',flush=True)
 a.audit.write_text(json.dumps(dict(sourceStart=a.start,sourceEndExclusive=a.end,fps=48,rows=rows,upper288RowsExact=True,timingChanged=False,defaultProfileChanged=False,reviewToolLoaded=True,animationReady=False,carrier='existing upper face with authored front cheek ownership',source='fv-redraw-v1 jaw candidate plus actual contact crown continuation; no new artwork',sourceCorrespondence=rig.correspondence,planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest()),indent=2)+'\n')
