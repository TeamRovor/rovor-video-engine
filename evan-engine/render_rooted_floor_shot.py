"""Chunkable full-reference render with per-frame tongue/provenance evidence."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2
from rooted_floor_cartoon_scene import RootedFloorCartoonSceneBody
from render_cartoon_scene import frame
if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=489);a=p.parse_args()
    if not 0<=a.start<a.end<=489:raise ValueError('Reference interval outside0–489')
    plan=json.loads(a.plan.read_text());body=RootedFloorCartoonSceneBody();body.head.capture_tongue=True;a.frames.mkdir(parents=True,exist_ok=True);a.audit.parent.mkdir(parents=True,exist_ok=True);rows=[]
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();code=Path(__file__).resolve().parent
    sources={n:digest(code/n) for n in ['cartoon_head.py','cached_cartoon_sampling.py','rooted_floor_cartoon_head.py','rooted_floor_cartoon_scene.py','render_rooted_floor_shot.py','duration_cartoon_head.py','dental_fv_cartoon_head.py']}
    base=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    def save():
        report=dict(start=a.start,end=a.end,completed=len(rows),fps=48,planSha256=digest(a.plan),parentCommitAtStart=base,codeSha256=sources,meshCacheHits=body.head.mesh_cache_hits,meshCacheMisses=body.head.mesh_cache_misses,meshCacheEntries=len(body.head._surface_cache),fvFallbacks=body.head.fv_correspondence_fallbacks,dentalFallbacks=body.head.dental_fallbacks,roundedFallbacks=body.head.contour_fallbacks,limits='Tongue coverage before cavity matte/material gates; posed surface evidence, not visible mouth anatomy or artistic quality.',rows=rows)
        a.audit.write_text(json.dumps(report,indent=2)+'\n')
    for i in range(a.start,a.end):
        body.head.last_tongue=None;frame(body,plan,i/48).save(a.frames/f'{i:06}.jpg',quality=96);rows.append(dict(frame=i,**(body.head.last_tongue or {})))
        if len(rows)%24==0:save();print(f'{a.start}: {len(rows)}/{a.end-a.start}',flush=True)
    save();print(json.dumps({k:v for k,v in json.loads(a.audit.read_text()).items() if k not in ['rows','codeSha256']}))
