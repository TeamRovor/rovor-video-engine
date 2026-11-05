"""Registered component/occlusion checks, not perceptual lip-sync acceptance."""
import unittest
import numpy as np
from PIL import Image
from bounded_cartoon_head import BoundedCartoonHead
from rounded_art_cartoon_head import RoundedArtCartoonHead,rounded_art_strength
from cartoon_head import POINTS
from layered_cartoon_head import over

class RoundedArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old=BoundedCartoonHead();cls.new=RoundedArtCartoonHead()
    def test_nonrounded_controls_remain_exact(self):
        for i in [0,1,2,3,4,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_source_components_cover_opaque_reference(self):
        def pm(name):
            a=self.new.round_art[name].astype('float32');a[:,:,:3]*=a[:,:,3:4]/255;return a
        joined=over(pm('cavity'),pm('rim'))
        reference=np.asarray(Image.open('evan-character/cartoon-v1/round-rig-v1/whole-reference.png'))
        core=reference[:,:,3]==255;self.assertGreater(int(core.sum()),100)
        self.assertGreaterEqual(float(joined[:,:,3][core].min()),254)
    def test_full_rounding_hides_teeth_even_at_low_energy(self):
        w=np.eye(9)[0]*.6+np.eye(9)[5]*.4
        self.assertAlmostEqual(rounded_art_strength(w),1)
        teeth=np.ones((1,1,4),np.float32)*255;tongue=teeth.copy();mask=np.ones((1,1,1),np.float32)
        clipped,retained=self.new.clip_interiors(teeth,tongue,mask,w)
        np.testing.assert_array_equal(clipped,np.zeros_like(teeth));np.testing.assert_array_equal(retained,tongue)
    def test_contacts_block_future_rounded_art(self):
        for i in [0,1,7,8]:self.assertEqual(rounded_art_strength(np.eye(9)[i],np.eye(9)[5]),0)
    def test_tongue_changes_only_inside_cavity_matte(self):
        class NoTongue(RoundedArtCartoonHead):
            def tongue_surface(self,w,oral,shape_weights=None):return np.zeros((512,512,4),np.float32)
        w=np.eye(9)[5];target=self.new.target_points(w);oral=self.new.oral_target(target,35)
        cavity=self.new.cavity_surface(w,oral);mask=self.new.interior_mask(cavity,w,oral)[:,:,0]
        a=np.asarray(self.new.weights(w));b=np.asarray(NoTongue().weights(w));changed=np.any(a!=b,axis=2)
        self.assertGreater(int(changed.sum()),0);self.assertEqual(int((changed&(mask==0)).sum()),0)
    def test_art_change_keeps_geometry_and_upper_face(self):
        for i in [5,6]:
            w=np.eye(9)[i];np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));outside=np.ones((512,512),bool);outside[300:385,180:295]=False
            np.testing.assert_array_equal(a[outside],b[outside]);self.assertGreater(int(np.count_nonzero(a!=b)),0)
