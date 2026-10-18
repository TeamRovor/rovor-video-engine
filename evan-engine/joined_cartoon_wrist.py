"""Opt-in continuous wrist skin; existing forearm grid retained and extended."""
import numpy as np
from PIL import Image
from cartoon_body import CartoonArm,ROOT
from compact_cartoon_scene import CompactCartoonSceneBody,compact_controls

class JoinedWristArm(CartoonArm):
    def __init__(self,image,geometry,reference):
        super().__init__(image,geometry)
        xs=list(np.unique(reference.vertices[:,0]));ys=list(np.unique(reference.vertices[:,1]));bbox=image.getbbox()
        while xs[-1]<bbox[2]+3:xs.append(xs[-1]+24)
        # The exact end of the wrist blend gives the independent index an
        # affine hand region with the same parent transform as the palm.
        end=geometry['wrist'][1]+30
        if ys[-1]<end:ys.append(float(end))
        while ys[-1]<bbox[3]+3:ys.append(ys[-1]+20)
        self.vertices=np.array([(x,y) for y in ys for x in xs],np.float32);self.triangles=[]
        nx=len(xs)
        for y in range(len(ys)-1):
            for x in range(nx-1):
                a=y*nx+x
                for ids in [(a,a+1,a+nx+1),(a,a+nx+1,a+nx)]:
                    tri=self.vertices[list(ids)];lo=np.floor(tri.min(axis=0)-3).astype(int);hi=np.ceil(tri.max(axis=0)+3).astype(int)
                    region=self.image[max(0,lo[1]):min(self.image.shape[0],hi[1]+1),max(0,lo[0]):min(self.image.shape[1],hi[0]+1),3]
                    # Empty Cartesian cells far outside the wrist silhouette
                    # must not be treated as skin or inverse-mapped foldovers.
                    if region.size and region.max()>0:self.triangles.append(ids)

class JoinedWristSceneBody(CompactCartoonSceneBody):
    def __init__(self,root=ROOT):
        super().__init__(root);self.joined_wrist=True
        old=self.arms['right'];self.arms['right']=JoinedWristArm(Image.open(root/'wrist-rig/right-skin.png').convert('RGBA'),old.geometry,old)
    def layers(self,t,plan,controls=None):
        layers=super().layers(t,plan,compact_controls(t,plan) if controls is None else controls)
        # The right arm now already contains continuous wrist/palm skin.
        del layers['palm-right']
        return layers
