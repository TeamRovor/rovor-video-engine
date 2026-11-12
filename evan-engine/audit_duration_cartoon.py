"""Geometry-only duration budget and independent contact-teeth evidence."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from duration_cartoon_head import DurationCartoonHead,duration_jaw_weights,duration_budget
from separated_cartoon_head import jaw_weights
from speech_planner import planned_weights

def kinematics(rows,a,b):
    selected=[r for r in rows if a<=r['frame']<b];out={}
    for name in ['oldAperture','newAperture']:
        values=np.array([r[name] for r in selected]);out[name]=dict(peak=float(values.max()),maximumFrameStep=float(np.abs(np.diff(values)).max()),maximumSecondDifference=float(np.abs(np.diff(values,n=2)).max()))
    return out
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text());head=DurationCartoonHead();head.capture_dental=True;rows=[];dental=[];contact_delta=0
    aperture=lambda w:float(sum(v*(head.geometry[k][7]-head.geometry[k][6]) for k,v in zip('XABCDEFGH',w)))
    for i in range(489):
        t=i/48;w=planned_weights(t,plan,plan['fallbackCues']);old=jaw_weights(t,plan,w);new=duration_jaw_weights(t,plan,w);contact_delta=max(contact_delta,float(np.abs(new[[1,7]]-old[[1,7]]).max()))
        rows.append(dict(frame=i,time=t,budget=duration_budget(t,plan),oldAperture=aperture(old),newAperture=aperture(new),contactWeight=float(w[7])))
        if not 0<float(w[7])<1:continue
        head.last_dental=None;head.at(t,plan)
        dental.append(dict(frame=i,**(head.last_dental or {'fallback':True})))
    report=dict(samples=489,contactGeometryChannelMaximumDifference=contact_delta,changedApertureSamples=sum(abs(r['oldAperture']-r['newAperture'])>1e-8 for r in rows),geometry='C/D jaw mass transfers to modest B; contact identity and recording-energy-weighted material weights are unchanged. Jaw/chin geometry intentionally changes.',favicon=kinematics(rows,402,450),earlyPhrase=kinematics(rows,187,235),wholeScene=kinematics(rows,0,489),dentalSamples=head.dental_samples,dentalFallbacks=head.dental_fallbacks,fvCorrespondenceFallbacks=head.fv_correspondence_fallbacks,roundedContourFallbacks=head.contour_fallbacks,allDentalSurfacesValid=all(r.get('validPremultiplied',False) for r in dental),limits='Authored duration curve/upper-edge quantile/source-component aperture, not measured biomechanics or verified phone boundaries. Kinematics are native geometry aperture, not rendered lip boundary or perceived smoothness. Teeth still blend with vowel materials.',rows=rows,dentalRows=dental)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['rows','dentalRows']},indent=2))
