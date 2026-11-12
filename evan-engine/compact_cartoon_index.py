"""Opt-in shallow index curl with authored 2D projected phalange lengths.

This is cartoon foreshortening, not a measured 3D hand or new artwork.
"""
import numpy as np
from cartoon_index import IndexRig
from painted_character import rotation

class CompactIndexRig(IndexRig):
    def matrices(self,angles):
        angles=np.asarray(angles,float)
        if angles.shape!=(3,) or not np.isfinite(angles).all() or np.any(angles<np.array([-7.,0.,0.])-.0001) or np.any(angles>np.array([0.,42.,24.5])+.0001):
            raise ValueError('Compact index angles exceed the inspected shallow-curl range')
        curl=float(np.clip(angles[1]/42,0,1))
        if curl==0:return super().matrices(angles)
        factor=1-.3*curl
        projection=np.eye(2)+(factor-1)*np.outer(self.axis,self.axis)
        matrices=[];position=self.joints[0].astype(float)
        for i,joint in enumerate(self.joints):
            if i:position=(matrices[-1]@np.r_[joint,1])[:2]
            linear=rotation((0,0),float(sum(angles[:i+1])))[:2,:2]@projection
            m=np.eye(3);m[:2,:2]=linear;m[:2,2]=position-linear@joint
            matrices.append(m)
        return matrices
