"""Narrated favicon scene through its real pause; no automatic approval/deploy."""
import argparse,json
from pathlib import Path
import cv2
from PIL import ImageDraw
from cartoon_scene import CartoonSceneBody,CartoonMaterialSceneBody
from render_cartoon_gesture_study import frame as base_frame
from render_cartoon_head_study import font

FPS=48;FRAME_COUNT=489

def frame(body,plan,t):
    im=base_frame(body,plan,t,review_labels=False);d=ImageDraw.Draw(im)
    favicon=next(w for w in plan['words'] if w['word']=='favicon')
    if t>=favicon['start']:
        d.ellipse((783,360,822,399),outline='#ba684b',width=3)
        d.text((685,603),'That globe can mean a missing favicon.',font=font(22),fill='#48636d')
    else:d.text((685,603),'A small detail that represents your brand.',font=font(22),fill='#48636d')
    return im
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--material',action='store_true');p.add_argument('--compact-index',action='store_true');p.add_argument('--joined-wrist',action='store_true');p.add_argument('--lingual-tongue',action='store_true');p.add_argument('--separated-jaw',action='store_true');p.add_argument('--anchored-skin',action='store_true');p.add_argument('--bounded-head',action='store_true');p.add_argument('--rounded-art',action='store_true');p.add_argument('--contour-art',action='store_true');p.add_argument('--light-lip',action='store_true');p.add_argument('--broad-cavity',action='store_true');p.add_argument('--occluded-teeth',action='store_true');p.add_argument('--planar-fv',action='store_true');p.add_argument('--correspondent-fv',action='store_true');p.add_argument('--duration-jaw',action='store_true');p.add_argument('--rooted-floor',action='store_true');p.add_argument('--drawn-dental',action='store_true');p.add_argument('--independent-chin',action='store_true');p.add_argument('--uniform-seal',action='store_true');p.add_argument('--rounded-duration',action='store_true');p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=FRAME_COUNT);a=p.parse_args()
    plan=json.loads(a.plan.read_text())
    if a.rounded_duration:
        from rounded_duration_cartoon_scene import RoundedDurationCartoonSceneBody
        body=RoundedDurationCartoonSceneBody()
    elif a.uniform_seal:
        from uniform_seal_cartoon_scene import UniformSealCartoonSceneBody
        body=UniformSealCartoonSceneBody()
    elif a.independent_chin:
        from independent_chin_cartoon_scene import IndependentChinCartoonSceneBody
        body=IndependentChinCartoonSceneBody()
    elif a.drawn_dental:
        from drawn_dental_cartoon_scene import DrawnDentalCartoonSceneBody
        body=DrawnDentalCartoonSceneBody()
    elif a.rooted_floor:
        from rooted_floor_cartoon_scene import RootedFloorCartoonSceneBody
        body=RootedFloorCartoonSceneBody()
    elif a.duration_jaw:
        from duration_cartoon_scene import DurationCartoonSceneBody
        body=DurationCartoonSceneBody()
    elif a.correspondent_fv:
        from correspondent_fv_cartoon_scene import CorrespondentFVCartoonSceneBody
        body=CorrespondentFVCartoonSceneBody()
    elif a.planar_fv:
        from planar_fv_cartoon_scene import PlanarFVCartoonSceneBody
        body=PlanarFVCartoonSceneBody()
    elif a.occluded_teeth:
        from occluded_teeth_cartoon_scene import OccludedTeethCartoonSceneBody
        body=OccludedTeethCartoonSceneBody()
    elif a.broad_cavity:
        from broad_cavity_cartoon_scene import BroadCavityCartoonSceneBody
        body=BroadCavityCartoonSceneBody()
    elif a.light_lip:
        from light_lip_cartoon_scene import LightLipCartoonSceneBody
        body=LightLipCartoonSceneBody()
    elif a.contour_art:
        from contour_cartoon_scene import ContourCartoonSceneBody
        body=ContourCartoonSceneBody()
    elif a.rounded_art:
        from rounded_art_cartoon_scene import RoundedArtCartoonSceneBody
        body=RoundedArtCartoonSceneBody()
    elif a.bounded_head:
        from bounded_cartoon_scene import BoundedCartoonSceneBody
        body=BoundedCartoonSceneBody()
    elif a.anchored_skin:
        from anchored_cartoon_scene import AnchoredCartoonSceneBody
        body=AnchoredCartoonSceneBody()
    elif a.separated_jaw:
        from separated_cartoon_scene import SeparatedCartoonSceneBody
        body=SeparatedCartoonSceneBody()
    elif a.lingual_tongue:
        from lingual_cartoon_scene import LingualCartoonSceneBody
        body=LingualCartoonSceneBody()
    elif a.joined_wrist:
        from joined_cartoon_wrist import JoinedWristSceneBody
        body=JoinedWristSceneBody()
    elif a.compact_index:
        from compact_cartoon_scene import CompactCartoonSceneBody
        body=CompactCartoonSceneBody()
    else:body=CartoonMaterialSceneBody() if a.material else CartoonSceneBody()
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(body,plan,i/FPS).save(a.frames/f'{i:06}.jpg',quality=96)
    summary=dict(start=a.start,end=a.end,fps=FPS)
    if a.rooted_floor:summary.update(meshCacheHits=body.head.mesh_cache_hits,meshCacheMisses=body.head.mesh_cache_misses,meshCacheEntries=len(body.head._surface_cache),fvFallbacks=body.head.fv_correspondence_fallbacks,dentalFallbacks=body.head.dental_fallbacks,roundedFallbacks=body.head.contour_fallbacks)
    print(json.dumps(summary))
