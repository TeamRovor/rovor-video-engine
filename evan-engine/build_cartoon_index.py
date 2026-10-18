"""Split the original index and register a coherent hidden-palm drawing."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT

def build(root=ROOT):
    original=root/'hand-source/right-point-v1.png';hidden=root/'index-source/hidden-palm-v1.png'
    base=np.asarray(Image.open(original).convert('RGBA'));height,width=base.shape[:2]
    raw=np.asarray(Image.open(hidden).convert('RGBA').resize((width,height),Image.Resampling.LANCZOS))
    def gray(a):
        visible=a[:,:,:3].astype(float)*a[:,:,3:4]/255+243*(1-a[:,:,3:4]/255)
        return cv2.cvtColor(visible.astype('float32'),cv2.COLOR_RGB2GRAY)/255
    mask=np.zeros((height,width),np.uint8);mask[100:600,100:650]=255
    score,m=cv2.findTransformECC(gray(base),gray(raw),np.eye(2,3,dtype='float32'),cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,250,1e-6),mask,5)
    if score<.96 or np.max(abs(m[:,:2]-np.eye(2)))>.04:raise ValueError(f'Hidden palm registration rejected: score={score}; matrix={m.tolist()}')
    placed=cv2.warpAffine(raw,m,(width,height),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    pivot=np.array([807.,749.]);axis=np.array([288.,310.]);axis/=np.linalg.norm(axis);normal=np.array([-axis[1],axis[0]])
    yy,xx=np.mgrid[:height,:width];s=(xx-pivot[0])*axis[0]+(yy-pivot[1])*axis[1];q=(xx-pivot[0])*normal[0]+(yy-pivot[1])*normal[1]
    select=(s>=-45)&(q>=-90)&(q<=np.clip(45+(s-150)*.6,45,85))
    index=base.copy();index[:,:,3][~select]=0
    # Use the coherent hidden-palm drawing below the wrist, rather than
    # cutting a rectangular patch through thumb/curled-finger outlines.
    palm=placed.copy();palm[:520]=base[:520]
    weight=np.linspace(0,1,40)[:,None,None]
    old=base[520:560].astype(float);new=placed[520:560].astype(float)
    old[:,:,:3]*=old[:,:,3:4]/255;new[:,:,:3]*=new[:,:,3:4]/255
    blend=old*(1-weight)+new*weight;blend[:,:,:3]*=255/np.maximum(blend[:,:,3:4],1)
    palm[520:560]=np.clip(blend,0,255).astype('uint8')
    out=root/'index-rig';out.mkdir(exist_ok=True)
    Image.fromarray(index).save(out/'index-source.png');Image.fromarray(palm).save(out/'palm-source.png')
    meta=json.loads((root/'hand-rig/manifest.json').read_text());matrix=np.asarray(meta['matrix'],np.float32)
    a=palm.astype('float32');a[:,:,:3]*=a[:,:,3:4]/255;a=cv2.warpAffine(a,matrix,(1024,1536),flags=cv2.INTER_CUBIC);a[:,:,:3]*=255/np.maximum(a[:,:,3:4],1)
    yy,xx=np.mgrid[:1536,:1024];direction=np.array([61,137])/np.linalg.norm([61,137]);distance=(xx-810)*direction[0]+(yy-762)*direction[1];a[:,:,3]*=np.clip((distance+18)/6,0,1)
    Image.fromarray(np.clip(a,0,255).astype('uint8')).save(out/'palm.png')
    report=dict(animationReady=False,sourceHashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (original,hidden)},registration=dict(ecc=float(score),hiddenCorrection=m.tolist(),sourceToBody=matrix.tolist()),joints=[[807,749],[938,904],[1026,998]],axis=axis.tolist(),palmTransitionRows=[520,560],indexAngleLimits=[[-10,0],[0,60],[0,35]],skinningBlendWidths=[160,130],limitations=['Only the index has independent phalange controls; three fingers and thumb remain one drawing','Bending a straight drawing cannot supply artist-designed folded creases','Thin hand outline and wrist join still need cleanup'])
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
    cv2.setNumThreads(1);print(json.dumps(build()))
