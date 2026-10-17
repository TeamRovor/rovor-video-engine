"""Register the generated point drawing to a manually inspected wrist axis."""
import hashlib,json,math
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from cartoon_body import ROOT

def build(root=ROOT):
    source=root/'hand-source/right-point-v1.png';image=np.asarray(Image.open(source).convert('RGBA')).astype('float32')
    pivot=np.array([457.,531.]);target=np.array([810.,762.]);angle=math.radians(15);scale=.16
    linear=scale*np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]],dtype='float32')
    matrix=np.c_[linear,target-linear@pivot].astype('float32')
    image[:,:,:3]*=image[:,:,3:4]/255
    raw=cv2.warpAffine(image,matrix,(1024,1536),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    raw[:,:,:3]*=255/np.maximum(raw[:,:,3:4],1)
    yy,xx=np.mgrid[:1536,:1024];direction=np.array([61,137])/np.linalg.norm([61,137]);distance=(xx-810)*direction[0]+(yy-762)*direction[1]
    raw[:,:,3]*=np.clip((distance+18)/6,0,1)
    output=root/'hand-rig';output.mkdir(exist_ok=True);Image.fromarray(np.clip(raw,0,255).astype('uint8')).save(output/'right-point.png')
    meta=dict(version=1,wrists=dict(left=[214,762],right=[810,762]),sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceSize=[image.shape[1],image.shape[0]],sourceWrist=pivot.tolist(),targetWrist=target.tolist(),matrix=matrix.tolist(),registration='manual wrist/axis placement, not whole-image similarity',pose='right-screen point: index extended, three curled fingers and thumb',animationReady=False,limitations=['Fingers are a single alternate drawing, not individually articulated','Original torso/armpit and neck seams remain','Wrist contour/color transition remains visible at close range','Pointing hand outline is thinner and palm more compact than original open drawing'])
    (output/'manifest.json').write_text(json.dumps(meta,indent=2));return meta
if __name__=='__main__':print(json.dumps(build(),indent=2))
