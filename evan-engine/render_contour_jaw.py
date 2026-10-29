"""Same-art continuous jaw-contour ablation with original voice controls.

The clean jaw remains unapproved paint. This is the existing multi-control
head, not the rejected two-pose release adapter or a new default profile.
"""
import argparse,hashlib,json,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from cartoon_body import ROOT
from current_contact_exposure import CurrentContactExposure
from guided_jaw_exposure import contour_target_mesh,target_mesh
from labiodental_construction import load,FaceCapture
from lip_surface_correspondence import source_mesh
from render_cartoon_head_study import font

# shortcut: mouth subparts still share the upper carrier; separate them before production narration.
def render(plan_path,audio,output,start,end):
 if not 816<=start<end<=920:raise ValueError('This comparison covers only source816..919')
 cv2.setNumThreads(1);output.mkdir(parents=True,exist_ok=True);(output/'frames').mkdir(exist_ok=True)
 plan=json.loads(plan_path.read_text());rig=CurrentContactExposure();rig.head=FaceCapture();rig.jaw=load(ROOT/'jaw-simplification-v1/Jaw-Candidate.png');rig.source_points,_=source_mesh(rig.jaw)
 with wave.open(str(audio)) as w:
  if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('Expected original mono16k PCM16 voice')
  w.setpos(272000);samples=np.frombuffer(w.readframes(34667),dtype='<i2').astype(float)
 graph=Image.new('RGB',(1180,65),'#e4e1d7');g=ImageDraw.Draw(graph);scale=29/max(float(abs(samples).max()),1)
 for x,section in enumerate(np.array_split(samples,1180)):g.line((x,32-int(section.max()*scale),x,32-int(section.min()*scale)),fill='#48636d')
 rows=[]
 for i in range(start,end):
  t=i/48;baseline=rig.head.at(t,plan);oral=rig.head.current_oral.copy()
  # Existing drawn skin underlaps both antialiased attachment edges. Never
  # threshold/fill their alpha; cavity and jaw remain in front of the skin.
  underpaint=np.zeros_like(rig.head.clean_face);underpaint[305:365,190:285]=rig.head.clean_face[305:365,190:285]
  _,old,previous=rig.assemble_target(baseline,*target_mesh(oral,rig.head.exposure_skin),underpaint)
  target,minimum=contour_target_mesh(oral,rig.head.exposure_skin);_,new,row=rig.assemble_target(baseline,target,minimum,underpaint)
  before=np.array(old);after=np.array(new);np.testing.assert_array_equal(before[:288],after[:288]);upper_delta=int(abs(before[:315].astype(int)-after[:315].astype(int)).max())
  if upper_delta>1:raise ValueError(f'Upper head exceeded existing one-level sampling tolerance: {upper_delta}')
  active=[p for p in plan['phonemes'] if p['start']<=t<p['end']];word=' / '.join(dict.fromkeys(p['word'] for p in active));phone=' / '.join(p['phone'] for p in active)
  row.update(sourceFrame=i,time=t,arch=oral[:9].tolist(),originalInnerLowerY=float(oral[20,1]),mouthWidth=float(oral[0,0]-oral[8,0]),activePhones=active,legacyOralBelow240=previous['oralBelow240'],twoPoseReleaseMapping=False,upper288PairExact=True,upper315PairExact=upper_delta==0,upper315MaximumChange=upper_delta);rows.append(row)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((25,15),'CONTINUOUS JAW / same original voice, controls and source artwork',font=font(24),fill='#253c49')
  d.text((35,55),'Legacy center/corner reconstruction',font=font(22),fill='#48636d');d.text((685,55),'Actual lower-arch correspondence',font=font(22),fill='#48636d');im.paste(old,(55,75),old);im.paste(new,(700,75),new)
  im.paste(graph,(50,575));cursor=50+round((t-17)/(104/48)*1180);d.line((cursor,575,cursor,640),fill='#c35b41',width=2)
  d.text((35,650),f'{word} [{phone}] / {t:.4f}s / width {row["mouthWidth"]:.2f}px / waveform peak-scaled',font=font(20),fill='#253c49')
  d.text((35,682),'No timing edits or two-pose clipping. Mouth pressure, artwork placement and sync accuracy remain unaccepted.',font=font(18),fill='#48636d');im.save(output/'frames'/f'{i:06}.png')
  if i in [816,840,848,851,855,856,864,872,887,892,895,919]:old.save(output/f'Legacy-{i}.png');new.save(output/f'Contour-{i}.png')
  if i%16==0:print(i,flush=True)
 (output/f'Audit-{start}.json').write_text(json.dumps(dict(rows=rows,planSha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),sourceAudioSha256=hashlib.sha256(audio.read_bytes()).hexdigest(),timingChanged=False,sourceArtworkChanged=False,underpaintSource='Current posed drawn clean-face skin, behind cavity/jaw on BOTH sides',underpaintBox=[190,305,285,365],alphaCleanup=False,anatomyAccepted=False,defaultChanged=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('audio',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=int,default=816);p.add_argument('--end',type=int,default=920);a=p.parse_args();render(a.plan,a.audio,a.output,a.start,a.end)
