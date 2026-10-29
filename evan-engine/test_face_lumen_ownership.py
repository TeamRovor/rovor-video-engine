"""The actual mouth lumen owns its interior, including expanded corners."""
import unittest,cv2,numpy as np
from separated_oral_review import SeparatedOralReview,face_ownership,inner_oral_coverage
class LumenOwnershipTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=SeparatedOralReview()
 def test_carrier_cannot_cover_actual_lumen_across_base_poses(self):
  for i in range(9):
   self.rig.head.weights(np.eye(9)[i]);oral=self.rig.head.current_oral;target,_=self.rig.jaw_target();mask=face_ownership(target,oral);lumen=inner_oral_coverage(oral)[:,:,0]
   self.assertEqual(np.count_nonzero(mask[lumen==1]),0)
   self.assertTrue(np.all(mask[40:288,90:425]==1));self.assertGreaterEqual(float(mask.min()),0);self.assertLessEqual(float(mask.max()),1)
 def test_widened_corner_excludes_skin_and_preserves_protected_face(self):
  self.rig.head.weights(np.eye(9)[2]);oral=self.rig.head.current_oral.copy();left,right=oral[8,0],oral[0,0];oral[:32,0]=187+(oral[:32,0]-left)*103/(right-left);self.rig.head.current_oral=oral;target,_=self.rig.jaw_target();mask=face_ownership(target,oral);lumen=inner_oral_coverage(oral)[:,:,0]
  right_corner=(np.indices(mask.shape)[1]>263)&(lumen==1);self.assertGreater(np.count_nonzero(right_corner),0);self.assertEqual(np.count_nonzero(mask[right_corner]),0);self.assertTrue(np.all(mask[40:288,90:425]==1))
if __name__=='__main__':unittest.main()
