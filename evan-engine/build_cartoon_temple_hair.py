"""Build opt-in temple repair; run from the repository with local image dependencies."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image
cv2.setNumThreads(1)
root=Path(__file__).resolve().parents[3];repo=root/'work/engine';art=repo/'evan-character/cartoon-v1';folder=art/'temple-hair-v1';working=art/'eye-underlay-v3';working.mkdir(exist_ok=True);out=root/'outputs/evan-cartoon-temple-hair';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=np.array(Image.open(art/'expression-rig/browless-head.png').convert('RGBA'));u=np.array(Image.open(art/'eye-underlay-v2/underlay.png').convert('RGBA'));plane=np.array(Image.open(art/'eye-underlay-v2/glasses.png').convert('RGBA'));raw=folder/'source/temple-hidden-v1.png';b=np.array(Image.open(raw).convert('RGB').resize((64,76),Image.Resampling.LANCZOS));target=a[220:296,310:374,:3];yy,xx=np.mgrid[:76,:64];anchors=((xx>36)&(yy<20))|((xx>45)&(yy>55))|((xx<12)&(yy>50));matrix=np.eye(2,3,dtype='float32')
ecc,matrix=cv2.findTransformECC(cv2.cvtColor(target,cv2.COLOR_RGB2GRAY),cv2.cvtColor(b,cv2.COLOR_RGB2GRAY),matrix,cv2.MOTION_TRANSLATION,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,150,1e-6),anchors.astype('uint8')*255,3)
ecc_trial=matrix.copy();ecc_rejected=not(np.isfinite(matrix).all() and abs(matrix[:,2]).max()<3)
# shortcut: flat hair makes ECC ambiguous; use authored crop bounds and inspect each new source.
if ecc_rejected:matrix=np.eye(2,3,dtype='float32')
assert np.isfinite(matrix).all() and abs(matrix[:,2]).max()<3,matrix
b=cv2.warpAffine(b,matrix,(64,76),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE);offset=np.median(target[anchors].astype(float)-b[anchors],axis=0);b=np.clip(b.astype(float)+offset,0,255).astype('uint8');Image.fromarray(b).save(out/'Registered-Patch.png')
canvas=u[:,:,:3].copy();canvas[220:296,310:374]=b;mask=np.zeros((512,512),np.uint8);cv2.fillPoly(mask,[np.array([(326,239),(358,257),(364,265),(350,272),(327,257)],np.int32)],255)
mask=cv2.dilate(mask,np.ones((7,7),np.uint8));yy,xx=np.mgrid[:512,:512];ear=(xx>=353)|((xx>=340)&(yy>=np.interp(xx,[340,350,360,374],[280,271,265,263])-1));mask[ear]=0;weight=np.clip(cv2.distanceTransform(mask,cv2.DIST_L2,5)/2,0,1)[:,:,None];new=u.copy();new[:,:,:3]=np.rint(canvas*weight+u[:,:,:3]*(1-weight)).astype('uint8');new[ear]=a[ear];mask[ear&np.any(u!=a,axis=2)]=255;assert np.array_equal(new[ear],a[ear]);assert np.array_equal(new[mask==0],u[mask==0]);assert np.array_equal(new[310:],a[310:])
yy,xx=np.mgrid[:512,:512];oldmask=np.array(Image.open(art/'eye-underlay-v1/ownership.png'))>0;opaque_left=oldmask&(xx<=160)&(yy>=240)&(yy<=288)&(a[:,:,:3].max(axis=2)<100)&(a[:,:,3]>250)
corrected=int(np.any(plane[opaque_left]!=a[opaque_left],axis=1).sum());plane[opaque_left]=a[opaque_left];assert np.array_equal(plane[opaque_left],a[opaque_left])
Image.fromarray(new).save(working/'underlay.png');Image.fromarray(plane).save(working/'glasses.png');Image.fromarray(mask).save(working/'temple-mask.png')
for amount in [0,12,18,25]:
 weight=np.clip((353-xx)/27,0,1);weight=weight*weight*(3-2*weight);scale=1-.35*amount/25*weight;mx=xx.astype('float32');my=((yy-245-amount*weight)/scale+245).astype('float32');associated=plane.astype('float32');associated[:,:,:3]*=associated[:,:,3:4]/255
 moved=cv2.remap(associated,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);moved[:,:,:3]*=255/np.maximum(moved[:,:,3:4],1);moved=Image.fromarray(np.clip(moved,0,255).astype('uint8')) if amount else Image.fromarray(plane)
 im=Image.fromarray(new);im.alpha_composite(moved);im.save(out/f'Glasses-{amount:02}.png')
 for name,color in [('Light','#f3eee2'),('Dark','#233442')]:
  bg=Image.new('RGBA',(512,512),color);bg.alpha_composite(im);bg.convert('RGB').save(out/f'{name}-{amount:02}.png')
report=dict(status='targeted-temple-construction-see-reviews/temple-hair-v1.json',rawSourceSha256=sha(raw),sourceSize=Image.open(raw).size,crop=[310,220,374,296],eccTrialScore=float(ecc),eccTrialMatrix=ecc_trial.tolist(),eccTrialRejected=bool(ecc_rejected),registration='authored crop bounds' if ecc_rejected else 'bounded translation',matrix=matrix.tolist(),colorOffset=offset.tolist(),nativePatchPixels=int((mask>0).sum()),outsideTemplePatchExactToV2=True,neutralOriginalMouthJawExact=True,originalOpaqueOuterCornerPixelsGuarded=int(opaque_left.sum()),outerCornerPixelsCorrected=corrected,animationReady=False,defaultChanged=False,fullFilmUpdated=False)
(working/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(out/'Verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
