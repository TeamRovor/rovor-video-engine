"""Register generated oral art as separate cavity/rim and an occlusion matte."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from layered_cartoon_head import ROOT,straight
from bounded_cartoon_head import bounded_premultiplied

def build(root=ROOT):
    path=root/'round-source-v1/rounded-mouth-v2.png';raw=np.asarray(Image.open(path).convert('RGBA')).copy()
    # The generated PNG's intended solid fill is mostly alpha 253. Preserve
    # its antialiased silhouette, but make near-solid working art truly opaque.
    raw[raw[:,:,3]>=250,3]=255
    y,x=np.where(raw[:,:,3]>128);bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
    sx=29/(bounds[2]-bounds[0]);sy=46/(bounds[3]-bounds[1]);matrix=np.array([[sx,0,211-sx*bounds[0]],[0,sy,320-sy*bounds[1]]],np.float32)
    r,g,b,a=[raw[:,:,i].astype(float) for i in range(4)]
    seed=((a>200)&(r>30)&(r<180)&(g<90)&(r>g*1.4)&(b<100)).astype('uint8')
    n,labels,stats,_=cv2.connectedComponentsWithStats(seed)
    if n<2:raise ValueError('Missing cavity fill')
    mask=(labels==1+np.argmax(stats[1:,cv2.CC_STAT_AREA])).astype('uint8')*255
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);mask[:]=0;cv2.drawContours(mask,contours,-1,255,-1)
    inside=mask>0;underlap=cv2.dilate(mask,np.ones((25,25),np.uint8))>0
    cavity=raw.copy();cavity[~underlap]=0;rim=raw.copy();rim[inside]=0
    matte=np.zeros_like(raw);matte[:,:,3]=mask
    def register(art):
        p=art.astype('float32');p[:,:,:3]*=p[:,:,3:4]/255
        p=cv2.warpAffine(p,matrix*4,(2048,2048),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        p=bounded_premultiplied(cv2.resize(p,(512,512),interpolation=cv2.INTER_AREA))
        return np.rint(straight(p)).astype('uint8')
    folder=root/'round-rig-v1';folder.mkdir(exist_ok=True)
    for name,art in [('cavity',cavity),('rim',rim),('interior-mask',matte),('whole-reference',raw)]:
        result=register(art);result[result[:,:,3]==0,:3]=0;Image.fromarray(result).save(folder/f'{name}.png')
    report=dict(version=1,sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),sourceBounds=bounds,matrix=matrix.tolist(),sourceGeometry='E',targetBounds=[211,320,240,366],registration='authored affine fit to existing E control space; not anatomical calibration',alphaSnapThreshold=250,underlapSourcePixels=12,supersample=4,components=['cavity','rim'],mask='interior-mask',animationReady=False,limitations=['Rounded-art candidate; source plate is not a complete rig','Canonical source controls are authored, not traced anatomical landmarks','Shallow contacts and dental tongue shapes remain separate unfinished work'])
    report['generationMode']='built-in imagegen'
    report['contextReference']='source/design-sheet-v1.png'
    report['contextSha256']=hashlib.sha256((root/report['contextReference']).read_bytes()).hexdigest()
    report['editReferenceSha256']=hashlib.sha256((root/'round-source-v1/old-mouth-reference.png').read_bytes()).hexdigest()
    report['promptSha256']={name:hashlib.sha256((root/'round-source-v1'/name).read_bytes()).hexdigest() for name in ['generation-v1.txt','contour-edit.txt']}
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':cv2.setNumThreads(1);print(json.dumps(build(),indent=2))
