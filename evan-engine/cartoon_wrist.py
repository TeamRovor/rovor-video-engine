"""Independent original-style pointing drawing attached to hierarchical wrist FK.

This is an experimental generated plate, never an automatic art approval.
"""
import math
import cv2
import numpy as np
from PIL import Image
from painted_character import arm_transforms


def without_hand(image, geometry, attachment=None, feather=8):
    """Keep the forearm with a short overlap beneath a replacement drawing."""
    raw = np.asarray(image).copy()
    wrist = np.asarray(geometry['wrist'] if attachment is None else attachment, float)
    axis = wrist - geometry['elbow']
    axis /= np.linalg.norm(axis)
    yy, xx = np.indices(raw.shape[:2])
    distance = (xx-wrist[0])*axis[0] + (yy-wrist[1])*axis[1]
    raw[:,:,3] = (raw[:,:,3] * np.clip((feather-distance)/feather, 0, 1)).astype('uint8')
    return Image.fromarray(raw)


class WristPlate:
    def __init__(self, image, metadata, geometry):
        self.geometry = geometry
        self.image = np.asarray(image.convert('RGBA')).astype('float32')
        self.image[self.image[:,:,3]<8]=0
        self.image[:,:,:3]=np.clip(self.image[:,:,:3]*np.asarray(metadata.get('paletteScale',[1,1,1])),0,255)
        self.image[:,:,:3] *= self.image[:,:,3:4] / 255
        anchor = np.asarray(metadata['attachment'], float)
        axis = np.asarray(metadata['axisPoint'], float) - anchor
        attachment = np.asarray(metadata.get('targetAttachment',geometry['wrist']), float)
        target = attachment - geometry['elbow']
        angle = math.atan2(target[1],target[0]) - math.atan2(axis[1],axis[0])
        c,s = math.cos(angle)*metadata['scale'], math.sin(angle)*metadata['scale']
        self.base = np.array([[c,-s,0],[s,c,0],[0,0,1]], dtype='float32')
        self.base[:2,2] = attachment - self.base[:2,:2] @ anchor
        self.anchor = np.r_[anchor,1]
        x0,y0,x1,y1=Image.fromarray(self.image[:,:,3].astype('uint8')).getbbox()
        self.corners = np.array([[x0,y0,1],[x1,y0,1],[x1,y1,1],[x0,y1,1]], dtype='float32')

    def transform(self, angles):
        return arm_transforms(self.geometry, angles)[2] @ self.base

    def render(self, angles):
        matrix = self.transform(angles)
        corners = (self.corners @ matrix.T)[:,:2]
        lo = np.floor(corners.min(axis=0)-2).astype(int)
        hi = np.ceil(corners.max(axis=0)+2).astype(int)
        matrix = matrix[:2].copy();matrix[:,2] -= lo
        raw = cv2.warpAffine(self.image, matrix, tuple(hi-lo), flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_CONSTANT)
        raw[:,:,:3] *= 255 / np.maximum(raw[:,:,3:4],1)
        return Image.fromarray(np.clip(raw,0,255).astype('uint8')), tuple(lo)
