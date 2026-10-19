"""Optional two-layer F/V contact on a uniform placement parent.

Contact width/tilt follows the mouth corners; open-jaw height cannot squash or
inflate the source drawing. One shared F/V drawing is not calibrated anatomy.
"""
import json
import cv2,numpy as np
from PIL import Image
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead
from layered_cartoon_head import ROOT,over

def contact_matrix(target,corners):
    left,right=np.asarray(corners,np.float32);v=right-left;length=float(np.linalg.norm(v))
    dl,dr=target[8],target[0];d=dr-dl;dest_length=float(np.linalg.norm(d))
    if min(length,dest_length)<=1e-6:raise ValueError('Degenerate contact corners')
    p=np.array([-v[1],v[0]],np.float32)/length;dp=np.array([-d[1],d[0]],np.float32)/dest_length
    source=np.array([left,right,(left+right)/2+p*20],np.float32)
    destination=np.array([dl,dr,(dl+dr)/2+dp*(20*dest_length/length)],np.float32)
    return cv2.getAffineTransform(source,destination)

class PlanarFVCartoonHead(OccludedTeethCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root);folder=root/'fv-rig-v3';self.fv_v3_meta=json.loads((folder/'manifest.json').read_text())
        self.contact_art={n:np.asarray(Image.open(folder/f'{n}.png').convert('RGBA')) for n in ['lip-contact','upper-teeth']}
    def contact_parts(self,target):
        matrix=contact_matrix(target,self.fv_v3_meta['sourceCorners']);parts={}
        for name,art in self.contact_art.items():
            raw=art.astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
            raw=cv2.warpAffine(raw,matrix*2,(1024,1024),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
            parts[name]=self.constrain_surface(cv2.resize(raw,(512,512),interpolation=cv2.INTER_AREA))
        return parts
    def contact_surface(self,target):
        parts=self.contact_parts(target)
        return over(parts['lip-contact'],parts['upper-teeth'])
