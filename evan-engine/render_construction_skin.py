"""Optional skin-only integration test; existing lip/jaw artwork stays in use."""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from rounded_duration_cartoon_head import RoundedDurationCartoonHead
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from render_cartoon_head_study import font
if __name__=='__main__':
 cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('audit',type=Path);p.add_argument('--start',type=int,default=714);p.add_argument('--end',type=int,default=774);a=p.parse_args();plan=json.loads(a.plan.read_text());old=RoundedDurationCartoonHead();new=ConstructionSkinCartoonHead();a.frames.mkdir(parents=True,exist_ok=True);rows=[]
 for i in range(a.start,a.end):
  t=i/48;x=old.at(t,plan);y=new.at(t,plan);xx=np.array(x);yy=np.array(y);np.testing.assert_array_equal(xx[:290],yy[:290]);np.testing.assert_array_equal(xx[:,:,3],yy[:,:,3]);delta=abs(xx.astype(int)-yy.astype(int));im=Image.new('RGB',(1280,720),'#f3eee2');d=ImageDraw.Draw(im);d.text((35,20),'Skin underpainting integration / existing oral art and timing',font=font(27),fill='#253c49');d.text((35,65),'Current working skin',font=font(21),fill='#48636d');d.text((680,65),'Registered clean skin — OPTIONAL',font=font(21),fill='#48636d');im.paste(x,(55,95),x);im.paste(y,(700,95),y);d.text((35,625),f'Original voice / source {t:.4f}s',font=font(22),fill='#48636d');d.text((35,670),'Skin component test only: old seal/release defect remains; new lip/interior/jaw layers still needed.',font=font(20),fill='#48636d');im.save(a.frames/f'{i:06}.png');rows.append(dict(sourceFrame=i,time=t,changedHeadPixels=int(np.any(delta,axis=2).sum()),maxChannelDifference=int(delta.max())))
  if len(rows)%12==0:print(f'{a.start}: {len(rows)}',flush=True)
 code=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();root=code.parent/'evan-character/cartoon-v1';a.audit.write_text(json.dumps(dict(rows=rows,fps=48,width=1280,height=720,sourceStart=a.start,sourceEndExclusive=a.end,planSha256=sha(a.plan),codeSha256={n:sha(code/n) for n in ['build_construction_skin.py','construction_skin_cartoon_head.py','render_construction_skin.py']},workingSkinSha256=sha(root/'construction-skin-v1/working-face-skin.png'),upper290RowsExact=True,alphaExact=True,oralArtworkChanged=False,phonemeTimingChanged=False,animationReady=False,fallbacks=dict(dentalMorph=new.dental_morph_fallbacks,fv=new.fv_correspondence_fallbacks,dental=new.dental_fallbacks,rounded=new.contour_fallbacks)),indent=2)+'\n')
