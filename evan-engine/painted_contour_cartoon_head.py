"""Opt-in continuous painted oral construction study, not an approved rig.

Reuses existing speech/jaw/skin controls. Painted cavity and rim have one
registered annulus; contact is its collapsed geometry, without a second seal
sprite. F/V retains the prior renderer. One open drawing cannot establish
correct bilabial anatomy; this profile is deliberately review-only.
"""
import cv2
import numpy as np
from PIL import Image
from construction_skin_cartoon_head import ConstructionSkinCartoonHead
from cartoon_body import ROOT
from cartoon_head import POINTS, TRIANGLES, SIZE
from layered_cartoon_head import over
from lingual_cartoon_head import tongue_lift
from painted_timing import ease


def radial_points(mask, padding=0):
    contours,_=cv2.findContours(mask.astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    if not contours:raise ValueError('Missing source contour')
    contour=max(contours,key=cv2.contourArea)[:,0].astype('float32')
    left=contour[contour[:,0]==contour[:,0].min()].mean(axis=0)
    right=contour[contour[:,0]==contour[:,0].max()].mean(axis=0)
    center=(left+right)/2
    tilt=float(np.arctan2(*(right-left)[::-1]))
    vertices=contour-center;edges=np.roll(contour,-1,axis=0)-contour
    result=[]
    for angle in tilt+np.arange(16)*np.pi/8:
        direction=np.array([np.cos(angle),np.sin(angle)])
        denominator=direction[0]*edges[:,1]-direction[1]*edges[:,0]
        valid=abs(denominator)>1e-6
        distance=np.zeros(len(edges));segment=distance.copy()
        np.divide(vertices[:,0]*edges[:,1]-vertices[:,1]*edges[:,0],denominator,out=distance,where=valid)
        np.divide(vertices[:,0]*direction[1]-vertices[:,1]*direction[0],denominator,out=segment,where=valid)
        hit=valid&(distance>0)&(segment>=0)&(segment<1)
        if not np.any(hit):raise ValueError('Missing source ray')
        result.append(center+direction*(distance[hit].max()+padding))
    return np.asarray(result,'float32')


def source_landmarks(rim):
    mask=np.asarray(rim)[:,:,3]>=128
    count,labels,stats,_=cv2.connectedComponentsWithStats((~mask).astype('uint8'),8)
    holes=[i for i in range(1,count) if stats[i,0]>0 and stats[i,1]>0
           and stats[i,0]+stats[i,2]<mask.shape[1] and stats[i,1]+stats[i,3]<mask.shape[0]]
    if not holes:raise ValueError('Painted rim lacks an aperture')
    hole=labels==max(holes,key=lambda i:stats[i,4]);outer=mask|hole
    return np.vstack([radial_points(outer,2),radial_points(hole,-1)])


def oral_fields(source,target,scale=3):
    """Only oral triangles: no unrelated skin sampling from a source sheet."""
    size=SIZE*scale;target=target[:32]*scale
    mx=np.full((size,size),-1,np.float32);my=mx.copy()
    for ids in TRIANGLES:
        if max(ids)>=32:continue
        tri=target[ids];x,y,w,h=cv2.boundingRect(tri);x=max(0,x);y=max(0,y);w=min(size-x,w);h=min(size-y,h)
        if w<=0 or h<=0:continue
        inv=cv2.getAffineTransform(tri,source[ids]);yy,xx=np.mgrid[y:y+h,x:x+w].astype('float32')
        mask=np.zeros((h,w),np.uint8);cv2.fillConvexPoly(mask,np.rint(tri-[x,y]).astype('int32'),255);take=mask>0
        mx[y:y+h,x:x+w][take]=(inv[0,0]*xx+inv[0,1]*yy+inv[0,2])[take]
        my[y:y+h,x:x+w][take]=(inv[1,0]*xx+inv[1,1]*yy+inv[1,2])[take]
    return mx,my


class PaintedContourCartoonHead(ConstructionSkinCartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root)
        self.painted={n:np.asarray(Image.open(root/f'painted-oral-parts-v1/{n}.png').convert('RGBA')) for n in ['Rim','Cavity']}
        self.painted_points=source_landmarks(self.painted['Rim'])
        self.painted_rim=None;self.last_painted_target=None;self.painted_samples=0;self._painted_use=True

    def weights(self,weights,expression=None,shape_weights=None,geometry_weights=None):
        previous=self._painted_use
        try:
            self._painted_use=float(np.asarray(weights)[7])<=1e-8
            return super().weights(weights,expression,shape_weights=shape_weights,geometry_weights=geometry_weights)
        finally:self._painted_use=previous

    def oral_target(self,target,aperture):
        oral=super().oral_target(target,aperture)
        if not self._painted_use:return oral
        # Preserve a finite drawn contact stroke rather than letting the
        # annulus disappear between pixel rows. No additional seal sprite.
        left,right=oral[8],oral[0]
        chord=left[1]+(oral[:32,0]-left[0])*(right[1]-left[1])/(right[0]-left[0])
        height=float(np.ptp(oral[:16,1]-chord[:16]))
        if height<2.2:
            oral[:32,1]=chord+(oral[:32,1]-chord)*(2.2/max(height,1e-6))
        return oral

    def cavity_surface(self,w,oral,shape_weights=None):
        # F/V is outside this experiment and retains its established path.
        if float(w[7])>1e-8:
            self.painted_rim=None
            return super().cavity_surface(w,oral,shape_weights)
        fields=oral_fields(self.painted_points,oral)
        parts={}
        for name,image in self.painted.items():
            raw=image.astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
            part=cv2.remap(raw,*fields,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
            parts[name]=cv2.resize(part,(SIZE,SIZE),interpolation=cv2.INTER_AREA)
        self.painted_rim=parts['Rim'];self.last_painted_target=oral.copy();self.painted_samples+=1
        return parts['Cavity']

    def interior_mask(self,cavity,w,oral,shape_weights=None):
        if self.painted_rim is None:return super().interior_mask(cavity,w,oral,shape_weights)
        # Rim is composited LAST to occlude all retained teeth/tongue edges.
        return np.clip(cavity[:,:,3:4],0,255)/255

    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        if self.painted_rim is None:return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        floor=float(ease((aperture-8)/12));lift=tongue_lift(w)*float(ease((aperture-1.2)/4))
        group=over(cavity,tongue,max(floor,lift))
        group=over(group,teeth,float(ease((aperture-2)/7))*self.teeth_rounding_visibility(w))
        group=over(group,self.painted_rim)
        return over(face,group)
