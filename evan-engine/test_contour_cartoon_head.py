"""Contour correspondence invariants; not perceptual animation acceptance."""
import unittest
import cv2
import numpy as np
from contour_cartoon_head import ContourCartoonHead, contour_maps, silhouette_profile
from rounded_art_cartoon_head import RoundedArtCartoonHead

class ContourTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cv2.setNumThreads(1);cls.old=RoundedArtCartoonHead();cls.new=ContourCartoonHead()
    def test_endpoints_remain_exact(self):
        for i in range(9):
            w=np.eye(9)[i]
            np.testing.assert_array_equal(self.old.weights(w),self.new.weights(w))
    def test_radial_maps_preserve_identity(self):
        a=np.zeros((100,100,4),np.float32)
        cv2.ellipse(a,(50,50),(26,17),0,0,360,(20,30,40,255),-1)
        maps=contour_maps(a,a,.4);yy,xx=np.mgrid[:100,:100].astype('float32')
        for mx,my in maps:
            np.testing.assert_allclose(mx,xx,atol=1e-5);np.testing.assert_allclose(my,yy,atol=1e-5)
    def test_boundary_correspondence_reduces_double_edge(self):
        a=np.zeros((100,100,4),np.float32);b=a.copy()
        cv2.ellipse(a,(44,50),(25,16),0,0,360,(20,30,40,255),-1)
        cv2.ellipse(b,(55,49),(18,23),0,0,360,(40,20,30,255),-1)
        fields=contour_maps(a,b,.5)
        moved=[self.new._remap(v,f) for v,f in zip((a,b),fields)]
        # At 50% alpha the two drawn silhouettes meet, while a dissolve leaves
        # disjoint edge bands. Quantify disagreement, not subjective quality.
        mismatch=lambda x,y:np.count_nonzero((x[:,:,3]>=127.5)!=(y[:,:,3]>=127.5))
        self.assertLess(mismatch(*moved),mismatch(a,b)*.12)
    def test_actual_transition_stays_valid_and_local(self):
        for s in [.1,.35,.5,.8,.99]:
            w=np.eye(9)[2]*(1-s)+np.eye(9)[5]*s
            oral=self.new.oral_target(self.new.target_points(w),20)
            cavity=self.new.cavity_surface(w,oral)
            mask=self.new.interior_mask(cavity,w,oral)
            self.assertTrue(np.isfinite(cavity).all());self.assertGreaterEqual(float(cavity.min()),0)
            self.assertLessEqual(float(cavity[:,:,3].max()),255.0001)
            self.assertTrue(np.all(cavity[:,:,:3]<=cavity[:,:,3:4]+1e-4))
            self.assertGreaterEqual(float(mask.min()),0);self.assertLessEqual(float(mask.max()),1)
            a=np.asarray(self.old.weights(w));b=np.asarray(self.new.weights(w))
            outside=np.ones((512,512),bool);outside[295:390,175:305]=False
            np.testing.assert_array_equal(a[outside],b[outside])
        self.assertEqual(self.new.contour_fallbacks,0)
    def test_tongue_stays_behind_aligned_interior(self):
        class NoTongue(ContourCartoonHead):
            def tongue_surface(self,w,oral,shape_weights=None):
                return np.zeros((512,512,4),np.float32)
        w=np.eye(9)[8]*.4+np.eye(9)[5]*.6
        target=self.new.target_points(w)
        aperture=sum(v*(self.new.geometry[k][7]-self.new.geometry[k][6]) for k,v in zip('XABCDEFGH',w))
        oral=self.new.oral_target(target,aperture)
        cavity=self.new.cavity_surface(w,oral)
        mask=self.new.interior_mask(cavity,w,oral)[:,:,0]
        a=np.asarray(self.new.weights(w));b=np.asarray(NoTongue().weights(w))
        changed=np.any(a!=b,axis=2)
        self.assertGreater(int(changed.sum()),0)
        self.assertEqual(int((changed&(mask==0)).sum()),0)
    def test_degenerate_art_rejected(self):
        with self.assertRaises(ValueError):silhouette_profile(np.zeros((30,30,4),np.float32))
