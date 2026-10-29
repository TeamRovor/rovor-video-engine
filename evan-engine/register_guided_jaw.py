"""Reproduce source-canvas placement and static assembly failure diagnostics.

Run from the repository root. Outputs are review-only. No source alpha cleanup,
correspondence-fitting, default renderer integration or overlap repair.
"""
from pathlib import Path
import argparse,hashlib,json,cv2,numpy as np
from PIL import Image,ImageDraw
from render_cartoon_head_study import font
from maxillary_cartoon_head import MaxillaryCartoonHead
cv2.setNumThreads(1);parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
raw=np.array(Image.open(args.source).convert('RGBA'));h,w=raw.shape[:2]
# Fixed canvas registration: no fit to pixel bounding boxes or alpha cleanup.
mat=np.array([[256/w,0,128],[0,160/h,288]],np.float32);assoc=raw.astype('float32');assoc[:,:,:3]*=assoc[:,:,3:4]/255
part=cv2.warpAffine(assoc,mat*3,(1536,1536),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);part=cv2.resize(part,(512,512),interpolation=cv2.INTER_AREA)
straight=part.copy();straight[:,:,:3]*=255/np.maximum(straight[:,:,3:4],1);straight=np.rint(np.clip(straight,0,255)).astype('uint8');Image.fromarray(straight).save(out/'Registered-Jaw-v2.png')
plan=json.loads(args.plan.read_text());head=MaxillaryCartoonHead();reference=head.at(741/48,plan)
# Explicit placeholder cut from the CURRENT face, not an artist-painted
# complementary upper face/neck. Any exposed gap is a failure to review.
polygon=np.array([(164,315),(181,320),(194,325),(211,327),(228.5,328.5),(246,327),(263,325),(298,321),(329,320),(328,355),(304,360),(278,372),(245,389),(220,394),(195,391),(181,375),(164,335)],np.float32)
mask=np.zeros((1536,1536),np.uint8);cv2.fillPoly(mask,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8);mask=cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA)
carrier=np.array(reference);carrier[:,:,3]=np.rint(carrier[:,:,3]*(1-mask/255)).astype('uint8')
assembly=Image.fromarray(carrier);assembly.alpha_composite(Image.fromarray(straight));assembly.save(out/'Static-Assembly-TEST.png')
checker=Image.new('RGBA',(512,512));d=ImageDraw.Draw(checker)
for y in range(0,512,16):
 for x in range(0,512,16):d.rectangle((x,y,x+15,y+15),fill='#ecdfc3' if (x//16+y//16)%2 else '#ffffff')
checker.alpha_composite(assembly)
sheet=Image.new('RGB',(1600,880),'#f3eee2');d=ImageDraw.Draw(sheet)
for i,(label,img) in enumerate([('Current reference',reference),('Cut carrier + new jaw / TEST',assembly),('Alpha / overlap inspection',checker)]):
 bg=Image.new('RGBA',(512,512),'#f3eee2');bg.alpha_composite(img);sheet.paste(bg.convert('RGB'),(10+i*530,60));d.text((20+i*530,20),label,font=font(22),fill='#253c49');crop=bg.crop((150,307,342,415)).resize((384,216),Image.Resampling.NEAREST);sheet.paste(crop.convert('RGB'),(65+i*530,600))
d.text((20,842),'Placeholder face partition only: no upper-face/neck overlap drawing or motion acceptance.',font=font(24),fill='#253c49');sheet.save(out/'Static-Assembly-Review.png')
# Native silhouette landmarks, authored guide samples; use threshold only to
# measure contours, never change source paint/alpha.
a=straight[:,:,3];samples=[]
for x,y,label in [(194,325,'left lip corner'),(228,329,'lower lip center'),(263,325,'right lip corner'),(220,394,'chin')]:
 ys=np.where(a[:,x]>=128)[0];actual=int(ys.max()) if label=='chin' else int(ys.min());samples.append(dict(anchor=label,x=x,targetY=y,actualAlphaEdgeY=actual,residualY=actual-y))
(out/'Canvas-Registration-Audit.json').write_text(json.dumps(dict(source=str(args.source),sourceSha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),sourceSize=[w,h],nativeWorkWindow=[128,288,384,448],matrix=mat.tolist(),axisScaleRatio=float(mat[0,0]/mat[1,1]),sourceAlphaModified=False,canvasPlacementOnly=True,edgeSamples=samples,carrierPartition='explicit guide polygon; NOT painted overlap layers',assemblyReady=False,defaultProfileChanged=False,animationReady=False),indent=2)+'\n')
print(samples)
