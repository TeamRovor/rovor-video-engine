"""Register a new contact plate; keep full source separate from working lips."""
import json,hashlib
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT

def build(root=ROOT):
    source=root/'fv-source-v2/contact-v2.png'
    raw=np.asarray(Image.open(source).convert('RGB').resize((512,512),Image.Resampling.LANCZOS))
    reference=np.asarray(Image.open(root/'fv-source/contact-v1.png').convert('RGB').resize((512,512),Image.Resampling.LANCZOS))
    gray=lambda a:cv2.cvtColor(a,cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((512,512),np.uint8);mask[80:300,130:390]=255
    matrix=np.eye(2,3,dtype='float32');score,matrix=cv2.findTransformECC(gray(reference),gray(raw),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),mask,5)
    if score<.98 or np.max(abs(matrix[:,:2]-np.eye(2)))>.04:raise ValueError('Stable-face registration rejected')
    art=cv2.warpAffine(raw,matrix,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    # Artist-plate extraction boundary includes the peach lower-lip volume.
    # It is an alpha mask for source pixels, not a generated geometric mouth.
    contour=np.array([[193,325],[199,319],[216,315],[239,314],[257,317],[272,320],[272,324],[251,329],[235,335],[220,338],[209,336],[203,331]],np.int32)
    alpha=np.zeros((512,512),np.uint8);cv2.fillPoly(alpha,[contour],255)
    alpha=cv2.GaussianBlur(alpha,(5,5),.7)
    tooth=((art[:,:,0]>185)&(art[:,:,1]>175)&(art[:,:,2]>125)&(alpha>200)).astype('uint8')
    n,labels,stats,_=cv2.connectedComponentsWithStats(tooth)
    if n<2:raise ValueError('Missing upper teeth')
    tooth=(labels==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))).astype('float32')
    tooth=cv2.GaussianBlur(tooth,(3,3),.4)*255
    roll=np.zeros((512,512),np.uint8)
    cv2.fillPoly(roll,[np.array([[204,328],[225,326],[251,326],[251,337],[204,342]],np.int32)],255)
    roll=cv2.GaussianBlur(roll,(3,3),.4).astype('float32')/255
    roll*=alpha/255
    lips=np.dstack((art,alpha)).copy();lips[:,:,3]=(alpha*(1-tooth/255)*(1-roll)).astype('uint8')
    volume=np.dstack((art,roll*255)).astype('uint8')
    teeth=np.dstack((art,tooth)).astype('uint8');folder=root/'fv-rig-v2';folder.mkdir(exist_ok=True)
    for name,a in [('lip-contact',lips),('upper-teeth',teeth),('lower-lip',volume)]:
        a[a[:,:,3]==0,:3]=0;Image.fromarray(a).save(folder/(name+'.png'))
    Image.fromarray(alpha).save(folder/'contact-mask.png')
    geometry=[196,325,270,320,315,337,319,325,393]
    report=dict(version=2,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),registration=dict(ecc=float(score),matrix=matrix.tolist()),geometry=geometry,animationReady=False,extractionContour=contour.tolist(),limitations=['Peach lower-lip roll remains stylized; not anatomical approval','One contact design shared by F and V','Feathered skin rim may show a seam during contact release','No acoustic timing or pronunciation changes'])
    (folder/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':cv2.setNumThreads(1);print(json.dumps(build(),indent=2))
