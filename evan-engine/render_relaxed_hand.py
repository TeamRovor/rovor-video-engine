"""Render a registered relaxed hand on the continuous acting accent, preserving acoustic timing."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
from detail_cartoon_scene import detail_controls,detail_event
from relaxed_cartoon_scene import RelaxedCartoonSceneBody
from render_cartoon_scene import frame
from painted_character import skin_vertices
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=684);p.add_argument('--end',type=int,default=828);a=p.parse_args();plan=json.loads(a.plan.read_text());body=RelaxedCartoonSceneBody();a.frames.mkdir(parents=True,exist_ok=True);rows=[]
 for i in range(a.start,a.end):
  t=i/48;c=detail_controls(t,plan);minimum={}
  for name,arm in body.arms.items():
   v=arm.posed_vertices(c[name]);tri=v[np.array(arm.triangles)];x=tri[:,1]-tri[:,0];y=tri[:,2]-tri[:,0];minimum[name]=float(np.min(x[:,0]*y[:,1]-x[:,1]*y[:,0]))
   if minimum[name]<=0:raise ValueError('Arm foldover')
  frame(body,plan,t).save(a.frames/f'{i:06}.jpg',quality=96);rows.append(dict(frame=i,time=t,controls=c,brows=body.head.expression_control(t,plan),minimumArmArea2=minimum))
  if len(rows)%12==0:print(f'{a.start}: {len(rows)}/{a.end-a.start}',flush=True)
 code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();a.audit.write_text(json.dumps(dict(start=a.start,end=a.end,fps=48,event=detail_event(plan),parentCommit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),planSha256=sha(a.plan),codeSha256={n:sha(code/n) for n in ['relaxed_cartoon_scene.py','build_relaxed_cartoon_hand.py','detail_cartoon_scene.py','render_relaxed_hand.py','painted_character.py']},sourceArtworkSha256={n:sha(code.parent/'evan-character/cartoon-v1/relaxed-hand-v1'/n) for n in ['source/right-relaxed-v2.png','right-skin.png','manifest.json']},newArtwork=True,phonemeTimingChanged=False,rows=rows,fallbacks=dict(dentalMorph=body.head.dental_morph_fallbacks,fv=body.head.fv_correspondence_fallbacks,dental=body.head.dental_fallbacks,rounded=body.head.contour_fallbacks)),indent=2)+'\n')
