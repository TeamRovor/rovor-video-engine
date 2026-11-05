import unittest
try:
 import numpy as np
 from cartoon_head import POINTS,TRIANGLES,area,CartoonHead
except ImportError:np=None

@unittest.skipIf(np is None,'Optional cartoon dependencies')
class CartoonHeadTests(unittest.TestCase):
 def test_no_triangle_flips_across_all_pose_pairs(self):
  for first in POINTS.values():
   for second in POINTS.values():
    for w in np.linspace(0,1,21):
     self.assertGreater(min(area(first*(1-w)+second*w,ids) for ids in TRIANGLES),0)
 def test_upper_face_is_exactly_stable(self):
  head=CartoonHead();base=np.asarray(head.weights(np.eye(9)[0]))
  for w in (np.eye(9)[3],np.eye(9)[6],np.ones(9)/9):
   result=np.asarray(head.weights(w));self.assertTrue(np.array_equal(base[:292],result[:292]))
 def test_blend_endpoints_and_small_motion_are_finite(self):
  head=CartoonHead()
  for w in (0,.001,.5,.999,1):
   weights=np.zeros(9);weights[0]=1-w;weights[3]=w
   result=np.asarray(head.weights(weights));self.assertEqual(result.shape,(512,512,4));self.assertTrue(np.isfinite(result).all())
