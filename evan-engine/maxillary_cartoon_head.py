"""Opt-in upper-lip/rigid incisor parent study, not calibrated anatomy."""
import cv2,numpy as np
from continuous_fv_cartoon_head import ContinuousFVCartoonHead
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from cartoon_head import POINTS,SIZE
from rounded_art_cartoon_head import rounded_art_strength
from layered_cartoon_head import over
from lingual_cartoon_head import tongue_lift
from painted_timing import ease


def maxillary_oral_target(target,aperture):
    oral=target.copy();left,right=target[8],target[0]
    gap=max(.15,float(aperture)-1.);upper=min(4.,.2*gap);lower=gap-upper
    def chord(points):return left[1]+(points[:,0]-left[0])*(right[1]-left[1])/(right[0]-left[0])
    for start,top,bottom,bias in [(0,upper+1.1,lower+1.1,0),(16,upper,lower,0)]:
        points=target[start:start+16];a,b=points[8],points[0];line=a[1]+(points[:,0]-a[0])*(b[1]-a[1])/(b[0]-a[0]);d=points[:,1]-line
        y=np.where(d>=0,d/max(float(d.max()),1e-6)*bottom,d/max(float(-d.min()),1e-6)*top)
        oral[start:start+16,1]=chord(points)+bias+y
    return oral


class MaxillaryCartoonHead(ContinuousFVCartoonHead):
    def oral_target(self,target,aperture):
        legacy=ConstructionSkinCartoonHead.oral_target(self,target,aperture);fv=self._fv_strength
        if fv>=1:return legacy
        direct=maxillary_oral_target(target,aperture);oral=direct.copy();oral[:32,1]=direct[:32,1]*(1-fv)+legacy[:32,1]*fv
        return oral

    def teeth_surface(self,w,oral,shape_weights=None):
        if self._fv_strength>=1:return super().teeth_surface(w,oral,shape_weights)
        return self.rigid_teeth_surface(w,oral)

    def rigid_teeth_surface(self,w,oral):
        teeth,tip=self.rigid_teeth_parts(w,oral)
        return over(teeth,tip)

    def rigid_teeth_parts(self,w,oral):
        # The source alpha is already isolated teeth. Hidden RGB elsewhere in
        # that PNG must never be mistaken for visible full-face paint.
        source=self.layers['upper-teeth'].astype('float32').copy();source[:,:,:3]*=source[:,:,3:4]/255
        left,right=oral[8],oral[0];v=right-left;angle=float(np.arctan2(v[1],v[0])-np.arctan2(*(POINTS['C'][0]-POINTS['C'][8])[::-1]));c,s=np.cos(angle),np.sin(angle)
        rotation=np.array([[c,-s],[s,c]],np.float32);anchor=POINTS['C'][28];dest=oral[28].copy()
        normal=np.array([-v[1],v[0]],np.float32)/np.linalg.norm(v)
        # Actual tooth plane retains native size/thickness; the upper-lip
        # parent and rounded retraction determine its exposure through matte.
        dest-=normal*(3+16*rounded_art_strength(w))
        matrix=np.column_stack([rotation,dest-rotation@anchor]).astype('float32')
        teeth=cv2.warpAffine(source,matrix*3,(SIZE*3,SIZE*3),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);teeth=cv2.resize(teeth,(SIZE,SIZE),interpolation=cv2.INTER_AREA)
        tip=np.zeros_like(teeth)
        if self.dental_fraction>0:
            blade,_=self.tongue_parts(w,oral);alpha=teeth[:,:,3];ys=np.arange(SIZE,dtype=np.float32)[:,None];bottom=np.max(np.where(alpha>=127.5,ys,-1000),axis=0);edge=np.clip((ys-(bottom[None,:]-1.5))/1.5,0,1)*(alpha/255);tip=blade*(float(self.dental_fraction)*edge[:,:,None])
        return teeth,tip

    def painted_oral_group(self,cavity,teeth,tongue,contact,closed,aperture,w):
        floor=float(ease((aperture-8)/12));lift=tongue_lift(w)*float(ease((aperture-1.2)/4))
        group=over(cavity,tongue,max(floor,lift))
        # Opaque tooth material is hidden geometrically, not faded into skin.
        return over(over(group,teeth),self.painted_rim)
