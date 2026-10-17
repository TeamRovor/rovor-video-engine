"""Small continuous source-art eyebrow acting with fixed glasses and hair.

Deform the eyebrow and surrounding skin together; no duplicated eyebrow pixels
or invented eye drawing. Larger expressions require independently drawn art.
"""
import cv2
import numpy as np
from PIL import Image


def eyebrow_maps(size, left=0., right=0.):
    if not all(np.isfinite(v) and abs(v)<=5 for v in (left,right)):
        raise ValueError('Eyebrow offsets must be finite and within five source pixels')
    yy,xx=np.indices((size,size),dtype='float32')
    offset=np.zeros_like(xx)
    for cx,value in ((186,left),(282,right)):
        radius=((xx-cx)/42)**2+((yy-215)/19)**2
        weight=np.maximum(0,1-radius)**3
        offset+=value*weight
    return xx,yy+offset


def upper_face(image, left=0., right=0.):
    if not left and not right:return image
    mx,my=eyebrow_maps(image.width,left,right)
    raw=np.asarray(image).astype('float32')
    raw[:,:,:3]*=raw[:,:,3:4]/255
    raw=cv2.remap(raw,mx,my,cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
    raw[:,:,:3]*=255/np.maximum(raw[:,:,3:4],1)
    return Image.fromarray(np.clip(raw,0,255).astype('uint8'))
