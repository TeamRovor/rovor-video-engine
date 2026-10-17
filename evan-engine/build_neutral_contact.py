"""Refine the existing drawn F/V aperture without generating a new identity."""
import hashlib,json
import cv2
import numpy as np
from PIL import Image
from build_cartoon_body import ROOT


def build(root=ROOT):
    source=root/'oral-rig/fv-contact.png'
    raw=np.asarray(Image.open(source).convert('RGBA')).astype('float32')
    raw[:,:,:3]*=raw[:,:,3:4]/255
    yy,xx=np.indices((512,512),dtype='float32')
    corner=np.exp(-((xx-197)/12)**2)+np.exp(-((xx-279)/12)**2)
    my=324+(yy-324)/.55+3.5*corner
    result=cv2.remap(raw,xx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    result[:,:,:3]*=255/np.maximum(result[:,:,3:4],1)
    path=root/'oral-rig/fv-contact-v3.png'
    Image.fromarray(np.clip(result,0,255).astype('uint8')).save(path)
    report={'method':'source-art aperture compression and corner relaxation',
            'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'outputSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'verticalScale':.55,'visualApproved':False,'phonemeCorrectnessVerified':False}
    (root/'oral-rig/fv-contact-v3.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(build(),indent=2))
