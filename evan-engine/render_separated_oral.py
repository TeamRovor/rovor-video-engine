"""Voiced comparison of old combined material versus ten separate planes."""
import argparse,hashlib,json,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from separated_oral_review import SeparatedOralReview
from current_contact_exposure import CurrentContactExposure
from render_cartoon_head_study import font

if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('audio',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=int,default=816);p.add_argument('--end',type=int,default=920);a=p.parse_args()
 if not 0<=a.start<a.end:raise ValueError('Expected a positive source-frame interval')
 a.output.mkdir(parents=True,exist_ok=True);(a.output/'frames').mkdir(exist_ok=True);plan=json.loads(a.plan.read_text());rig=SeparatedOralReview();prior=CurrentContactExposure();prior.head=rig.head;prior.jaw=rig.jaw;prior.source_points=rig.source_points;prior.neck=rig.neck;rows=[]
 with wave.open(str(a.audio)) as w:
  if (w.getframerate(),w.getnchannels(),w.getsampwidth())!=(16000,1,2):raise ValueError('Expected original mono16k PCM16 voice')
  first=round(a.start/48*16000);last=round(a.end/48*16000)
  if last>w.getnframes():raise ValueError('Review interval exceeds original voice')
  w.setpos(first);samples=np.frombuffer(w.readframes(last-first),dtype='<i2').astype(float)
 graph=Image.new('RGB',(1180,65),'#e4e1d7');g=ImageDraw.Draw(graph);scale=29/max(float(abs(samples).max()),1)
 for x,section in enumerate(np.array_split(samples,1180)):
  if section.size:g.line((x,32-int(section.max()*scale),x,32-int(section.min()*scale)),fill='#48636d')
 for i in range(a.start,a.end):
  t=i/48;new,row=rig.at(t,plan);_,old,_=prior.assemble_target(rig.baseline,rig.last_target,row['minimumTriangleArea2'],rig.last_parts['Drawn skin underlap']);np.testing.assert_array_equal(np.array(old)[:288],np.array(new)[:288])
  active=[p for p in plan['phonemes'] if p['start']<=t<p['end']];word=' / '.join(dict.fromkeys(p['word'] for p in active));phone=' / '.join(p['phone'] for p in active)
  row.update(sourceFrame=i,time=t,activePhones=active,dentalTipAlphaArea=float(rig.head.review_dental_tip[:,:,3].sum()/255),oralAlphaMinimum=int(np.array(new)[315:345,195:280,3].min()));rows.append(row)
  im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((25,15),'NARRATED MOUTH / separate lips, jaw, incisors, cavity and tongue',font=font(24),fill='#253c49');d.text((35,55),'Prior carrier / combined mouth paint',font=font(22),fill='#48636d');d.text((685,55),'Ten actual planes / full oral controls',font=font(22),fill='#48636d');im.paste(old,(55,75),old);im.paste(new,(700,75),new);im.paste(graph,(50,575));cursor=50+round((t-a.start/48)/((a.end-a.start)/48)*1180);d.line((cursor,575,cursor,640),fill='#c35b41',width=2)
  d.text((35,650),f'{word} [{phone}] / {t:.4f}s / original voice and alignment / peak-scaled waveform',font=font(20),fill='#253c49');d.text((35,682),'Pressure remains a thickness proxy. Contact shape, expressions and sync accuracy are unaccepted.',font=font(19),fill='#48636d');im.save(a.output/'frames'/f'{i:06}.png')
  if i==a.start or i==a.end-1 or any(x['phone'] in ('TH','DH') for x in active):new.save(a.output/f'Separated-{i}.png');old.save(a.output/f'Prior-{i}.png')
  if i%16==0:print(i,flush=True)
 (a.output/f'Audit-{a.start}.json').write_text(json.dumps(dict(rows=rows,planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),audioSha256=hashlib.sha256(a.audio.read_bytes()).hexdigest(),timingChanged=False,sourceArtworkChanged=False,defaultChanged=False,anatomyAccepted=False),indent=2)+'\n')
