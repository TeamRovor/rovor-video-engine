"""Scene-clock F/V contour disagreement evidence, not perceptual approval."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from planar_fv_cartoon_head import PlanarFVCartoonHead
from speech_planner import planned_weights
from rounded_cartoon_head import rounding_identity
from separated_cartoon_head import jaw_weights
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text());new=CorrespondentFVCartoonHead();old=PlanarFVCartoonHead();new.capture_fv_registration=True;rows=[];delta=0
    for i in range(489):
        w=planned_weights(i/48,plan,plan['fallbackCues']);shape=rounding_identity(i/48,plan);jaw=jaw_weights(i/48,plan,w)
        delta=max(delta,float(np.abs(new.target_points(jaw,shape)-old.target_points(jaw,shape)).max()))
        if not 0<float(w[7])<1:continue
        new.last_fv_registration=None;new.at(i/48,plan)
        rows.append(dict(frame=i,time=i/48,**(new.last_fv_registration or {'fallback':True})))
    report=dict(jawFaceTargetSamples=489,jawFaceTargetMaximumDifference=delta,registeredMixedSamples=new.fv_correspondence_samples,fvCorrespondenceFallbacks=new.fv_correspondence_fallbacks,roundedContourFallbacks=new.contour_fallbacks,beforeDisagreementPixelSum=sum(r.get('beforeDisagreementPixels',0) for r in rows),afterDisagreementPixelSum=sum(r.get('afterDisagreementPixels',0) for r in rows),allSurfacesValid=all(r.get('validPremultiplied',False) for r in rows),limits='Disagreement is between 50%-alpha silhouettes, not inner lip/teeth anatomy, temporal smoothness or phonetic accuracy. Tiny nonzero FV tails are included.',rows=rows)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'}))
