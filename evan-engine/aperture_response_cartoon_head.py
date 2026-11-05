"""Optional direct lip-aperture response, avoiding a second opening gate.

Existing phoneme boundaries and jaw weights remain unchanged. This is authored
cartoon geometry, not recovered facial motion or a phoneme timing correction.
"""
import cv2
import numpy as np
from painted_contour_cartoon_head import PaintedContourCartoonHead


def direct_oral_target(target,aperture):
    oral=target.copy()
    left,right=target[8],target[0]
    def chord(points):
        return left[1]+(points[:,0]-left[0])*(right[1]-left[1])/(right[0]-left[0])
    # Inner and outer lips share a chord, but have independent vertical
    # extents. The old whole-surface ease multiplied an already changing
    # aperture and released the entire outer drawing within one frame.
    gap=max(.15,float(aperture)-1.)
    for start,height in [(0,gap+2.2),(16,gap)]:
        points=target[start:start+16];a,b=points[8],points[0]
        local=a[1]+(points[:,0]-a[0])*(b[1]-a[1])/(b[0]-a[0])
        offset=points[:,1]-local
        pos=max(float(offset.max()),1e-6);neg=max(float(-offset.min()),1e-6)
        normalized=np.where(offset>=0,offset/pos,offset/neg)
        oral[start:start+16,1]=chord(points)+normalized*height/2
    return oral


class ApertureResponseCartoonHead(PaintedContourCartoonHead):
    def oral_target(self,target,aperture):
        if not self._painted_use:return super().oral_target(target,aperture)
        return direct_oral_target(target,aperture)

    def interior_mask(self,cavity,w,oral,shape_weights=None):
        if not self._painted_use:return super().interior_mask(cavity,w,oral,shape_weights)
        # Interior surfaces belong inside the inner contour, not the cavity's
        # filled outer silhouette. One native pixel retracts them behind ink.
        scale=3;mask=np.zeros((512*scale,512*scale),np.uint8)
        cv2.fillConvexPoly(mask,np.rint(oral[16:32]*scale*256).astype('int32'),255,lineType=cv2.LINE_AA,shift=8)
        mask=cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA)
        mask=cv2.erode(mask,np.ones((3,3),np.uint8))
        return mask[:,:,None].astype('float32')/255*np.clip(cavity[:,:,3:4],0,255)/255
