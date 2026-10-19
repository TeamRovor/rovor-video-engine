"""Geometric occlusion regressions, not perceptual or anatomical acceptance."""
import unittest
import cv2,numpy as np
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from occluded_teeth_cartoon_head import OccludedTeethCartoonHead,tooth_retraction
from cartoon_head import POINTS

class OccludedTeethTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.old=BroadCavityCartoonHead();cls.new=OccludedTeethCartoonHead()
    def test_all_pure_controls_stay_exact(self):
        for i in range(9):np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_rounding_does_not_scale_tooth_material_alpha(self):
        w=np.eye(9)[8]*.6+np.eye(9)[5]*.4
        teeth=np.ones((1,1,4),np.float32)*255;tongue=teeth.copy();mask=np.ones((1,1,1),np.float32)
        a,b=self.new.clip_interiors(teeth,tongue,mask,w)
        np.testing.assert_array_equal(a,teeth);np.testing.assert_array_equal(b,tongue)
        self.assertEqual(self.new.teeth_rounding_visibility(w),1)
    def test_retraction_is_continuous_in_identity_and_oral_height(self):
        oral=POINTS['C'].copy();track=[tooth_retraction(np.eye(9)[8]*(1-s)+np.eye(9)[5]*s,oral) for s in np.linspace(0,1,101)]
        self.assertEqual(track[0],0);self.assertGreater(track[-1],8)
        self.assertTrue(np.all(np.diff(track)>=0))
        self.assertLess(float(np.diff(track).max()),track[-1]*.03)
    def test_full_round_teeth_hide_behind_matte(self):
        for i in [5,6]:
            for energy in [.4,1.]:
                w=np.eye(9)[0]*(1-energy)+np.eye(9)[i]*energy;target=self.new.target_points(w)
                aperture=sum(v*(self.new.geometry[k][7]-self.new.geometry[k][6]) for k,v in zip('XABCDEFGH',w));oral=self.new.oral_target(target,aperture)
                c=self.new.cavity_surface(w,oral);mask=self.new.interior_mask(c,w,oral)
                moved=self.new.teeth_surface(w,oral)*mask
                self.assertLess(float(moved[:,:,3].max()),1)
    def test_partial_change_is_local_with_identical_geometry(self):
        w=np.eye(9)[8]*.6+np.eye(9)[5]*.4
        np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
        a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));outside=np.ones((512,512),bool);outside[295:390,175:305]=False
        np.testing.assert_array_equal(a[outside],b[outside]);self.assertGreater(np.count_nonzero(a!=b),0)
    def test_moved_surface_stays_bounded_and_premultiplied(self):
        w=np.eye(9)[8]*.7+np.eye(9)[5]*.3;oral=self.new.oral_target(self.new.target_points(w),20)
        art=self.new.teeth_surface(w,oral)
        self.assertTrue(np.isfinite(art).all());self.assertGreaterEqual(float(art.min()),0);self.assertLessEqual(float(art[:,:,3].max()),255)
        self.assertTrue(np.all(art[:,:,:3]<=art[:,:,3:4]+1e-5))
