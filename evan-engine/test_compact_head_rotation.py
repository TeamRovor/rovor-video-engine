"""Regress the exact original plate composition against bounded rotation."""
import unittest
import numpy as np
from PIL import Image
from cartoon_body import rotate_head_plate

class BoundedHeadRotationTests(unittest.TestCase):
    def test_alpha_boundary_and_shading_match_original_stage(self):
        head=Image.new('RGBA',(555,555))
        yy,xx=np.indices((555,555))
        raw=np.empty((555,555,4),dtype=np.uint8)
        raw[:,:,0]=(80+xx//6).astype('uint8')
        raw[:,:,1]=(50+yy//6).astype('uint8')
        raw[:,:,2]=(20+(xx+yy)//14).astype('uint8')
        raw[:,:,3]=np.where(((xx-277)**2+(yy-276)**2)<250**2,255,0).astype('uint8')
        head=Image.fromarray(raw,'RGBA')
        origin=(430,85);pivot=(720,445)
        for degrees in (-2,0,0.6,1.8):
            with self.subTest(degrees=degrees):
                reference=Image.new('RGBA',(1464,1536));reference.alpha_composite(head,origin)
                reference=reference.rotate(degrees,Image.Resampling.BICUBIC,center=pivot)
                updated=rotate_head_plate(head,origin,pivot,degrees)
                difference=np.abs(np.asarray(reference).astype('int16')-np.asarray(updated).astype('int16'))
                self.assertEqual(int(difference.max()),0)
                self.assertEqual(reference.getchannel('A').getbbox(),updated.getchannel('A').getbbox())

if __name__=='__main__':unittest.main()
