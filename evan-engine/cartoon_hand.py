"""Separate wrist-local drawings on the existing hierarchical hand transform.

Pose drawings are selected discretely; never dissolve two sets of fingers.
"""
import cv2
import numpy as np
from PIL import Image
from painted_character import arm_transforms

def split_hand(image,geometry):
    """Feather inside the bare wrist, retaining overlap for a separate hand."""
    a=np.asarray(image).copy();yy,xx=np.mgrid[:a.shape[0],:a.shape[1]]
    wrist=np.asarray(geometry['wrist']);direction=wrist-np.asarray(geometry['elbow']);direction=direction/np.linalg.norm(direction)
    distance=(xx-wrist[0])*direction[0]+(yy-wrist[1])*direction[1]
    # Retain the original surface in an overlapping wrist band. Put hand below
    # forearm when reassembling so that there is no fractional-alpha seam.
    arm=a.copy();hand=a.copy()
    arm[:,:,3]=(a[:,:,3]*np.clip((-distance)/8,0,1)).astype('uint8')
    hand[:,:,3]=(a[:,:,3]*np.clip((distance+24)/8,0,1)).astype('uint8')
    return Image.fromarray(arm),Image.fromarray(hand)

def transformed_hand(image,geometry,angles,canvas=(1464,1536),pad=220):
    matrix=arm_transforms(geometry,angles)[2].copy();matrix[0,2]+=pad
    raw=np.asarray(image).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
    raw=cv2.warpAffine(raw,matrix[:2],canvas,flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    raw[:,:,:3]*=255/np.maximum(raw[:,:,3:4],1)
    return Image.fromarray(np.clip(raw,0,255).astype('uint8'))
