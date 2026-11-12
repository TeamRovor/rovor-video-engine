"""Lighter source component/occlusion regressions, not artistic acceptance."""
import unittest
import cv2,numpy as np
from PIL import Image
from contour_cartoon_head import ContourCartoonHead
from light_lip_cartoon_head import LightLipCartoonHead
from layered_cartoon_head import ROOT,over

class LightLipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cv2.setNumThreads(1);cls.old=ContourCartoonHead();cls.new=LightLipCartoonHead()
    def test_nonrounded_controls_remain_exact(self):
        for i in [0,1,2,3,4,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
    def test_registered_parts_cover_source(self):
        def pm(name):
            a=self.new.round_art[name].astype('float32');a[:,:,:3]*=a[:,:,3:4]/255;return a
        joined=over(pm('cavity'),pm('rim'))
        reference=np.asarray(Image.open(ROOT/'light-lip-rig-v1/whole-reference.png'))
        core=reference[:,:,3]==255;self.assertGreater(int(core.sum()),100)
        self.assertGreaterEqual(float(joined[:,:,3][core].min()),254)
    def test_full_rounded_art_changes_only_oral_pixels(self):
        for i in [5,6]:
            w=np.eye(9)[i]
            np.testing.assert_array_equal(self.old.target_points(w),self.new.target_points(w))
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w))
            outside=np.ones((512,512),bool);outside[295:390,175:305]=False
            np.testing.assert_array_equal(a[outside],b[outside]);self.assertGreater(np.count_nonzero(a!=b),0)
    def test_transition_profiles_and_coverage(self):
        for s in [.1,.5,.9]:
            w=np.eye(9)[2]*(1-s)+np.eye(9)[5]*s
            oral=self.new.oral_target(self.new.target_points(w),20)
            cavity=self.new.cavity_surface(w,oral)
            self.assertTrue(np.isfinite(cavity).all());self.assertGreaterEqual(float(cavity.min()),0)
            self.assertTrue(np.all(cavity[:,:,:3]<=cavity[:,:,3:4]+1e-4))
        self.assertEqual(self.new.contour_fallbacks,0)
    def test_tongue_remains_independent_behind_matte(self):
        class NoTongue(LightLipCartoonHead):
            def tongue_surface(self,w,oral,shape_weights=None):return np.zeros((512,512,4),np.float32)
        w=np.eye(9)[8]*.4+np.eye(9)[5]*.6;target=self.new.target_points(w)
        aperture=sum(v*(self.new.geometry[k][7]-self.new.geometry[k][6]) for k,v in zip('XABCDEFGH',w))
        oral=self.new.oral_target(target,aperture);cavity=self.new.cavity_surface(w,oral)
        mask=self.new.interior_mask(cavity,w,oral)[:,:,0]
        a=np.asarray(self.new.weights(w));b=np.asarray(NoTongue().weights(w));changed=np.any(a!=b,axis=2)
        self.assertGreater(int(changed.sum()),0);self.assertEqual(int((changed&(mask==0)).sum()),0)
