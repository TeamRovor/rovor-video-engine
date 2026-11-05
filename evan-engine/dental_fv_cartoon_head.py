"""Optional rigid contact incisors behind a moving source-derived aperture.

Teeth keep their uniform-plane thickness instead of following oral-envelope
strain. Their upper edge follows the registered contact's upper edge. The
matte is a source-component aperture plus one native pixel, NOT measured lips.
"""
import cv2,numpy as np
from correspondent_fv_cartoon_head import CorrespondentFVCartoonHead
from planar_fv_cartoon_head import contact_matrix
from layered_cartoon_head import ROOT,over

def tooth_anchor(surface):
    alpha=surface[:,:,3].astype(float);mass=float(alpha.sum())
    if mass<=1e-6:raise ValueError('Empty tooth surface')
    rows=alpha.sum(axis=1);cdf=np.cumsum(rows);q=float(np.interp(.1*mass,cdf,np.arange(len(rows))+.5))
    x=float((alpha.sum(axis=0)*np.arange(alpha.shape[1])).sum()/mass)
    return np.array([x,q],np.float32)

class DentalFVCartoonHead(CorrespondentFVCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        support=(self.contact_art['upper-teeth'][:,:,3]>0).astype('uint8')
        distance=cv2.distanceTransform(1-support,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)
        self.contact_window=np.clip(2-distance,0,1).astype('float32')
        self.capture_dental=False;self.last_dental=None;self.dental_samples=0;self.dental_fallbacks=0
    def contact_surface(self,target):
        self._dental_parts=self.contact_parts(target)
        matrix=contact_matrix(target,self.fv_v3_meta['sourceCorners'])
        window=cv2.warpAffine(self.contact_window,matrix*2,(1024,1024),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        self._dental_window=cv2.resize(window,(512,512),interpolation=cv2.INTER_AREA)
        return over(self._dental_parts['lip-contact'],self._dental_parts['upper-teeth'])
    def registered_contact_surface(self,contact,field,w):
        original=self._dental_parts['upper-teeth'];stretched=self._remap(original,field)
        try:delta=tooth_anchor(stretched)-tooth_anchor(original)
        except ValueError:
            self.dental_fallbacks+=1
            return super().registered_contact_surface(contact,field,w)
        matrix=np.array([[1,0,delta[0]],[0,1,delta[1]]],np.float32)
        rigid=cv2.warpAffine(original,matrix,(512,512),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        aperture=np.clip(self._remap(self._dental_window,field),0,1)
        clipped=rigid*aperture[:,:,None]
        lip=self._remap(self._dental_parts['lip-contact'],field)
        self.dental_samples+=1
        if self.capture_dental:
            self.last_dental=dict(contactWeight=float(w[7]),translation=delta.tolist(),beforeMatteCoverage=float(rigid[:,:,3].sum()/255),afterMatteCoverage=float(clipped[:,:,3].sum()/255),materialAlphaBeforeMatte=float(rigid[:,:,3].max()),materialAlphaAfterMatte=float(clipped[:,:,3].max()),stretchedAlphaVariance=float(self._vertical_variance(stretched)),rigidAlphaVariance=float(self._vertical_variance(rigid)),validPremultiplied=bool(np.isfinite(clipped).all() and clipped.min()>=0 and np.all(clipped[:,:,:3]<=clipped[:,:,3:4]+1e-4)))
        return over(lip,clipped)
    @staticmethod
    def _vertical_variance(surface):
        rows=surface[:,:,3].sum(axis=1);total=float(rows.sum());y=np.arange(len(rows));mean=float((rows*y).sum()/max(total,1e-9));return float((rows*(y-mean)**2).sum()/max(total,1e-9))
