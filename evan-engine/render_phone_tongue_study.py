"""Native-resolution before/after excerpts; explicit source times and waveform.

This study evaluates an authored deformation, not an approved anatomy change.
"""
import argparse,json,hashlib,wave
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from rooted_floor_cartoon_head import RootedFloorCartoonHead
from phone_tongue_cartoon_head import PhoneTongueCartoonHead,dental_fraction
from render_cartoon_head_study import font
RANGES=[(76,100,'DH / that'),(124,148,'L / little'),(312,336,'TH / thing')]

def run(plan_path,wav_path,out,drawn_dental=False):
 cv2.setNumThreads(1);out.mkdir(parents=True,exist_ok=True);frames=out/'frames';frames.mkdir(exist_ok=True)
 plan=json.loads(plan_path.read_text());old=RootedFloorCartoonHead();new=PhoneTongueCartoonHead()
 if drawn_dental:
  from drawn_dental_cartoon_head import DrawnDentalCartoonHead
  new=DrawnDentalCartoonHead()
 new.capture_tongue=True
 with wave.open(str(wav_path)) as f:
  rate=f.getframerate();assert f.getnchannels()==1 and f.getsampwidth()==2;x=np.frombuffer(f.readframes(f.getnframes()),'<i2')
 chunks=[];rows=[];index=0
 for lo,hi,label in RANGES:
  chunks.append(x[round(lo/48*rate):round(hi/48*rate)])
  for i in range(lo,hi):
   t=i/48;a=old.at(t,plan);new.last_tongue=None;b=new.at(t,plan)
   canvas=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(canvas)
   d.text((35,18),'L / dental tongue construction study',font=font(26),fill='#253c49')
   d.text((35,62),'Current raised blade',font=font(20),fill='#48636d');d.text((680,62),('Separate dental drawing / contact — STUDY' if drawn_dental else 'Flatter dental deformation — UNAPPROVED'),font=font(20),fill='#48636d')
   canvas.paste(a,(55,80),a);canvas.paste(b,(700,80),b)
   d.text((35,594),f'{label} | original source {t:.4f}s | no retiming',font=font(20),fill='#48636d')
   left,right,cy=35,1245,652;d.line((left,cy,right,cy),fill='#a9bbb6')
   for px in range(left,right):
    start=round((lo+(hi-lo)*(px-left)/(right-left))/48*rate);end=max(start+1,round((lo+(hi-lo)*(px+1-left)/(right-left))/48*rate))
    peak=float(np.max(np.abs(x[start:end].astype(float))))/32768;h=peak*25;d.line((px,cy-h,px,cy+h),fill='#48636d')
   cx=left+(right-left)*(i-lo)/(hi-lo);d.line((cx,625,cx,678),fill='#be6845',width=2)
   phones=[p for p in plan['phonemes'] if p['end']>lo/48 and p['start']<hi/48]
   for p in phones:
    xx=left+(right-left)*((p['start']+p['end'])/2-lo/48)/((hi-lo)/48)
    d.text((max(left,min(right-35,xx-12)),685),p['phone'],font=font(16),fill='#48636d')
   canvas.save(frames/f'{index:06}.png')
   changed=np.any(np.asarray(a)!=np.asarray(b),axis=2)
   rows.append(dict(frame=index,sourceFrame=i,sourceTime=t,dentalFraction=dental_fraction(t,plan),changedHeadPixels=int(changed.sum()),tongue=new.last_tongue))
   index+=1
  print(f'{label}: {index} frames',flush=True)
 with wave.open(str(out/'Excerpt-Audio.wav'),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes(np.concatenate(chunks).tobytes())
 code=Path(__file__).parent
 report=dict(fps=48,frames=index,ranges=RANGES,planSha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),sourceAudioSha256=hashlib.sha256(wav_path.read_bytes()).hexdigest(),codeSha256={n:hashlib.sha256((code/n).read_bytes()).hexdigest() for n in ['phone_tongue_cartoon_head.py','rooted_floor_cartoon_head.py','render_phone_tongue_study.py']+(['drawn_dental_cartoon_head.py'] if drawn_dental else [])},fvFallbacks=new.fv_correspondence_fallbacks,dentalFallbacks=new.dental_fallbacks,roundedFallbacks=new.contour_fallbacks,animationReady=False,profile='drawn-dental' if drawn_dental else 'flattened-blade',dentalMorphFallbacks=getattr(new,'dental_morph_fallbacks',0),limits='Head panels at native512px. Three discontinuous0.5s excerpts. Optional registered dental-source/edge-contact study; no anatomical, listening or continuous-playback acceptance.' if drawn_dental else 'Head panels at native512px. Three discontinuous0.5s excerpts. Geometry study only: dental blade largely hidden by floor; no distinct new source drawing or protruding tongue. No listening/continuous-playback acceptance.',rows=rows)
 if drawn_dental:
  from cartoon_body import ROOT
  report['assetSha256']={str(n):hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in [Path('dental-tongue-v1/tip.png'),Path('dental-tongue-v1/source/dental-tip-v1.png'),Path('dental-tongue-v1/tip.json')]}
 (out/'Articulation-Audit.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('out',type=Path);p.add_argument('--drawn-dental',action='store_true');a=p.parse_args();run(a.plan,a.wav,a.out,a.drawn_dental)
