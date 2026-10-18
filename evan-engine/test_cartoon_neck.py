"""Attachment mechanics only; the collar stress test is visibly NOT accepted."""
import unittest
import numpy as np
from PIL import Image
from cartoon_body import ROOT
from cartoon_neck import neck_vertices,TRIANGLES,collar_torso
from painted_character import rotation

class NeckTests(unittest.TestCase):
    def test_collar_base_is_fixed_while_upper_end_follows_head(self):
        for jaw in (0,11,22):
            _,rest=neck_vertices(0,jaw)
            for angle in (-8,-2,2,8):
                _,posed=neck_vertices(angle,jaw)
                np.testing.assert_allclose(posed[-10:],rest[-10:],atol=.001)
                expected=(np.c_[rest[:10],np.ones(10)]@rotation([510,343],-angle).T)[:,:2]
                np.testing.assert_allclose(posed[:10],expected,atol=.001)
    def test_no_foldover_in_jaw_and_tilt_sweep(self):
        for jaw in np.linspace(0,22,12):
            for angle in np.linspace(-8,8,17):
                _,v=neck_vertices(angle,jaw);tri=v[np.asarray(TRIANGLES)]
                a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),1)
    def test_collar_edit_preserves_rgb_and_remote_alpha(self):
        original=Image.open(ROOT/'socket-rig/torso.png').convert('RGBA');before=np.asarray(original);after=np.asarray(collar_torso(original))
        np.testing.assert_array_equal(after[:,:,:3],before[:,:,:3])
        np.testing.assert_array_equal(after[395:],before[395:])
        np.testing.assert_array_equal(after[:,:435],before[:,:435])
        np.testing.assert_array_equal(after[:,578:],before[:,578:])
        blue=before[:,:,2].astype(int)>before[:,:,0].astype(int)+10
        np.testing.assert_array_equal(after[:,:,3][blue],before[:,:,3][blue])

    def test_extended_art_mesh_remains_attached_and_noninverting(self):
        for jaw in (0,11,22):
            _,rest=neck_vertices(0,jaw,(195,355),.25)
            for angle in np.linspace(-8,8,17):
                _,v=neck_vertices(angle,jaw,(195,355),.25)
                np.testing.assert_allclose(v[-10:],rest[-10:],atol=.001)
                tri=v[np.asarray(TRIANGLES)];a=tri[:,1]-tri[:,0];b=tri[:,2]-tri[:,0]
                self.assertGreater(float(np.min(a[:,0]*b[:,1]-a[:,1]*b[:,0])),1)
    def test_registered_art_discards_generated_face_and_supplies_base(self):
        art=np.asarray(Image.open(ROOT/'neck-art-rig/neck.png').convert('RGBA'))
        self.assertEqual(int(art[:380,:,3].max()),0)
        self.assertGreater(int(art[470,260,3]),240)
        self.assertGreater(int(art[470,320,3]),240)

    def test_redrawn_collar_is_local_and_has_empty_neck_opening(self):
        before=np.asarray(Image.open(ROOT/'socket-rig/torso.png').convert('RGBA'))
        after=np.asarray(Image.open(ROOT/'neck-art-rig/torso.png').convert('RGBA'))
        yy,xx=np.mgrid[:1536,:1024];outside=(xx<=430)|(xx>=590)|(yy<=280)|(yy>=400)
        np.testing.assert_array_equal(before[outside],after[outside])
        self.assertEqual(int(after[325,510,3]),0)
        self.assertGreater(int(after[350,450,3]),240)

if __name__=='__main__':unittest.main()
