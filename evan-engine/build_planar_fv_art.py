"""Separate a generated contact source into lip/underpaint and upper teeth."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from layered_cartoon_head import ROOT,straight,over
from bounded_cartoon_head import bounded_premultiplied

def bounds(a):
    y,x=np.where(a[:,:,3]>128);return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def build(root=ROOT):
    folder=root/'fv-source-v3';path=folder/'contact-v4.png';hidden_path=folder/'hidden-base-v1.png'
    raw=np.array(Image.open(path).convert('RGBA'));hidden=np.array(Image.open(hidden_path).convert('RGBA'))
    raw[raw[:,:,3]>=250,3]=255;hidden[hidden[:,:,3]>=250,3]=255
    b=bounds(raw);hb=bounds(hidden);hx=(b[2]-b[0])/(hb[2]-hb[0]);hy=(b[3]-b[1])/(hb[3]-hb[1])
    hidden_matrix=np.array([[hx,0,b[0]-hx*hb[0]],[0,hy,b[1]-hy*hb[1]]],np.float32)
    p=hidden.astype('float32');p[:,:,:3]*=p[:,:,3:4]/255
    p=cv2.warpAffine(p,hidden_matrix,(raw.shape[1],raw.shape[0]),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    hidden=straight(bounded_premultiplied(p))
    r,g,blue,a=[raw[:,:,i].astype(float) for i in range(4)]
    seed=((a>200)&(r>180)&(g>175)&(blue>140)).astype('uint8')
    n,labels,stats,_=cv2.connectedComponentsWithStats(seed)
    ids=[i for i in range(1,n) if stats[i,cv2.CC_STAT_AREA]>100]
    if len(ids)<1:raise ValueError('No ivory incisor source')
    core=np.isin(labels,ids).astype('uint8')*255
    fill=cv2.dilate(core,np.ones((9,9),np.uint8))>0
    guard=cv2.dilate(core,np.ones((39,39),np.uint8))>0
    if float(hidden[:,:,3][fill].min())<240:raise ValueError('Hidden plate does not cover tooth footprint')
    base=raw.copy();base[fill,:3]=np.rint(hidden[fill,:3]).astype('uint8')
    base[guard&(raw[:,:,3]<255)]=0
    teeth=raw.copy();teeth[~guard]=0
    sx=76/(b[2]-b[0]);sy=14/(b[3]-b[1]);matrix=np.array([[sx,0,198-sx*b[0]],[0,sy,317-sy*b[1]]],np.float32)
    def register(art):
        p=art.astype('float32');p[:,:,:3]*=p[:,:,3:4]/255
        p=cv2.warpAffine(p,matrix*4,(2048,2048),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        p=bounded_premultiplied(cv2.resize(p,(512,512),interpolation=cv2.INTER_AREA));out=np.rint(straight(p)).astype('uint8');out[out[:,:,3]==0,:3]=0;return out
    output=root/'fv-rig-v3';output.mkdir(exist_ok=True);parts={name:register(art) for name,art in [('lip-contact',base),('upper-teeth',teeth),('whole-reference',raw)]}
    for name,art in parts.items():Image.fromarray(art).save(output/f'{name}.png')
    def pm(v):
        p=v.astype('float32');p[:,:,:3]*=p[:,:,3:4]/255;return p
    combined=over(pm(parts['lip-contact']),pm(parts['upper-teeth']));error=np.abs(combined-pm(parts['whole-reference']));diff=float(error.mean());roi=parts['whole-reference'][:,:,3]>0;local_diff=float(error[roi].mean())
    ys,xs=np.where(raw[:,:,3]>128);anchors=[]
    for take in [xs<b[0]+4,xs>=b[2]-4]:
        point=np.array([float(xs[take].mean()),float(ys[take].mean()),1]);anchors.append((matrix@point).tolist())
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    report=dict(version=3,source='fv-source-v3/contact-v4.png',sourceSha256=digest(path),hiddenSourceSha256=digest(hidden_path),sourceBounds=b,hiddenBounds=hb,hiddenRegistration=hidden_matrix.tolist(),matrix=matrix.tolist(),targetBounds=[198,317,274,331],sourceCorners=anchors,registration='canonical affine fit and alpha-endpoint corner estimates, not anatomical calibration',alphaSnapThreshold=250,supersample=4,components=['lip-contact','upper-teeth'],sourceCompositeMeanPremultipliedDifference255=diff,sourceCompositeLocalMeanPremultipliedDifference255=local_diff,animationReady=False,generationMode='built-in imagegen')
    report['promptSha256']={p.name:digest(p) for p in folder.glob('*.txt')};report['rawSourceSha256']={p.name:digest(p) for p in folder.glob('*.png')};report['styleReferenceSha256']=digest(root/'source/design-sheet-v1.png')
    report['generationGraph']=[{'output':'contact-v1.png','reference':'source/design-sheet-v1.png','prompt':'generation.txt','status':'rejected grin'},{'output':'contact-v2.png','reference':'contact-v1.png','prompt':'contact-edit.txt','status':'rejected grin'},{'output':'contact-v3.png','reference':'source/design-sheet-v1.png','prompt':'neutral-contact.txt','status':'rejected upper-lip bulk'},{'output':'contact-v4.png','reference':'contact-v3.png','prompt':'upper-lip-edit.txt','status':'chosen optional source'},{'output':'hidden-base-v1.png','reference':'contact-v4.png','prompt':'hidden-base.txt','status':'hidden underpaint only'}]
    report['limitations']=['F/V share one pose; no calibrated speaker anatomy','Peach lower-lip volume and corner creases need artist review','Two actual contact layers currently share a uniform placement parent','Generated hidden plate used only beneath extracted teeth; canonical fit is authored']
    (output/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':cv2.setNumThreads(1);print(json.dumps(build(),indent=2))
