"""Scene-clock uniform contact-plane audit; no alignment/quality acceptance."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from planar_fv_cartoon_head import PlanarFVCartoonHead,contact_matrix
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead
from rounded_cartoon_head import rounding_identity
from separated_cartoon_head import jaw_weights
from speech_planner import planned_weights
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    plan=json.loads(a.plan.read_text());new=PlanarFVCartoonHead();old=OccludedTeethCartoonHead();rows=[];delta=0
    for i in range(489):
        w=planned_weights(i/48,plan,plan['fallbackCues']);shape=rounding_identity(i/48,plan);jaw=jaw_weights(i/48,plan,w);t=new.target_points(jaw,shape)
        delta=max(delta,float(np.abs(t-old.target_points(jaw,shape)).max()));m=contact_matrix(t,new.fv_v3_meta['sourceCorners']);linear=m[:,:2];det=float(np.linalg.det(linear));error=float(np.abs(linear.T@linear-np.eye(2)*det).max())
        rows.append(dict(frame=i,contactWeight=float(w[7]),uniformScale=float(np.sqrt(det)),determinant=det,uniformMatrixError=error,matrix=m.tolist()))
    report=dict(samples=489,jawFaceTargetMaximumDifference=delta,minimumDeterminant=min(r['determinant'] for r in rows),maximumUniformMatrixError=max(r['uniformMatrixError'] for r in rows),activeContactSamples=sum(r['contactWeight']>0 for r in rows),limits='One shared F/V art pose. No timing edits, measured anatomy or perceptual acceptance.',rows=rows)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
