"""Physical sample-range/compositing regressions, not art acceptance."""
import unittest
import numpy as np
from bounded_cartoon_head import BoundedCartoonHead,bounded_premultiplied
from anchored_cartoon_head import AnchoredCartoonHead

def valid(test,raw):
    test.assertTrue(np.isfinite(raw).all())
    test.assertGreaterEqual(float(raw.min()),-1e-3)
    test.assertLessEqual(float(raw[:,:,3].max()),255.001)
    test.assertLessEqual(float((raw[:,:,:3]-raw[:,:,3:4]).max()),1e-3)

class SampleBoundsTests(unittest.TestCase):
    def test_valid_samples_exact_and_input_not_mutated(self):
        raw=np.array([[[0.,0.,0.,0.],[120.,30.,12.,128.],[240.,220.,200.,255.]]],np.float32);saved=raw.copy()
        np.testing.assert_array_equal(bounded_premultiplied(raw),raw)
        np.testing.assert_array_equal(raw,saved)
    def test_positive_alpha_overshoot_preserves_straight_colour(self):
        raw=np.array([[[288.,144.,72.,288.]]],np.float32);out=bounded_premultiplied(raw)
        np.testing.assert_allclose(out,[[[255,127.5,63.75,255]]],atol=1e-5)
    def test_negative_lobes_hidden_rgb_and_rgb_overshoot(self):
        raw=np.array([[[-10.,5.,8.,-1.],[20.,50.,90.,0.],[100.,-5.,20.,40.]]],np.float32)
        out=bounded_premultiplied(raw);valid(self,out)
        np.testing.assert_array_equal(out,[[[0,0,0,0],[0,0,0,0],[40,0,20,40]]])
    def test_uint8_input_is_supported(self):
        raw=np.array([[[100,20,0,128]]],np.uint8);np.testing.assert_array_equal(bounded_premultiplied(raw),raw)
    def test_actual_surface_samples_and_oral_composites_are_valid(self):
        test=self
        class Audit(BoundedCartoonHead):
            count=0;invalid_input_seen=False
            def constrain_surface(self,raw):
                self.invalid_input_seen|=bool(raw.min()<0 or raw[:,:,3].max()>255 or (raw[:,:,:3]-raw[:,:,3:4]).max()>0)
                out=super().constrain_surface(raw);valid(test,out);self.count+=1;return out
            def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
                for art in [face,cavity,teeth,tongue,contact,closed]:valid(test,art)
                out=super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w);valid(test,out);return out
        head=Audit()
        for w in list(np.eye(9))+[np.eye(9)[3]*.5+np.eye(9)[7]*.5]:head.weights(w)
        self.assertTrue(head.invalid_input_seen);self.assertGreater(head.count,80)
    def test_geometry_targets_and_mouth_closure_preserved(self):
        old=AnchoredCartoonHead();new=BoundedCartoonHead()
        for w in np.eye(9):np.testing.assert_array_equal(old.target_points(w),new.target_points(w))
        closed=np.asarray(new.weights(np.eye(9)[1]))[309:370,180:290,:3]
        self.assertEqual(int(((closed[:,:,0]>180)&(closed[:,:,1]>190)&(closed[:,:,2]>160)).sum()),0)
