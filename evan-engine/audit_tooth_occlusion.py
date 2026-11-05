"""Scene-clock tooth coverage/retraction evidence, not perceptual acceptance."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead,tooth_retraction
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from rounded_art_cartoon_head import rounded_art_strength
from rounded_cartoon_head import rounding_identity
from separated_cartoon_head import jaw_weights
from speech_planner import planned_weights

if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    plan=json.loads(a.plan.read_text());new=OccludedTeethCartoonHead();old=BroadCavityCartoonHead();rows=[];geometry_delta=0.
    for i in range(489):
        w=planned_weights(i/48,plan,plan['fallbackCues']);shape=rounding_identity(i/48,plan);jaw=jaw_weights(i/48,plan,w);target=new.target_points(jaw,shape)
        geometry_delta=max(geometry_delta,float(np.abs(target-old.target_points(jaw,shape)).max()))
        s=rounded_art_strength(w)
        if s<=0:continue
        aperture=sum(v*(new.geometry[k][7]-new.geometry[k][6]) for k,v in zip('XABCDEFGH',jaw));oral=new.oral_target(target,aperture)
        cavity=new.cavity_surface(w,oral,shape);mask=new.interior_mask(cavity,w,oral,shape)
        before=old.teeth_surface(w,oral,shape)*mask*(1-s)*old.teeth_rounding_visibility(w)
        after=new.teeth_surface(w,oral,shape)*mask
        rows.append({'frame':i,'time':i/48,'roundedStrength':s,'upwardRetractionPixels':tooth_retraction(w,oral),'oldRoundedOpacityFactor':(1-s)*old.teeth_rounding_visibility(w),'newRoundedOpacityFactor':1.,'oldToothCoveragePixelSumBeforeSharedApertureFVGate':float(before[:,:,3].sum()/255),'newToothCoveragePixelSumBeforeSharedApertureFVGate':float(after[:,:,3].sum()/255),'newMaximumAlphaAfterMatte':float(after[:,:,3].max())})
    full=[r for r in rows if r['roundedStrength']>=1-1e-9]
    report={'jawFaceTargetSamples':489,'jawFaceTargetMaximumDifference':geometry_delta,'roundedSamples':len(rows),'fullRoundedSamples':len(full),'fullRoundedStrengthTolerance':1e-9,'fullRoundedMaximumToothAlpha':max((r['newMaximumAlphaAfterMatte'] for r in full),default=0),'contourFallbacks':new.contour_fallbacks,'limits':'Coverage before shared aperture/FV gates. Authored 2D retraction, not measured anatomy, alignment accuracy or artistic quality.','rows':rows}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
