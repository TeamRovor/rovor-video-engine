"""One complete voiced thought with a word-anchored branded visual payoff."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
from finished_cartoon_scene import FinishedCartoonSceneBody,FinishedStage,finished_controls,finish_event,favicon_progress
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--separated-face',action='store_true',help='Use the ten-plane review face with existing finished-thought acting');p.add_argument('--start',type=int,default=696);p.add_argument('--end',type=int,default=936);a=p.parse_args();plan=json.loads(a.plan.read_text());body=FinishedCartoonSceneBody();stage=FinishedStage();a.frames.mkdir(parents=True,exist_ok=True);rows=[]
 if a.separated_face:body.enable_separated_face()
 for i in range(a.start,a.end):
  t=i/48;c=finished_controls(t,plan);minimum={}
  for name,arm in body.arms.items():
   tri=arm.posed_vertices(c[name])[np.array(arm.triangles)];x=tri[:,1]-tri[:,0];y=tri[:,2]-tri[:,0];minimum[name]=float(np.min(x[:,0]*y[:,1]-x[:,1]*y[:,0]))
   if minimum[name]<=0:raise ValueError('Arm foldover')
  stage.draw(body.render(t,plan),t,plan).save(a.frames/(f'{i:06}.png' if a.separated_face else f'{i:06}.jpg'),quality=96);rows.append(dict(frame=i,time=t,controls=c,brows=body.head.expression_control(t,plan),faviconProgress=favicon_progress(t,plan),minimumArmArea2=minimum,faceAudit=body.head.last_audit if a.separated_face else None))
  if len(rows)%24==0:print(f'{a.start}: {len(rows)}/{a.end-a.start}',flush=True)
 head=body.head.rig.head if a.separated_face else body.head
 code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();root=code.parent/'evan-character';a.audit.write_text(json.dumps(dict(start=a.start,end=a.end,fps=48,event=finish_event(plan),parentCommit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),planSha256=sha(a.plan),codeSha256={n:sha(code/n) for n in ['finished_cartoon_scene.py','render_finished_thought.py']},artworkSha256={n:sha(root/n) for n in ['cartoon-v1/relaxed-hand-v1/right-skin.png','cartoon-v1/source/design-sheet-v1.png','brand/rovor-mark-black.png']},separatedFace=a.separated_face,frameFormat='png' if a.separated_face else 'jpg',existingArtworkModified=False,phonemeTimingChanged=False,rows=rows,fallbacks=dict(dentalMorph=head.dental_morph_fallbacks,fv=head.fv_correspondence_fallbacks,dental=head.dental_fallbacks,rounded=head.contour_fallbacks)),indent=2)+'\n')
