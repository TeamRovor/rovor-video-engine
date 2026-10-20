"""Full-head closed-seal diagnostic over original B/M phrase transitions."""
import argparse,json,hashlib,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from independent_chin_cartoon_head import IndependentChinCartoonHead
from uniform_seal_cartoon_head import UniformSealCartoonHead
from speech_planner import planned_weights
from duration_cartoon_head import duration_jaw_weights
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=668);p.add_argument('--end',type=int,default=772);a=p.parse_args();plan=json.loads(a.plan.read_text());old=IndependentChinCartoonHead();new=UniformSealCartoonHead();new.capture_seal=True;a.frames.mkdir(parents=True,exist_ok=True);rows=[];code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();hashes={n:sha(code/n) for n in ['layered_cartoon_head.py','uniform_seal_cartoon_head.py','independent_chin_cartoon_head.py','render_seal_phrase.py']};parent=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 for i in range(a.start,a.end):
  t=i/48;x=old.at(t,plan);new.last_seal=None;y=new.at(t,plan);d=np.any(np.asarray(x)!=np.asarray(y),axis=2);w=planned_weights(t,plan,plan['fallbackCues']);g=duration_jaw_weights(t,plan,w);aperture=float(sum(v*(new.geometry[k][7]-new.geometry[k][6]) for k,v in zip('XABCDEFGH',g)))
  im=Image.new('RGB',(1280,720),'#f3eee2');draw=ImageDraw.Draw(im);draw.text((35,20),'Bilabial seal drawing / original word and audio timing',font=font(27),fill='#253c49');draw.text((35,65),'Current closed-seal source',font=font(20),fill='#48636d');draw.text((680,65),'Separate seam / lower shadow — STUDY',font=font(20),fill='#48636d');im.paste(x,(55,95),x);im.paste(y,(700,95),y);words=[r['word'] for r in plan['words'] if r['start']<=t<r['end']];draw.text((35,625),f'Original source {t:.4f}s | '+(' '.join(words) or '(pause)'),font=font(22),fill='#48636d');draw.text((35,670),'Original rest retained / same oral aperture / no whole-face patch',font=font(19),fill='#48636d');im.save(a.frames/f'{i:06}.png')
  rows.append(dict(frame=i,time=t,bilabialWeight=float(w[1]),oralAperture=aperture,closedVisibility=new.closed_visibility(aperture),changedHeadPixels=int(d.sum()),seal=new.last_seal))
  if len(rows)%26==0:print(f'{a.start}: {len(rows)}/{a.end-a.start}',flush=True)
 root=Path(__file__).resolve().parents[1]/'evan-character/cartoon-v1/lip-seal-v1'
 report=dict(start=a.start,end=a.end,completed=len(rows),fps=48,parentCommit=parent,planSha256=sha(a.plan),codeSha256=hashes,assetSha256={n:sha(root/n) for n in ['seam.png','lower-shadow.png','manifest.json','source/seal-source-v3.png']},animationReady=False,rows=rows,limits='Pre-visibility seal component interpolation. Original contact/jaw/cavity alpha timing unchanged; not a continuous lip topology or artistic/sync acceptance.')
 a.audit.write_text(json.dumps(report,indent=2)+'\n')
