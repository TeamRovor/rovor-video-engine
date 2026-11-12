"""Hidden forehead skin and original separate eyebrow ink, locally registered."""
import hashlib,json
import cv2
import numpy as np
from PIL import Image
from cartoon_body import ROOT
BOXES={'left':(160,205,217,232),'right':(242,202,324,234)}

def build(root=ROOT):
    base=np.asarray(Image.open(root/'head-rig-v2/head-X.png').convert('RGBA'));source=root/'expression-source/browless-v1.png';raw=np.asarray(Image.open(source).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS))
    visible=base.copy();visible[:,:,:3]=(base[:,:,:3].astype(float)*base[:,:,3:4]/255.+np.array([243,238,226])*(1-base[:,:,3:4]/255.)).astype('uint8')
    gray=lambda a:cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((512,512),np.uint8);mask[75:200,130:390]=255;mask[238:388,140:390]=255
    matrix=np.eye(2,3,dtype='float32');score,matrix=cv2.findTransformECC(gray(visible),gray(raw),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),mask,5)
    if score<.96 or np.max(abs(matrix[:,:2]-np.eye(2)))>.10:raise ValueError('Browless source failed registration')
    registered=cv2.warpAffine(raw,matrix,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    ink=np.zeros((512,512),np.uint8);components={}
    for name,(x0,y0,x1,y1) in BOXES.items():
        dark=(base[y0:y1,x0:x1,:3].max(axis=2)<80).astype('uint8');n,labels,stats,_=cv2.connectedComponentsWithStats(dark);i=1+np.argmax(stats[1:,cv2.CC_STAT_AREA]);select=np.zeros_like(ink);select[y0:y1,x0:x1]=(labels==i)*255;ink=np.maximum(ink,select);components[name]=select
    repair=cv2.GaussianBlur(cv2.dilate(ink,np.ones((5,5),np.uint8)),(7,7),1.4).astype(float)/255;repair=np.maximum(repair,cv2.dilate(ink,np.ones((3,3),np.uint8))/255.)
    skin=(base[:,:,0]>175)&(base[:,:,0]>base[:,:,1]*1.1);allowed=skin|(cv2.dilate(ink,np.ones((3,3),np.uint8))>0);repair*=allowed
    ring=(cv2.dilate(ink,np.ones((11,11),np.uint8))>0)&(cv2.dilate(ink,np.ones((5,5),np.uint8))==0)&skin
    delta=np.median(base[ring,:3].astype(float)-registered[ring,:3].astype(float),axis=0);corrected=np.clip(registered[:,:,:3].astype(float)+delta,0,255)
    clean=base.copy();clean[:,:,:3]=np.clip(base[:,:,:3]*(1-repair[:,:,None])+corrected*repair[:,:,None],0,255).astype('uint8')
    output=root/'expression-rig';output.mkdir(exist_ok=True);Image.fromarray(clean).save(output/'browless-head.png');Image.fromarray(np.rint(repair*255).astype('uint8')).save(output/'repair-mask.png')
    for name,select in components.items():
        support=cv2.dilate(select,np.ones((3,3),np.uint8))/255.;pigment=np.array([18,13,10]);direction=np.maximum(corrected-pigment,1);alpha=np.clip(((corrected-base[:,:,:3])*direction).sum(axis=2)/np.maximum((direction*direction).sum(axis=2),1),0,1)*support
        rgb=np.clip((base[:,:,:3]-(1-alpha[:,:,None])*corrected)/np.maximum(alpha[:,:,None],.01),0,255);layer=np.dstack((rgb,alpha*255)).astype('uint8');layer[layer[:,:,3]==0,:3]=0;Image.fromarray(layer).save(output/f'brow-{name}.png')
    occlude=((clean[:,:,0]>175)&(clean[:,:,0]>clean[:,:,1]*1.1)).astype('uint8')*255;roi=np.zeros_like(occlude);roi[180:239,150:335]=1;occlude*=roi;Image.fromarray(occlude).save(output/'forehead-mask.png')
    report=dict(version=1,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),registration=dict(ecc=float(score),matrix=matrix.tolist(),skinOffset=delta.tolist()),pivots=dict(left=[188,220],right=[280,219]),animationReady=False,limitations=['Only original brow drawings are articulated; eyes remain hidden by sunglasses','Hair/glasses clip brow excursion','Skin repair and brow edges need full-resolution review'])
    (output/'manifest.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(build(),indent=2))
