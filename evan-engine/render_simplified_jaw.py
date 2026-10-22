"""Restricted voiced jaw-art comparison, not a narration-ready face profile.

Both sides use the same original oral control and fixed six-plane construction.
Only the jaw drawing/its source correspondence differs. Clamped release cannot
represent vowels, tongue or lip pressure; this deliberately exposes that limit.
"""
import argparse,hashlib,json,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from cartoon_body import ROOT
from current_contact_exposure import CurrentContactHead
from labiodental_construction import LabiodentalConstruction,load
from lip_surface_correspondence import source_mesh
from render_cartoon_head_study import font

def render(plan_path,audio,output,start,end):
 if not 840<=start<end<=888:raise ValueError('This review covers only source frames840..887')
 cv2.setNumThreads(1);output.mkdir(parents=True,exist_ok=True);(output/'frames').mkdir(exist_ok=True)
 plan=json.loads(plan_path.read_text());driver=CurrentContactHead();old=LabiodentalConstruction();new=LabiodentalConstruction()
 new.jaw=load(ROOT/'jaw-simplification-v1/Jaw-Candidate.png');new.source_points,_=source_mesh(new.jaw)
 with wave.open(str(audio)) as w:
  assert w.getframerate()==16000 and w.getnchannels()==1 and w.getsampwidth()==2
  w.setpos(280000);pcm=w.readframes(16000)
 samples=np.frombuffer(pcm,dtype='<i2').astype(float)/32768
 graph=Image.new('RGB',(1180,65),'#e4e1d7');g=ImageDraw.Draw(graph)
 for x,section in enumerate(np.array_split(samples,1180)):
  g.line((x,32-int(section.max()*28),x,32-int(section.min()*28)),fill='#48636d')
 rows=[]
 for i in range(start,end):
  t=i/48;driver.at(t,plan);lower=float(driver.current_oral[20,1]);release=float(np.clip((lower-325)/7,0,1))
  before,a=old.pose(release);after,b=new.pose(release)
  np.testing.assert_array_equal(np.array(before)[:315],np.array(after)[:315])
  active=[p for p in plan['phonemes'] if p['start']<=t<p['end']]
  row=dict(sourceFrame=i,time=t,originalLowerControlY=lower,release=release,releaseClamped=not 325<=lower<=332,fv=float(driver.current_fv),minimumTriangleArea2=min(a['minimumTriangleArea2'],b['minimumTriangleArea2']),activePhone=active,upper315RowsExact=True)
  rows.append(row)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
  d.text((25,15),'JAW DRAWING / original audio and articulation controls',font=font(25),fill='#253c49')
  d.text((35,55),'Previous fold',font=font(22),fill='#48636d');d.text((685,55),'Simplified source / placement unaccepted',font=font(22),fill='#48636d')
  im.paste(before,(55,75),before);im.paste(after,(700,75),after)
  im.paste(graph,(50,575));cursor=50+round((t-17.5)*1180);d.line((cursor,575,cursor,640),fill='#c35b41',width=2)
  d.text((35,650),f'feel / way | {t:.4f}s | lower control {lower:.2f} | release {release:.3f}',font=font(20),fill='#253c49')
  d.text((35,682),'Restricted contact-release mapping; vowels/pressure/acting remain unsupported. Timing is unchanged and unverified.',font=font(18),fill='#48636d')
  im.save(output/'frames'/f'{i:06}.png')
  if i in [840,848,851,855,856,864,876,887]:before.save(output/f'Previous-{i}.png');after.save(output/f'Candidate-{i}.png')
  if i%12==0:print(i,flush=True)
 (output/f'Audit-{start}.json').write_text(json.dumps(dict(rows=rows,planSha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),sourceAudioSha256=hashlib.sha256(audio.read_bytes()).hexdigest(),sourceTimingChanged=False,anatomyAccepted=False,fullSpeechProfile=False,defaultChanged=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('audio',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=int,default=840);p.add_argument('--end',type=int,default=888);a=p.parse_args();render(a.plan,a.audio,a.output,a.start,a.end)
