from pathlib import Path
import json,hashlib,shutil,subprocess,sys
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[4];repo=root/'work/engine';out=root/'outputs/evan-cartoon-clean-palm-continuous';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();audit=json.loads((out/'Render-Audit.json').read_text());rows=audit['rows'];assert len(rows)==532 and [r['sourceFrame']for r in rows]==list(range(532))
journal=[json.loads(s)for s in (out/'Frame-Audit.jsonl').read_text().splitlines()];assert journal==rows
for name,digest in json.loads((out/'Frame-Hashes.json').read_text()).items():assert sha(out/'Frames'/name)==digest
baseline=root/'outputs/evan-cartoon-dismissive-acting';v=json.loads((out/'Verification.json').read_text());previous=json.loads((baseline/'Verification.json').read_text());assert v['sourcePlanSha256']==previous['sourcePlanSha256']
assert sha(baseline/'Normal.mp4')==previous['films']['Normal.mp4']['sha256']
ff=root.parent/'referenced-chatgpt-conversation-this-is-an/work/media-tools/ffmpeg'
for name,indices in [('Normal',[69,276,374,540]),('Quarter-Speed',[276,1496])]:
 select="select='"+('+'.join('eq(n,'+str(n)+')'for n in indices))+"'";subprocess.run([str(ff),'-v','error','-nostdin','-y','-i',str(out/(name+'.mp4')),'-vf',select,'-fps_mode','passthrough',str(out/('Encoded-'+name+'-%02d.png'))],check=True)
 for k in range(1,len(indices)+1):assert Image.open(out/f'Encoded-{name}-{k:02}.png').size==(1280,720)
# Uniform sampling plus every control extremum and both sides of major accents.
selected=sorted(set(range(0,532,8))|{0,42,43,60,66,68,69,70,71,72,74,76,124,130,138,148,156,168,178,234,235,246,248,276,324,336,348,350,355,360,368,374,380,384,396,402,403,444,456,480,504,510,516,528,531})
for start in range(0,len(selected),12):
 sheet=Image.new('RGB',(1110,1384),'#eee8dd');d=ImageDraw.Draw(sheet)
 for j,n in enumerate(selected[start:start+12]):
  im=Image.open(out/'Native'/f'{n:06}.png');assert im.size==(370,330);x=j%3*370;y=j//3*346;sheet.paste(im,(x,y+16),im);d.text((x+3,y+2),f'{n} {n/24:.3f}s',fill='#233442')
 sheet.save(out/f'Native-Samples-{start}.png')
overview=sorted(set(range(0,552,24))|{60,69,70,138,248,276,348,374,384,444,510,531,532,540,551})
for start in range(0,len(overview),9):
 sheet=Image.new('RGB',(1280,780),'#eee8dd');d=ImageDraw.Draw(sheet)
 for j,n in enumerate(overview[start:start+9]):
  im=Image.open(out/'Frames'/f'{n:06}.png');im.thumbnail((426,240),Image.Resampling.LANCZOS);x=j%3*426;y=j//3*260;sheet.paste(im,(x,y+18));d.text((x+3,y+3),f'{n} {n/24:.3f}s',fill='#233442')
 sheet.save(out/f'Overview-{start}.png')
(out/'Contact-Sheet-Provenance.json').write_text(json.dumps(dict(nativeSamples=selected,nativeCount=len(selected),overviewFrames=overview,overviewCount=len(overview),selection='Uniform 1/3s plus controls extrema and accent entry/exit; sampled inspection, not all532 native frames'),indent=2)+'\n')
subprocess.run([sys.executable,str(repo/'evan-engine/reviews/build_continuous_review_page.py'),'evan-cartoon-clean-palm-continuous'],check=True)
p=out/'Review.html';s=p.read_text().replace('<h1>Evan continuous cartoon review</h1>','<h1>Evan: cleaner hand in the full cartoon review</h1><p>The calibrated open palm now runs through all532speech frames. Skeptical brows, the left negation sweep, the right definition gesture and all20closing frames are retained. Fingers remain a fixed drawing; source edge stippling, cuff folds and restrained face/body acting remain below the polished milestone.</p><p><a href="../evan-cartoon-dismissive-acting/Review.html">Previous full-length candidate</a> · <a href="../evan-cartoon-clean-open-palm/Review.html">Registered hand source and component review</a></p>');p.write_text(s)
source=out/'Source';source.mkdir(exist_ok=True);manifest={}
for f in ['render_clean_palm_continuous.py','build_clean_palm_continuous_review.py']:
 p=Path(__file__).parent/f;shutil.copy2(p,source/f);manifest[str(p.relative_to(root))]=sha(p)
for f in ['relaxed_cartoon_scene.py','dismissive_cartoon_review.py','painted_character.py','cartoon_hand.py','finished_cartoon_scene.py','reviews/build_continuous_review_page.py','reviews/render_clean_palm_continuous.py','reviews/build_clean_palm_continuous_review.py','reviews/trace_clean_palm_outline.py']:
 p=repo/'evan-engine'/f;shutil.copy2(p,source/p.name);manifest[str(p.relative_to(root))]=sha(p)
for f in ['outputs/evan-cartoon-dismissive-acting/Verification.json','outputs/evan-cartoon-clean-open-palm/Verification.json','outputs/evan-speech-alignment/Aligned-Speech-Plan.json','work/engine/evan-character/cartoon-v1/open-palm-clean-v1/source-v2.png','work/engine/evan-character/cartoon-v1/open-palm-clean-v1/right-skin.png','work/engine/evan-character/cartoon-v1/open-palm-clean-v1/manifest.json']:
 p=root/f;manifest[f]=sha(p)
(out/'Source-Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('Native sample count',len(selected),'overview count',len(overview),'and18timing markers retained')
