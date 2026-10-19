"""Register the lighter mouth source into separate cavity/rim working layers."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from layered_cartoon_head import ROOT,straight
from bounded_cartoon_head import bounded_premultiplied

def build(root=ROOT):
    path=root/'light-lip-source-v1/light-mouth-v2.png'
    raw=np.asarray(Image.open(path).convert('RGBA')).copy()
    raw[raw[:,:,3]>=250,3]=255
    y,x=np.where(raw[:,:,3]>128)
    bounds=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
    sx=29/(bounds[2]-bounds[0]);sy=46/(bounds[3]-bounds[1])
    matrix=np.array([[sx,0,211-sx*bounds[0]],[0,sy,320-sy*bounds[1]]],np.float32)
    r,g,b,a=[raw[:,:,i].astype(float) for i in range(4)]
    seed=((a>200)&(r>55)&(g<65)&(b<75)&(r>g*2)).astype('uint8')
    n,labels,stats,_=cv2.connectedComponentsWithStats(seed)
    if n<2:raise ValueError('Missing burgundy cavity fill')
    mask=(labels==1+np.argmax(stats[1:,cv2.CC_STAT_AREA])).astype('uint8')*255
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    mask[:]=0;cv2.drawContours(mask,contours,-1,255,-1)
    cavity=raw.copy();cavity[cv2.dilate(mask,np.ones((25,25),np.uint8))==0]=0
    rim=raw.copy();rim[mask>0]=0
    matte=np.zeros_like(raw);matte[:,:,3]=mask
    def register(art):
        p=art.astype('float32');p[:,:,:3]*=p[:,:,3:4]/255
        p=cv2.warpAffine(p,matrix*4,(2048,2048),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        p=bounded_premultiplied(cv2.resize(p,(512,512),interpolation=cv2.INTER_AREA))
        result=np.rint(straight(p)).astype('uint8');result[result[:,:,3]==0,:3]=0
        return result
    folder=root/'light-lip-rig-v1';folder.mkdir(exist_ok=True)
    for name,art in [('cavity',cavity),('rim',rim),('interior-mask',matte),('whole-reference',raw)]:
        Image.fromarray(register(art)).save(folder/f'{name}.png')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(version=1,source='light-lip-source-v1/light-mouth-v2.png',sourceSha256=digest(path),sourceBounds=bounds,matrix=matrix.tolist(),sourceGeometry='E',targetBounds=[211,320,240,366],registration='authored affine fit to existing E control space; not anatomical calibration',alphaSnapThreshold=250,underlapSourcePixels=12,supersample=4,components=['cavity','rim'],mask='interior-mask',animationReady=False,generationMode='built-in imagegen')
    report['contextReference']='source/design-sheet-v1.png';report['contextSha256']=digest(root/report['contextReference'])
    report['editReference']='round-source-v1/rounded-mouth-v2.png';report['editReferenceSha256']=digest(root/report['editReference'])
    report['promptSha256']={name:digest(root/'light-lip-source-v1'/name) for name in ['generation.txt','flatten-edit.txt']}
    report['generationChain']=[
        {'prompt':'generation.txt','editTarget':report['editReference'],'editTargetSha256':report['editReferenceSha256'],'styleReference':report['contextReference'],'output':'light-lip-source-v1/light-mouth-v1.png','outputSha256':digest(root/'light-lip-source-v1/light-mouth-v1.png')},
        {'prompt':'flatten-edit.txt','editTarget':'light-lip-source-v1/light-mouth-v1.png','editTargetSha256':digest(root/'light-lip-source-v1/light-mouth-v1.png'),'output':report['source'],'outputSha256':report['sourceSha256']}
    ]
    report['limitations']=['Optional rounded-art study, not a complete rig','Flattening prompt did not remove all cavity gradient; retain generated pixels honestly','Canonical fit and radial correspondence do not register inner lip anatomy','Shallow contacts and distinct dental tongue shapes remain unfinished']
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    return report
if __name__=='__main__':cv2.setNumThreads(1);print(json.dumps(build(),indent=2))
