"""Local FV contact artwork split into independent lip/outline and upper teeth."""
import hashlib,json
import cv2
import numpy as np
from PIL import Image
from cartoon_body import ROOT

def build(root=ROOT):
    base=np.asarray(Image.open(root/'head-rig-v2/head-X.png').convert('RGBA'));source=root/'fv-source/contact-v1.png';raw=np.asarray(Image.open(source).convert('RGBA').resize((512,512),Image.Resampling.LANCZOS))
    visible=base.copy();visible[:,:,:3]=(base[:,:,:3].astype(float)*base[:,:,3:4]/255+np.array([243,238,226])*(1-base[:,:,3:4]/255)).astype('uint8')
    gray=lambda a:cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((512,512),np.uint8);mask[80:300,130:390]=255
    matrix=np.eye(2,3,dtype='float32');score,matrix=cv2.findTransformECC(gray(visible),gray(raw),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),mask,5)
    if score<.97 or np.max(abs(matrix[:,:2]-np.eye(2)))>.08:raise ValueError('FV source changes stable features')
    art=cv2.warpAffine(raw,matrix,(512,512),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP)
    roi=np.zeros((512,512),np.uint8);roi[308:340,187:290]=1
    dark=((art[:,:,:3].max(axis=2)<130)&(roi>0)).astype('uint8');contours,_=cv2.findContours(dark,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);outer=np.zeros_like(dark);cv2.drawContours(outer,[max(contours,key=cv2.contourArea)],-1,255,-1)
    outer=cv2.GaussianBlur(cv2.dilate(outer,np.ones((3,3),np.uint8)),(3,3),.4)
    teeth=(art[:,:,0]>180)&(art[:,:,1]>175)&(art[:,:,2]>125)&(outer>200)
    teeth=cv2.GaussianBlur(teeth.astype('float32'),(3,3),.4)*255
    lips=np.dstack((art[:,:,:3],outer)).copy();lips[:,:,3]=(outer*(1-teeth/255)).astype('uint8')
    tooth=np.dstack((art[:,:,:3],teeth)).astype('uint8')
    # Upper teeth form their own complete surface, not holes revealing skin.
    output=root/'fv-rig';output.mkdir(exist_ok=True)
    for name,a in [('lip-contact',lips),('upper-teeth',tooth)]:a[a[:,:,3]==0,:3]=0;Image.fromarray(a.astype('uint8')).save(output/(name+'.png'))
    Image.fromarray(outer).save(output/'contact-mask.png')
    geometry=[196,325,274,320,316,329,319,324,393]
    report=dict(version=1,sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),registration=dict(ecc=float(score),matrix=matrix.tolist()),geometry=geometry,animationReady=False,limitations=['Small stylized contact; rolled lower-lip anatomy still needs animator review','One contact design for F and V; no calibrated speaker anatomy','No timing or pronunciation corrections'])
    (output/'manifest.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(build(),indent=2))
