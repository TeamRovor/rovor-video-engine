"""Experimental separate cavity/teeth/tongue/lip surfaces for cartoon speech."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from cartoon_head import CartoonHead,GEOMETRY,POINTS,warp,SYMBOLS,SIZE
from painted_timing import ease
ROOT=Path(__file__).resolve().parent.parent/'evan-character/cartoon-v1'

def over(bottom,top,opacity=1.):
    top=top*opacity
    return top+bottom*(1-top[:,:,3:4]/255)

def straight(raw):
    result=raw.copy();result[:,:,:3]*=255/np.maximum(result[:,:,3:4],1)
    return np.clip(result,0,255)

class LayeredCartoonHead(CartoonHead):
    def __init__(self,root=ROOT):
        super().__init__(root/'head-rig-v2')
        self.geometry=GEOMETRY;self.points=POINTS
        self.layers={name:np.asarray(Image.open(root/'oral-rig'/(name+'.png')).convert('RGBA')) for name in ['face-skin','cavity-outline','upper-teeth','tongue','tongue-raised','closed-lips','fv-contact']}
        self.contact=self.layers['fv-contact']
    def contact_surface(self,target):
        return warp(self.contact,self.points['G'],target)
    def cavity_visibility(self,aperture):
        return float(ease((aperture-2)/6))
    def closed_visibility(self,aperture):
        return 1-self.cavity_visibility(aperture)
    def oral_target(self,target,aperture):
        opening=float(ease((aperture-1)/7));oral=target.copy()
        cy=float((target[0,1]+target[8,1])/2)
        # Collapse the drawn oral surfaces at contact; facial cheek/jaw anchors
        # keep their own anatomy. No second teeth texture is cross-faded in.
        height=max(1.,float(target[:16,1].max()-target[:16,1].min()))
        scale=(1.2+(height-1.2)*opening)/height
        oral[:32,1]=cy+(oral[:32,1]-cy)*scale
        return oral
    def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
        visible=self.cavity_visibility(aperture)
        fv=float(w[7]);face=over(face,cavity,visible*(1-fv))
        face=over(face,teeth,visible*float(ease((aperture-2)/7))*(1-fv)*(1-float(w[5]+w[6])))
        face=over(face,tongue,visible*float(ease((aperture-8)/12))*(1-fv))
        face=over(face,contact,fv)
        return over(face,closed,self.closed_visibility(aperture)*(1-fv))
    def target_points(self,weights,shape_weights=None):
        return np.asarray(sum(self.points[s]*v for s,v in zip(SYMBOLS,weights)),np.float32)
    def skin_target(self,weights,target):
        return target
    def tongue_surface(self,w,oral,shape_weights=None):
        # One raised tongue drawing moves down/scales toward the floor for
        # vowels, and lifts for L. It never dissolves between two tongue images.
        tongue_art=self.layers['tongue-raised'].astype('float32').copy()
        tongue_art[:,:,:3]*=tongue_art[:,:,3:4]/255
        lift=float(w[8]);sy=.6+.4*lift
        move=np.array([[1,0,0],[0,sy,340*(1-sy)+11*(1-lift)]],np.float32)
        tongue_art=cv2.warpAffine(tongue_art,move,(SIZE,SIZE),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        tongue_art=straight(tongue_art).astype('uint8')
        return warp(tongue_art,POINTS['H'],oral,2)
    def weights(self,weights,shape_weights=None,geometry_weights=None):
        w=np.asarray(weights,float);w=w/w.sum()
        jaw=w if geometry_weights is None else np.asarray(geometry_weights,float)
        jaw=jaw/jaw.sum() if geometry_weights is not None else jaw
        target=self.target_points(jaw,shape_weights)
        aperture=float(sum(v*(self.geometry[s][7]-self.geometry[s][6]) for s,v in zip(SYMBOLS,jaw)))
        oral=self.oral_target(target,aperture)
        face=warp(self.layers['face-skin'],POINTS['X'],self.skin_target(jaw,target))
        cavity=warp(self.layers['cavity-outline'],POINTS['C'],oral,2)
        teeth=warp(self.layers['upper-teeth'],POINTS['C'],oral,2)
        tongue=self.tongue_surface(w,oral,shape_weights)
        # Interior surfaces must stay behind the inked lip boundary.
        interior=cv2.erode(np.clip(cavity[:,:,3],0,255),np.ones((3,3),np.uint8))[:,:,None]/255
        teeth*=interior;tongue*=interior
        # Reuse the original contact drawing while it awaits anatomical cleanup.
        contact=self.contact_surface(target)
        closed=warp(self.layers['closed-lips'],POINTS['X'],target,2)
        face=self.composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)
        result=straight(face)
        result=self.images['X'].astype('float32')*(1-self.weight)+result*self.weight
        return Image.fromarray(np.clip(result,0,255).astype('uint8'))
