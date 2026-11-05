"""Build separate oral surfaces from existing cartoon drawings and hidden plates."""
import argparse,hashlib,json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from build_cartoon_heads import affine_rgba,SIZE
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'

def align_hidden(path,base):
    image=Image.open(path).convert('RGBA').resize((SIZE,SIZE),Image.Resampling.LANCZOS);raw=np.asarray(image)
    yy,xx=np.where(raw[:,:,3]>128);by,bx=np.where(base[:,:,3]>128)
    scale=(by.max()-by.min())/(yy.max()-yy.min())
    dx=(bx.max()+bx.min())/2-scale*(xx.max()+xx.min())/2;dy=by.min()-scale*yy.min()
    initial=np.array([[scale,0,dx],[0,scale,dy]],np.float32);placed=affine_rgba(raw,initial)
    gray=lambda a:cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    mask=np.zeros((SIZE,SIZE),np.uint8);mask[80:290,130:390]=255
    matrix=np.eye(2,3,dtype='float32')
    score,matrix=cv2.findTransformECC(gray(base),gray(placed),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,250,1e-6),mask,5)
    if score<.94 or np.max(abs(matrix[:,:2]-np.eye(2)))>.15:raise ValueError('Hidden plate does not register faithfully')
    return affine_rgba(placed,matrix,True),dict(ecc=float(score),initial=initial.tolist(),correction=matrix.tolist(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def mouth_mask(image,box=(187,308,289,369)):
    x0,y0,x1,y1=box;roi=np.zeros((SIZE,SIZE),np.uint8);roi[y0:y1,x0:x1]=1
    dark=((image[:,:,:3].max(axis=2)<155)&(roi>0)).astype('uint8')
    contours,_=cv2.findContours(dark,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    mask=np.zeros_like(dark);cv2.drawContours(mask,[max(contours,key=cv2.contourArea)],-1,255,-1)
    return mask

def layer(rgb,alpha):
    return np.dstack((rgb[:,:,:3],np.clip(alpha,0,255))).astype('uint8')

def build(root=ROOT):
    heads=root/'head-rig-v2';source=root/'oral-source';output=root/'oral-rig';output.mkdir(exist_ok=True)
    inputs=list(heads.glob('*.png'))+list(source.glob('*.png'))
    before={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    base=np.asarray(Image.open(heads/'head-X.png'));mouth=np.asarray(Image.open(heads/'head-C.png'))
    blank,blank_report=align_hidden(source/'blank-face.png',base);empty,empty_report=align_hidden(source/'empty-cavity.png',mouth)
    # Only use the artist-generated hidden skin where the old lip stroke was.
    ink=np.zeros((SIZE,SIZE),np.uint8);ink[307:336,185:290]=(base[307:336,185:290,:3].max(axis=2)<145)*255
    repair=cv2.GaussianBlur(cv2.dilate(ink,np.ones((11,11),np.uint8)),(17,17),4).astype('float32')/255
    repair=np.maximum(repair,cv2.dilate(ink,np.ones((5,5),np.uint8)).astype('float32')/255)[:,:,None]
    # Match hidden skin color using surrounding cheek pixels, excluding ink.
    ring=cv2.dilate(ink,np.ones((23,23),np.uint8))-cv2.dilate(ink,np.ones((15,15),np.uint8));samples=ring>0
    delta=np.median(base[samples,:3].astype(float)-blank[samples,:3].astype(float),axis=0)
    corrected=np.clip(blank[:,:,:3].astype(float)+delta,0,255)
    clean=base.copy();clean[:,:,:3]=np.clip(base[:,:,:3]*(1-repair)+corrected*repair,0,255).astype('uint8')
    Image.fromarray(clean).save(output/'face-skin.png')
    mask=mouth_mask(mouth);Image.fromarray(mask).save(output/'oral-mask.png')
    # Original black outline remains original art. Generated cavity supplies
    # only hidden interior colors behind the original teeth/tongue.
    shell=(mask-cv2.erode(mask,np.ones((5,5),np.uint8))).astype(float)/255
    keep=shell*np.clip((110-mouth[:,:,:3].max(axis=2).astype(float))/55,0,1)
    cavity=mouth.copy();cavity[:,:,:3]=(mouth[:,:,:3]*keep[:,:,None]+empty[:,:,:3]*(1-keep[:,:,None])).astype('uint8');cavity[:,:,3]=mask
    Image.fromarray(cavity).save(output/'cavity-outline.png')
    teeth=(mouth[:,:,0]>180)&(mouth[:,:,1]>170)&(mouth[:,:,2]>120)&(mask>0)
    tongue=(mouth[:,:,0]>150)&(mouth[:,:,1]<165)&(mouth[:,:,2]<145)&(np.mgrid[:SIZE,:SIZE][0]>=336)&(mask>0)
    for name,select in [('upper-teeth',teeth),('tongue',tongue)]:
        alpha=cv2.GaussianBlur(select.astype('float32'),(3,3),.45)*255
        Image.fromarray(layer(mouth,alpha)).save(output/(name+'.png'))
    support=cv2.dilate(ink,np.ones((3,3),np.uint8)).astype(float)/255
    pigment=np.array([15,10,7],float);direction=np.maximum(corrected-pigment,1)
    opacity=np.clip(((corrected-base[:,:,:3])*direction).sum(axis=2)/np.maximum((direction*direction).sum(axis=2),1),0,1)*support
    rgb=np.clip((base[:,:,:3]-(1-opacity[:,:,None])*corrected)/np.maximum(opacity[:,:,None],.01),0,255)
    lip=layer(rgb,opacity*255)
    Image.fromarray(lip).save(output/'closed-lips.png')
    h=np.asarray(Image.open(heads/'head-H.png'));hm=mouth_mask(h,(186,307,289,366))
    raised=(h[:,:,0]>150)&(h[:,:,1]<165)&(h[:,:,2]<145)&(np.mgrid[:SIZE,:SIZE][0]>=318)&(hm>0)
    Image.fromarray(layer(h,cv2.GaussianBlur(raised.astype('float32'),(3,3),.45)*255)).save(output/'tongue-raised.png')
    g=np.asarray(Image.open(heads/'head-G.png'));contact_mask=mouth_mask(g,(186,309,286,339));contact_mask=cv2.GaussianBlur(cv2.dilate(contact_mask,np.ones((3,3),np.uint8)),(3,3),.4)
    Image.fromarray(layer(g,contact_mask)).save(output/'fv-contact.png')
    report=dict(version=1,blank=blank_report,cavity=empty_report,skin_color_offset=delta.tolist(),layers=['face-skin','cavity-outline','upper-teeth','tongue','tongue-raised','closed-lips','fv-contact'],status='experimental oral layers; visual acceptance required',animationReady=False)
    report['input_sha256']=before
    (output/'manifest.json').write_text(json.dumps(report,indent=2))
    if before!={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}:raise RuntimeError('Oral builder modified its source')
    return report
if __name__=='__main__':print(json.dumps(build(),indent=2))
