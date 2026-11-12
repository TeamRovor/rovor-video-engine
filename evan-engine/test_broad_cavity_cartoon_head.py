"""Broad-art component/occlusion checks, not perceptual acceptance."""
import unittest
import cv2,numpy as np
from PIL import Image
from broad_cavity_cartoon_head import BroadCavityCartoonHead
from light_lip_cartoon_head import LightLipCartoonHead
from layered_cartoon_head import ROOT,over

class BroadCavityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.old=LightLipCartoonHead();cls.new=BroadCavityCartoonHead()
    def test_closure_fv_and_full_round_controls_stay_exact(self):
        for i in [0,1,5,6,7]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_source_components_cover_opaque_reference(self):
        def pm(n):
            a=self.new.broad_art[n].astype('float32');a[:,:,:3]*=a[:,:,3:4]/255;return a
        joined=over(pm('cavity'),pm('rim'));ref=np.asarray(Image.open(ROOT/'broad-rig-v1/whole-reference.png'));core=ref[:,:,3]==255
        self.assertGreater(int(core.sum()),1000);self.assertGreaterEqual(float(joined[:,:,3][core].min()),254)
    def test_broad_change_keeps_geometry_and_nonoral_pixels(self):
        for i in [2,3,4,8]:
            w=np.eye(9)[i];np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w));outside=np.ones((512,512),bool);outside[290:405,175:305]=False
            np.testing.assert_array_equal(a[outside],b[outside]);self.assertGreater(np.count_nonzero(a!=b),0)
    def test_tongue_stays_behind_broad_matte(self):
        class NoTongue(BroadCavityCartoonHead):
            def tongue_surface(self,w,oral,shape_weights=None):return np.zeros((512,512,4),np.float32)
        w=np.eye(9)[8]*.8+np.eye(9)[2]*.2;target=self.new.target_points(w)
        aperture=sum(v*(self.new.geometry[k][7]-self.new.geometry[k][6]) for k,v in zip('XABCDEFGH',w));oral=self.new.oral_target(target,aperture)
        cavity=self.new.cavity_surface(w,oral);mask=self.new.interior_mask(cavity,w,oral)[:,:,0]
        changed=np.any(np.asarray(self.new.weights(w))!=np.asarray(NoTongue().weights(w)),axis=2)
        self.assertGreater(int(changed.sum()),0);self.assertEqual(int((changed&(mask==0)).sum()),0)
    def test_transition_samples_remain_valid(self):
        for s in [.1,.5,.9]:
            w=np.eye(9)[2]*(1-s)+np.eye(9)[5]*s;oral=self.new.oral_target(self.new.target_points(w),20);c=self.new.cavity_surface(w,oral)
            self.assertTrue(np.isfinite(c).all());self.assertGreaterEqual(float(c.min()),0);self.assertLessEqual(float(c[:,:,3].max()),255.0001)
            self.assertTrue(np.all(c[:,:,:3]<=c[:,:,3:4]+1e-4))
        self.assertEqual(self.new.contour_fallbacks,0)
