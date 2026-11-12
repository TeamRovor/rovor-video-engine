"""Separate v2 static eye/glasses matte; v1 and full-film defaults stay preserved."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image
cv2.setNumThreads(1)
root=Path(__file__).resolve().parents[3];repo=root/'work/engine';source=repo/'evan-character/cartoon-v1/eye-underlay-v1';folder=repo/'evan-character/cartoon-v1/eye-underlay-v2';folder.mkdir(exist_ok=True);out=root/'outputs/evan-cartoon-eye-matte';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=np.array(Image.open(repo/'evan-character/cartoon-v1/expression-rig/browless-head.png').convert('RGBA'));meta=json.loads((source/'manifest.json').read_text());b=np.array(Image.open(source/'source/glasses-free-v1.png').convert('RGBA').resize((512,512),Image.Resampling.LANCZOS));b=cv2.warpAffine(b,np.array(meta['matrix'],np.float32),(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT);b[:,:,:3]=np.clip(b[:,:,:3].astype(float)+meta['skinOffset'],0,255).astype('uint8');oldmask=np.array(Image.open(source/'ownership.png'))>0;yy,xx=np.mgrid[:512,:512]
patch=cv2.dilate(oldmask.astype('uint8'),np.ones((15,15),np.uint8))>0
strap=np.zeros((512,512),np.uint8);cv2.fillPoly(strap,[np.array([(326,239),(358,257),(364,265),(350,272),(327,257)],np.int32)],255);strap=strap>0
hair=(xx>=327)&~strap&(a[:,:,0]<140)&(a[:,:,1]<95)&(a[:,:,2]<65)
patch|=strap
patch&=(yy>=222)&(yy<302)&~hair;patch[(xx>196)&(xx<242)&(yy>=294)]=False
valid=patch&(a[:,:,3]>250)&(b[:,:,3]>250);m=valid.astype('uint8')*255
x,y,w,h=cv2.boundingRect(m);repaired=cv2.seamlessClone(b[:,:,:3],a[:,:,:3],m,(x+w//2,y+h//2),cv2.NORMAL_CLONE)
u=a.copy();u[valid,:3]=repaired[valid]
hidden_hair=cv2.inpaint(a[:,:,:3],strap.astype('uint8')*255,7,cv2.INPAINT_TELEA);u[strap,:3]=hidden_hair[strap]
# The old lens extends beyond the skin silhouette; retain the generated skin edge.
edge=patch&(b[:,:,3]<=250)&(xx<175);u[edge]=b[edge]
# Only the original glasses core owns opaque material. Skin and nose stay underneath.
core=cv2.erode(oldmask.astype('uint8'),np.ones((5,5),np.uint8))>0
core|=cv2.erode(strap.astype('uint8'),np.ones((3,3),np.uint8))>0
core[hair]=False
core[(xx>196)&(xx<242)&(yy>=294)]=False
band=(cv2.dilate(core.astype('uint8'),np.ones((9,9),np.uint8))>0)&(yy<302)
band|=strap
band[hair]=False
band[(xx>196)&(xx<242)&(yy>=294)]=False
_,labels=cv2.distanceTransformWithLabels((~core).astype('uint8'),cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
lookup=np.zeros((int(labels.max())+1,3),np.float32);lookup[labels[core]]=a[core,:3];f=lookup[labels];assert np.array_equal(f[core],a[core,:3]);background=u[:,:,:3].astype('float32');observed=a[:,:,:3].astype('float32');delta=f-background
alpha=np.clip(np.sum((observed-background)*delta,axis=2)/np.maximum(np.sum(delta*delta,axis=2),1),0,1);alpha[~band]=0;alpha[core]=1
outside=band&(u[:,:,3]<5);alpha[outside]=a[:,:,3][outside]/255;f[outside]=observed[outside]
# Edge RGB comes from nearby original opaque frame pixels, not baked skin.
plane=np.dstack([f,alpha*255]);plane=np.clip(plane,0,255).astype('uint8');plane[plane[:,:,3]==0,:3]=0;assert np.array_equal(plane[core,:3],a[core,:3]) and np.array_equal(plane[core,3],np.where(outside[core],a[core,3],255))
Image.fromarray(u).save(folder/'underlay.png');Image.fromarray(plane).save(folder/'glasses.png');Image.fromarray(m).save(folder/'repair-mask.png')
assert np.array_equal(u[310:],a[310:]);assert not np.any(plane[302:,:,3]);assert np.array_equal(u[~patch],a[~patch])
rows=[]
for amount in [0,12,18,25]:
 weight=np.clip((353-xx)/27,0,1);weight=weight*weight*(3-2*weight);scale=1-.35*amount/25*weight;assert scale.min()>=.65
 mx=xx.astype('float32');my=((yy-245-amount*weight)/scale+245).astype('float32');assert np.array_equal(my[:,353:],yy[:,353:]) and np.array_equal(mx[:,353:],xx[:,353:]);raw=plane.astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
 moved=cv2.remap(raw,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);moved[:,:,:3]*=255/np.maximum(moved[:,:,3:4],1);moved=Image.fromarray(np.clip(moved,0,255).astype('uint8')) if amount else Image.fromarray(plane)
 im=Image.fromarray(u);im.alpha_composite(moved);im.save(out/f'Glasses-{amount:02}.png')
 for name,color in [('Light','#f3eee2'),('Dark','#233442')]:
  bg=Image.new('RGBA',(512,512),color);bg.alpha_composite(im);bg.convert('RGB').save(out/f'{name}-{amount:02}.png')
 rows.append(dict(amount=amount,lensYScale=float(scale.min())))
rest=np.array(Image.open(out/'Glasses-00.png'));diff=np.abs(rest.astype(int)-a.astype(int));outside_diff=np.any(diff>0,axis=2)&~patch;report=dict(status='matte-construction-review-pending',restRgbaExact=bool(np.array_equal(rest,a)),restChangedPixels=int(np.any(diff>0,axis=2).sum()),restMaximumChannelError=int(diff.max()),restOutsidePatchChangedPixels=int(outside_diff.sum()),neutralOriginalMouthJawExact=bool(np.array_equal(rest[310:],a[310:])),repairPixels=int(valid.sum()),corePixels=int(core.sum()),edgePixels=int(((plane[:,:,3]>0)&~core).sum()),staticPoses=rows,rawSourceSha256=sha(source/'source/glasses-free-v1.png'),rawSourceAlphaUnmodified=True,defaultChanged=False,fullFilmUpdated=False,animationReady=False)
(folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(out/'Verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
