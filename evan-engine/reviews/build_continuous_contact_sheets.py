from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[4];out=root/'outputs/evan-cartoon-continuous';frames=out/'Frames'
markers=json.loads((out/'Timing-Markers.json').read_text())['markers'];assert len(markers)==18
sheet=Image.new('RGB',(840,960),'#eee8dd');d=ImageDraw.Draw(sheet);rows=[]
for k,w in enumerate(markers):
 x=k%3*280;y=k//3*160;d.text((x+4,y+2),f'{w["scriptIndex"]}: {w["word"]}',fill='#233442');row=dict(word=w['word'],scriptIndex=w['scriptIndex'],frames=[])
 for j,key in enumerate(['acoustic','anchor']):
  t=sum(w[key])/2;n=round(t*24);p=frames/f'{n:06}.png';im=Image.open(p)
  crop=(140,225,255,280) if n>=532 else (230,135,350,215)
  sheet.paste(im.crop(crop),(x+4+j*136,y+38));d.text((x+4+j*136,y+20),f'{key} {t:.3f}',fill='#233442')
  row['frames'].append(dict(hypothesis=key,midpoint=t,sampledFrame=n,sampledTime=n/24,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 rows.append(row)
sheet.save(out/'Flagged-Word-Pose-Pairs.png')
for first in [0,192,384]:
 sheet=Image.new('RGB',(1280,800),'#eee8dd');d=ImageDraw.Draw(sheet)
 for k,n in enumerate(range(first,min(first+192,552),24)):
  x=k%2*640;y=k//2*200;im=Image.open(frames/f'{n:06}.png');sheet.paste(im.resize((320,180)),(x,y+20));d.text((x+4,y+2),f'{n/24:.2f}s',fill='#233442')
  box=(140,225,255,280)if n>=532 else(230,135,350,215);sheet.paste(im.crop(box),(x+350,y+45))
 sheet.save(out/f'Acting-Overview-{first}.png')
(out/'Contact-Sheet-Provenance.json').write_text(json.dumps(dict(markers=rows,flagCount=18,flagsCleared=0,reviewStatus='visual-sampling-only'),indent=2)+'\n');print('18 timing pose pairs and three acting overview sheets saved')
