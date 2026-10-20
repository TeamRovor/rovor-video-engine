"""Uniform seal isolation/placement regressions, not artistic acceptance."""
import unittest
import cv2,numpy as np
from independent_chin_cartoon_head import IndependentChinCartoonHead
from uniform_seal_cartoon_head import UniformSealCartoonHead
from cartoon_head import POINTS
class UniformSealTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.old=IndependentChinCartoonHead();cls.new=UniformSealCartoonHead()
 def test_non_bilabial_controls_exact(self):
  for i in [0,2,3,4,5,6,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
 def test_uniform_parts_ignore_jaw_height_and_chin(self):
  a=POINTS['X'].copy();b=a.copy();b[[4,12],1]+=[-25,30];b[[45,46,47],1]+=15
  aa=self.new.closed_parts(a);bb=self.new.closed_parts(b)
  for n in aa:np.testing.assert_array_equal(aa[n],bb[n])
 def test_parts_and_mixed_surface_bounded_and_local(self):
  t=POINTS['A'].copy();previous=self.new._seal_mix
  try:
   for f in [.25,.5,1]:
    self.new._seal_mix=f;v=self.new.closed_surface(t);self.assertTrue(np.isfinite(v).all());self.assertGreaterEqual(v.min(),0);self.assertTrue(np.all(v[:,:,:3]<=v[:,:,3:4]+1e-4));self.assertLessEqual(v[:,:,3].max(),255.0001)
    ys,xs=np.where(v[:,:,3]>0);self.assertGreaterEqual(xs.min(),180);self.assertLessEqual(xs.max(),290);self.assertGreaterEqual(ys.min(),300);self.assertLessEqual(ys.max(),345)
  finally:self.new._seal_mix=previous
 def test_context_restores_after_render_failure(self):
  with self.assertRaises(TypeError):self.new.weights(np.eye(9)[1],unexpected_argument=1)
  self.assertEqual(self.new._seal_mix,0)
if __name__=='__main__':unittest.main()
