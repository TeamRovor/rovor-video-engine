"""Rebuild the separate static eye/glasses construction; assertions guard preserved art."""
from pathlib import Path
import json,hashlib
import cv2,numpy as np
from PIL import Image,ImageDraw
cv2.setNumThreads(1)
root=Path(__file__).resolve().parents[3];repo=root/'work/engine';folder=repo/'evan-character/cartoon-v1/eye-underlay-v1';out=root/'outputs/evan-cartoon-eye-underlay';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
target=repo/'evan-character/cartoon-v1/expression-rig/browless-head.png';raw=folder/'source/glasses-free-v1.png';a=np.array(Image.open(target).convert('RGBA'));b=np.array(Image.open(raw).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS));yy,xx=np.mgrid[:512,:512]
mask=((a[:,:,3]>250)&((yy<220)|((xx>340)&(yy>280)&(yy<330))|((xx>190)&(xx<280)&(yy>345)&(yy<380)))).astype('uint8')*255
m=np.eye(2,3,dtype='float32');ecc,m=cv2.findTransformECC(cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY),cv2.cvtColor(b[:,:,:3],cv2.COLOR_RGB2GRAY),m,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,200,1e-7),mask,5)
b=cv2.warpAffine(b,m,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
patch=(xx>185)&(xx<310)&(yy>209)&(yy<226)&(a[:,:,3]==255)
offset=np.median(a[:,:,:3][patch].astype(float)-b[:,:,:3][patch],axis=0);b[:,:,:3]=np.clip(b[:,:,:3].astype(float)+offset,0,255).astype('uint8');Image.fromarray(b).save(out/'Registered-Source.png')
poly=np.array([(135,236),(157,230),(200,230),(218,237),(241,229),(302,227),(325,236),(331,246),(357,259),(358,272),(346,274),(325,262),(318,285),(306,296),(250,297),(237,286),(228,258),(217,254),(211,279),(202,294),(153,297),(140,285)],np.int32)
roi=np.zeros((512,512),np.uint8);cv2.fillPoly(roi,[poly],255)
core=((cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY)<115)&(a[:,:,:3].max(axis=2)<145)&(roi>0)).astype('uint8')
count,labels,stats,_=cv2.connectedComponentsWithStats(core,8);label=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);core=(labels==label).astype('uint8')*255
flood=core.copy();cv2.floodFill(flood,None,(0,0),255);glass=core|cv2.bitwise_not(flood);glass=cv2.dilate(glass,np.ones((3,3),np.uint8));glass=(glass>0)&(roi>0)&(a[:,:,3]>0)
under=a.copy();under[glass]=b[glass];under[glass&(a[:,:,3]<255),3]=0
plane=np.zeros_like(a);plane[glass]=a[glass];Image.fromarray(under).save(folder/'underlay.png');Image.fromarray(plane).save(folder/'glasses.png');Image.fromarray(glass.astype('uint8')*255).save(folder/'ownership.png')
rest=Image.fromarray(under);rest.alpha_composite(Image.fromarray(plane));assert np.array_equal(np.array(rest),a),'Rest reconstruction drift'
assert np.array_equal(under[~glass],a[~glass]);assert not np.any(glass[310:])
rows=[]
for amount in [0,12,18,25]:
 weight=np.clip((353-xx)/27,0,1);weight=weight*weight*(3-2*weight)
 scale=1-(.35 if amount==25 else 0)*weight;assert scale.min()>=.65
 mx=xx.astype('float32');my=((yy-245-amount*weight)/scale+245).astype('float32');associated=plane.astype('float32');associated[:,:,:3]*=associated[:,:,3:4]/255
 moved=cv2.remap(associated,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT);moved[:,:,:3]*=255/np.maximum(moved[:,:,3:4],1);glasses=Image.fromarray(np.clip(moved,0,255).astype('uint8')) if amount else Image.fromarray(plane)
 im=Image.fromarray(under);im.alpha_composite(glasses);im.save(out/f'Glasses-{amount:02}.png');rows.append(dict(amount=amount,templeAnchorX=353,fullLensThroughX=326,lensYScale=float(scale.min())))
overlay=a.copy();overlay[glass,:3]=(overlay[glass,:3]*.35+np.array([20,220,160])*.65).astype('uint8');Image.fromarray(overlay).save(out/'Ownership-Overlay.png')
report=dict(status='registered-static-construction-review-pending',sourceSha256=sha(raw),targetSha256=sha(target),sourceSize=Image.open(raw).size,sourceAlphaUnmodified=True,ecc=float(ecc),matrix=m.tolist(),skinOffset=offset.tolist(),ownershipPixels=int(glass.sum()),restRgbaExact=True,outsideOwnershipExact=True,workingRegisteredDerivatives=True,animationReady=False,staticPoses=rows,defaultChanged=False,fullFilmUpdated=False)
(folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');(out/'Verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
