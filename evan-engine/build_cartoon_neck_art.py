"""Register generated hidden neck artwork; never replace the original face."""
import hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT

def build(root=ROOT):
    src=root/'neck-source/extended-neck-v1.png';base=np.asarray(Image.open(root/'head-rig-v2/head-X.png').convert('RGBA'));raw=np.asarray(Image.open(src).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS))
    def gray(a):
        visible=a[:,:,:3].astype(float)*a[:,:,3:4]/255+243*(1-a[:,:,3:4]/255)
        return cv2.cvtColor(visible.astype('float32'),cv2.COLOR_RGB2GRAY)/255
    mask=np.zeros((512,512),np.uint8);mask[90:300,130:390]=255
    score,matrix=cv2.findTransformECC(gray(base),gray(raw),np.eye(2,3,dtype='float32'),cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,250,1e-6),mask,5)
    if score<.96 or np.max(abs(matrix[:,:2]-np.eye(2)))>.1:raise ValueError('Head registration changed too much')
    art=cv2.warpAffine(raw,matrix,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    # Only hidden neck pixels are consumed. The generated face is discarded.
    yy,xx=np.mgrid[:512,:512];art[:,:,3][(yy<380)|(xx<195)|(xx>355)]=0
    output=root/'neck-art-rig';output.mkdir(exist_ok=True)
    Image.fromarray(art).save(output/'neck.png')
    meta=dict(animationReady=False,sourceSha256=hashlib.sha256(src.read_bytes()).hexdigest(),registration=dict(ecc=float(score),matrix=matrix.tolist()),generatedFaceUsed=False,limitations=['2D head tilt only; no perspective turn','Collar and jaw overlap require assembled visual review'])
    # Register only a local collar redraw, preserving remote torso pixels.
    torso=np.asarray(Image.open(root/'socket-rig/torso.png').convert('RGBA'))
    target=torso[260:440,350:650].copy()
    collar_src=root/'neck-source/collar-empty-v1.png'
    collar=np.asarray(Image.open(collar_src).convert('RGBA').resize((300,180),Image.Resampling.LANCZOS))
    cmask=np.zeros((180,300),np.uint8);cmask[80:,:90]=255;cmask[80:,240:]=255;cmask[145:]=255
    cs,cm=cv2.findTransformECC(gray(target),gray(collar),np.eye(2,3,dtype='float32'),cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,250,1e-6),cmask,5)
    if cs<.95 or np.max(abs(cm[:,:2]-np.eye(2)))>.1:raise ValueError('Collar redraw changes registration')
    aligned=cv2.warpAffine(collar,cm,(300,180),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    yy,xx=np.mgrid[:180,:300];weight=np.minimum.reduce([np.clip((xx-80)/8,0,1),np.clip((240-xx)/8,0,1),np.clip((yy-20)/8,0,1),np.clip((140-yy)/8,0,1)])[:,:,None]
    old=target.astype(float);new=aligned.astype(float)
    old[:,:,:3]*=old[:,:,3:4]/255;new[:,:,:3]*=new[:,:,3:4]/255
    mixed=old*(1-weight)+new*weight;mixed[:,:,:3]*=255/np.maximum(mixed[:,:,3:4],1)
    result=torso.copy();take=weight[:,:,0]>0;result[260:440,350:650][take]=np.clip(mixed[take],0,255).astype('uint8')
    Image.fromarray(result).save(output/'torso.png');Image.fromarray((weight[:,:,0]*255).astype('uint8')).save(output/'collar-patch-mask.png')
    meta['collar']=dict(sourceSha256=hashlib.sha256(collar_src.read_bytes()).hexdigest(),ecc=float(cs),matrix=cm.tolist(),crop=[350,260,650,440],patchBounds=[430,280,590,400])
    meta['spread']=.25
    meta['targetHashes']={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in ['head-rig-v2/head-X.png','socket-rig/torso.png']}
    (output/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':
    cv2.setNumThreads(1);print(json.dumps(build()))
