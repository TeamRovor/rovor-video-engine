import unittest,cv2,numpy as np
from smile_crease_plane import SmileCreasePlane
class SmileCreaseTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.plane=SmileCreasePlane();cls.upper=np.column_stack([np.linspace(192,285,9),np.linspace(328,318,9)]).astype('float32')
 def test_off_is_exactly_empty_and_bad_guides_rejected(self):
  self.assertEqual(np.count_nonzero(self.plane.pose(self.upper,0)),0)
  for strength in [-1,2,float('nan')]:
   with self.assertRaises(ValueError):self.plane.pose(self.upper,strength)
  for upper in [np.zeros((8,2)),np.full((9,2),np.nan),np.zeros((9,2))]:
   with self.assertRaises(ValueError):self.plane.pose(upper,1)
 def test_accent_follows_lip_parent_translation(self):
  before=self.plane.pose(self.upper,1);after=self.plane.pose(self.upper+[0,10],1);np.testing.assert_array_equal(after[10:],before[:-10]);self.assertGreater(float(before[:,:,3].sum()),0);self.assertTrue(np.isfinite(before).all())
if __name__=='__main__':unittest.main()
