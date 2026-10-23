"""Fresh material/geometry, geometric crown occlusion and source safety."""
import unittest,cv2,numpy as np
from separated_oral_review import SeparatedOralReview

class SeparatedOralTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=SeparatedOralReview()
 def pose(self,fv):
  w=np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv;baseline=self.rig.head.weights(w);return self.rig.assemble(baseline)
 def test_contact_endpoint_is_fresh_and_continuous(self):
  source=self.rig.lower.source.copy()
  for pair in [(0,1e-7),(1-1e-7,1)]:
   images=[]
   for fv in pair:
    self.rig.head.last_painted_target=np.full((48,2),np.nan);im,row=self.pose(fv);images.append(np.array(im).astype(int));self.assertGreater(row['minimumTriangleArea2'],0);self.assertEqual(len(row['planes']),9);self.assertFalse(row['bakedMouthInUpperCarrier'])
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
  np.testing.assert_array_equal(source,self.rig.lower.source)
 def test_crown_is_clipped_geometrically_and_upper_identity_preserved(self):
  im,row=self.pose(.4);parts=self.rig.last_parts;mask=self.rig.head.review_interior[:,:,0]
  self.assertEqual(float(parts['Rigid upper incisors'][:,:,3][mask==0].max()),0)
  self.assertTrue(row['upper288Exact']);self.assertLessEqual(row['noseMaximumChange'],1)
  self.assertGreater(float(parts['Independent lower lip'][:,:,3].sum()),0)
  self.assertGreater(float(parts['Independent upper-lip cap'][:,:,3].sum()),0)
 def test_material_capture_does_not_change_original_head_output(self):
  from current_contact_exposure import CurrentContactHead
  original=CurrentContactHead();w=np.eye(9)[3]*.6+np.eye(9)[7]*.4
  np.testing.assert_array_equal(np.array(original.weights(w)),np.array(self.rig.head.weights(w)))
 def test_unseparated_dental_overlay_rejects_explicitly(self):
  self.rig.head.dental_fraction=1
  try:
   with self.assertRaisesRegex(ValueError,'TH/DH'):self.pose(0)
  finally:self.rig.head.dental_fraction=0

if __name__=='__main__':unittest.main()
