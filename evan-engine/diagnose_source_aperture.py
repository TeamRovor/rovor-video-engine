"""Inspect the actual painted hole and post-mask teeth at two flagged frames.

Alpha threshold detects a source contour for analysis only; no source cleanup.
"""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from continuous_fv_cartoon_head import ContinuousFVCartoonHead
from maxillary_cartoon_head import MaxillaryCartoonHead
from painted_contour_cartoon_head import oral_fields
class Capture:
 def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
  self.captured_teeth=teeth.copy();return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
class Previous(Capture,ContinuousFVCartoonHead):pass
class Study(Capture,MaxillaryCartoonHead):pass
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True);plan=json.loads(a.plan.read_text());old,new=Previous(),Study();rim=old.painted['Rim'];n,labels,stats,_=cv2.connectedComponentsWithStats((rim[:,:,3]<128).astype('uint8'),8)
 ids=[i for i in range(1,n) if stats[i,0]>0 and stats[i,1]>0 and stats[i,0]+stats[i,2]<rim.shape[1] and stats[i,1]+stats[i,3]<rim.shape[0]]
 if not ids:raise ValueError('Missing enclosed source aperture')
 hole=(labels==max(ids,key=lambda i:stats[i,4])).astype('float32')*255;rows=[]
 for i in [554,630]:
  for name,h in [('previous',old),('maxillary',new)]:
   h.at(i/48,plan);fields=oral_fields(h.painted_points,h.last_painted_target);matte=cv2.resize(cv2.remap(hole,*fields,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA);alpha=h.captured_teeth[:,:,3]
   rows.append(dict(frame=i,profile=name,postMaskToothCoveragePixels=float(alpha.sum()/255),postMaskMaxAlpha=float(alpha.max()),opaqueToothPixelsOutsideSourceHole=int(np.count_nonzero((alpha>=127.5)&(matte<127.5)))))
 report=dict(rows=rows,sourceAlphaAlreadyIsolated=True,hiddenFaceRGBIsVisible=False,sourcePixelsChanged=False,limits='Coverage is not an acting-quality measure. Original tooth opacity is already isolated; source-hole threshold is analysis only, not color-key cleanup.')
 (a.output/'Source-Aperture-Diagnosis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
