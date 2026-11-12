"""Local generated underarm patches on an otherwise exact original torso."""
import hashlib,json
import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from cartoon_body import ROOT

def build(root=ROOT):
    original=np.asarray(Image.open(root/'body-rig/torso.png').convert('RGBA')).copy()
    raw=np.asarray(Image.open(root/'socket-source/torso-hidden-v2.png').convert('RGBA').resize((1024,1536))).copy()
    gray=lambda a:cv2.cvtColor(a[:,:,:3],cv2.COLOR_RGB2GRAY).astype('float32')/255
    gate=np.zeros((1536,1024),np.uint8);gate[390:640,420:610]=255
    matrix=np.array([[1,0,0],[0,1.028,-73.4]],np.float32)
    score,matrix=cv2.findTransformECC(gray(original),gray(raw),matrix,cv2.MOTION_AFFINE,(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,300,1e-6),gate,5)
    if score<.95 or np.max(abs(matrix[:,:2]-np.eye(2)))>.10:raise ValueError('Shirt registration outside local patch gate')
    f=raw.astype('float32');f[:,:,:3]*=f[:,:,3:4]/255
    f=cv2.warpAffine(f,matrix,(1024,1536),flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_CONSTANT)
    f[:,:,:3]*=255/np.maximum(f[:,:,3:4],1)
    delta=np.median(original[410:445,410:440,:3].reshape(-1,3),axis=0)-np.median(f[410:445,410:440,:3].reshape(-1,3),axis=0)
    navy=(f[:,:,2]>f[:,:,0]+15)&(f[:,:,3]>0);f[:,:,:3][navy]+=delta
    mask=Image.new('L',(1024,1536));draw=ImageDraw.Draw(mask)
    draw.polygon([(320,440),(385,440),(416,596),(412,623),(378,623),(340,520)],fill=255)
    draw.polygon([(1024-x,y) for x,y in [(320,440),(385,440),(416,596),(412,623),(378,623),(340,520)]],fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(3));weight=np.asarray(mask).astype('float32')[:,:,None]/255
    # Blend associated colors and alpha together; no black edge at soft seams.
    a=original.astype('float32');a[:,:,:3]*=a[:,:,3:4]/255;f[:,:,:3]*=f[:,:,3:4]/255
    out=a*(1-weight)+f*weight;out[:,:,:3]*=255/np.maximum(out[:,:,3:4],1)
    result=np.clip(out,0,255).astype('uint8');result[weight[:,:,0]==0]=original[weight[:,:,0]==0]
    output=root/'socket-rig';output.mkdir(exist_ok=True);Image.fromarray(result).save(output/'torso.png');mask.save(output/'patch-mask.png')
    report=dict(version=1,sourceSha256=hashlib.sha256((root/'socket-source/torso-hidden-v2.png').read_bytes()).hexdigest(),registration=dict(method='center-shirt affine ECC with collar/waist initialization',score=float(score),matrix=matrix.tolist(),navyColorOffset=delta.tolist()),changedPixels=int(np.any(result!=original,axis=2).sum()),visibleChangedPixels=int((np.any(result!=original,axis=2)&((result[:,:,3]>0)|(original[:,:,3]>0))).sum()),protectedCenterExact=bool(np.array_equal(result[:,430:594],original[:,430:594])),animationReady=False,limitations=['Local underarm replacement only, not a completed shoulder rig','Neck and hand joins still require cleanup'])
    (output/'manifest.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':print(json.dumps(build(),indent=2))
