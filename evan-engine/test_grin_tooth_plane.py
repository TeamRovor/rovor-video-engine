"""Experimental crown registration checks, not an anatomy acceptance test."""
import unittest,cv2,numpy as np
from grin_tooth_plane import GrinToothPlane
from separated_oral_review import MaterialCapture,inner_arch,inner_oral_coverage
class GrinToothTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plane=GrinToothPlane();cls.head=MaterialCapture()
 def test_invalid_guides_rejected(self):
  for guide in [np.zeros((8,2)),np.full((9,2),np.nan),np.zeros((9,2))]:
   with self.assertRaises(ValueError):self.plane.pose(guide)
 def test_parent_translation_moves_complete_drawn_plane(self):
  self.head.weights(np.eye(9)[2]);upper=inner_arch(self.head.current_oral,True);before=self.plane.pose(upper);upper[:,1]+=10;after=self.plane.pose(upper)
  np.testing.assert_array_equal(after[10:],before[:-10]);self.assertTrue(np.isfinite(after).all());self.assertGreater(float(after[:,:,3].sum()),0)
 def test_actual_closed_lumen_leaks_no_crown(self):
  self.head.weights(np.eye(9)[1]);oral=self.head.current_oral;clipped=self.plane.pose(inner_arch(oral,True))*inner_oral_coverage(oral)
  self.assertEqual(np.count_nonzero(clipped),0)
if __name__=='__main__':unittest.main()
