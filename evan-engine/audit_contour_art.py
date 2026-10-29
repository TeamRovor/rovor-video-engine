"""Reproducible scene-clock silhouette audit; not an artistic quality score."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from contour_cartoon_head import ContourCartoonHead
from rounded_art_cartoon_head import RoundedArtCartoonHead,rounded_art_strength
from speech_planner import planned_weights
from rounded_cartoon_head import rounding_identity
from separated_cartoon_head import jaw_weights

if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);p.add_argument('--light-lip',action='store_true');p.add_argument('--broad-cavity',action='store_true');a=p.parse_args()
    plan=json.loads(a.plan.read_text());
    if a.broad_cavity:
        from broad_cavity_cartoon_head import BroadCavityCartoonHead
        from light_lip_cartoon_head import LightLipCartoonHead
        head=BroadCavityCartoonHead();old_head=LightLipCartoonHead()
    elif a.light_lip:
        from light_lip_cartoon_head import LightLipCartoonHead
        head=LightLipCartoonHead();old_head=ContourCartoonHead()
    else:head=ContourCartoonHead();old_head=RoundedArtCartoonHead()
    rows=[];geometry_delta=0.
    for i in range(489):
        t=i/48;w=planned_weights(t,plan,plan['fallbackCues']);shape=rounding_identity(t,plan);jaw=jaw_weights(t,plan,w)
        target=head.target_points(jaw,shape)
        geometry_delta=max(geometry_delta,float(np.max(np.abs(target-old_head.target_points(jaw,shape)))))
        s=rounded_art_strength(w)
        if s<=0 or s>=1:continue
        aperture=sum(v*(head.geometry[k][7]-head.geometry[k][6]) for k,v in zip('XABCDEFGH',jaw));oral=head.oral_target(target,aperture)
        old,new,fields=head._aligned_oral(w,oral,shape)
        mismatch=lambda x,y:int(np.count_nonzero((x[:,:,3]>=127.5)!=(y[:,:,3]>=127.5)))
        if fields is None:
            rows.append({'frame':i,'strength':s,'fallback':True});continue
        moved=[head._remap(x,f) for x,f in zip((old,new),fields)]
        rows.append({'frame':i,'time':t,'strength':s,'fallback':False,'silhouetteDisagreementBefore':mismatch(old,new),'silhouetteDisagreementAligned':mismatch(*moved)})
    result={'samples':489,'geometryMaxAbsoluteDifference':geometry_delta,'partialRoundedFrames':len(rows),'fallbacks':head.contour_fallbacks,'metric':'Count of unequal >=50% alpha silhouette pixels in the two oral materials before blending; this measures correspondence, not appeal or lip-sync accuracy.','rows':rows}
    result['totalDisagreementBefore']=sum(x.get('silhouetteDisagreementBefore',0) for x in rows)
    result['totalDisagreementAligned']=sum(x.get('silhouetteDisagreementAligned',0) for x in rows)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
