"""Original voiced rig beside static construction references, never head swaps."""
import argparse,json,hashlib
from pathlib import Path
import cv2
from PIL import Image,ImageDraw
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('construction',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text());head=RoundedDurationCartoonHead();a.frames.mkdir(parents=True,exist_ok=True);refs=[Image.open(a.construction/f'{n}-Aligned.png').convert('RGBA') for n in ['Seal','Release','Rounded']];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[]
 for i in range(714,774):
  t=i/48;im=Image.new('RGB',(2160,720),'#f3eee2');d=ImageDraw.Draw(im)
  for x,label,art in [(15,'Working rig / original voice',head.at(t,plan))]+[(545+j*530,n+' drawing / STATIC SOURCE',r) for j,(n,r) in enumerate(zip(['Seal','Release','Rounded'],refs))]:
   d.text((x+10,25),label,font=font(23),fill='#253c49');im.paste(art,(x,90),art)
  word=next((w['word'] for w in plan['words'] if w['start']<=t<w['end']),'pause');phone=next((q['phone'] for q in plan['phonemes'] if q['start']<=t<q['end']),'pause')
  d.text((25,620),f'Original source {t:.4f}s | {word} | phone label {phone} (unverified)',font=font(23),fill='#48636d');d.text((25,665),'SOURCE CONSTRUCTION REVIEW: right-hand drawings are static; no candidate lip-sync, no full-head swaps, no rig promotion.',font=font(23),fill='#48636d');im.save(a.frames/f'{i:06}.png');rows.append(dict(sourceFrame=i,time=t,word=word,phone=phone))
  if len(rows)%12==0:print(len(rows),flush=True)
 a.audit.write_text(json.dumps(dict(rows=rows,fps=48,width=2160,height=720,sourceHead='working RoundedDuration unchanged',candidateAnimation=False,staticSourceDrawings=True,planSha256=sha(a.plan),codeSha256={n:sha(Path(__file__).parent/n) for n in ['render_construction_review.py','audit_cartoon_construction.py']},constructionAuditSha256=sha(a.construction/'Construction-Audit.json'),fallbacks=dict(dentalMorph=head.dental_morph_fallbacks,fv=head.fv_correspondence_fallbacks,dental=head.dental_fallbacks,rounded=head.contour_fallbacks)),indent=2)+'\n')
