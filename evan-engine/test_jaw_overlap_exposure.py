"""Coverage regressions for authored cheek ownership, not art-quality tests."""
import unittest,numpy as np
from cartoon_head import POINTS
from guided_jaw_exposure import target_mesh
from jaw_overlap_exposure import upper_ownership
class UpperFaceOwnershipTests(unittest.TestCase):
 def fixture(self,opening):
  oral=POINTS['B'].copy();oral[8]=[194,325];oral[0]=[263,325];oral[20]=[228.5,opening];skin=POINTS['X'].copy();skin[46,1]=394
  return target_mesh(oral,skin)[0]
 def test_opening_never_removes_upper_nose_band(self):
  # The old remapped finite-grid mask lost a strip above its moved top row.
  for opening in [325.2,336,348,365]:
   mask=upper_ownership(self.fixture(opening));np.testing.assert_array_equal(mask[:315,190:280],1)
 def test_old_neck_is_removed_from_front_carrier(self):
  for opening in [325.2,348,365]:
   mask=upper_ownership(self.fixture(opening));np.testing.assert_array_equal(mask[410:480,200:340],0);self.assertGreaterEqual(float(mask.min()),0);self.assertLessEqual(float(mask.max()),1)
if __name__=='__main__':unittest.main()
