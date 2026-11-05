"""Read-only audit of actual contact-incisor loss at the upper-face ownership cut.

This measures a component before/after ONE carrier mask, not final visible
teeth, lip-sync accuracy or anatomy. It does not change the rendered head.
"""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from current_contact_exposure import CurrentContactHead,CurrentContactExposure
from dental_fv_cartoon_head import tooth_anchor
from layered_cartoon_head import straight
from render_cartoon_head_study import font

class CrownCaptureHead(CurrentContactHead):
 def contact_surface(self,target):
  result=super().contact_surface(target)
  self.audit_crown=self._dental_parts['upper-teeth'].copy()
  return result
 def registered_contact_surface(self,contact,field,w):
  result=super().registered_contact_surface(contact,field,w)
  original=self._dental_parts['upper-teeth'];stretched=self._remap(original,field)
  delta=tooth_anchor(stretched)-tooth_anchor(original)
  matrix=np.array([[1,0,delta[0]],[0,1,delta[1]]],np.float32)
  rigid=cv2.warpAffine(original,matrix,(512,512),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  self.audit_crown=rigid*np.clip(self._remap(self._dental_window,field),0,1)[:,:,None]
  return result

def crown_continuation(crown,ownership,fv):
 # Counterfactual material placement: expose only the source crown removed
 # by this ownership cut. This deliberately does not prove lip occlusion.
 return crown*(1-ownership)[:,:,None]*float(fv)

def crown_coverage(crown,ownership):
 before=crown[:,:,3].astype(float)/255;after=before*ownership;mass=float(before.sum())
 if mass<=0:raise ValueError('Empty incisor material')
 return dict(beforeCarrierAlphaArea=mass,afterCarrierAlphaArea=float(after.sum()),removedFraction=float((before-after).sum()/mass),beforeOpaquePixels=int(np.count_nonzero(before>=.5)),afterOpaquePixels=int(np.count_nonzero(after>=.5)))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=int,default=848);p.add_argument('--end',type=int,default=899);a=p.parse_args();cv2.setNumThreads(1);a.output.mkdir(parents=True,exist_ok=True)
 plan=json.loads(a.plan.read_text());rig=CurrentContactExposure();rig.head=CrownCaptureHead();rows=[]
 from jaw_overlap_exposure import upper_ownership
 for frame in range(a.start,a.end):
  _,head,row=rig.at(frame/48,plan)
  if row['fv']<=0:continue
  crown=rig.head.audit_crown;mask=upper_ownership(rig.last_target);coverage=crown_coverage(crown,mask);rows.append(dict(sourceFrame=frame,time=frame/48,fv=row['fv'],**coverage))
  if frame in [850,851,854,855,892,895]:
   im=Image.new('RGB',(1120,650),'#f3eee2');d=ImageDraw.Draw(im);d.text((20,15),f'Contact incisor ownership / source frame {frame} / no render change',font=font(25),fill='#253c49');im.paste(head,(15,65),head)
   # Same actual material shown over a dark background, enlarged with nearest
   # sampling only for inspection. No threshold modifies material alpha.
   for x,part,label in [(570,crown,'Actual contact crown'),(845,crown*mask[:,:,None],'After carrier cut')]:
    tile=Image.new('RGBA',(100,50),'#405563');tile.alpha_composite(Image.fromarray(np.rint(straight(part)).astype('uint8')).crop((185,305,285,355)));im.paste(tile.convert('RGB').resize((250,125),Image.Resampling.NEAREST),(x,180));d.text((x,135),label,font=font(18),fill='#253c49')
   d.text((570,350),f"Carrier removes {coverage['removedFraction']:.1%} of alpha area",font=font(22),fill='#253c49');d.text((20,610),'Component ownership diagnosis only; final occlusion and anatomical validity are separate.',font=font(21),fill='#253c49');im.save(a.output/f'Crown-{frame}.png')
 report=dict(rows=rows,renderChanged=False,sourceArtworkChanged=False,timingChanged=False,measures='contact incisor material before/after upper-face carrier ownership ONLY',limits='Not final visible-tooth area: ignores overlap with other foreground paint and FV material blend. Alpha area is fractional coverage, not tooth anatomy.',anatomyAccepted=False)
 (a.output/'Crown-Ownership-Audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(frames=len(rows),maximumRemovedFraction=max(r['removedFraction'] for r in rows),minimumRemovedFraction=min(r['removedFraction'] for r in rows)),indent=2))
