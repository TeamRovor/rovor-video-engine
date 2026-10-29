"""Fractional alpha accounting and read-only head instrumentation."""
import unittest
import cv2,numpy as np
from contact_crown_audit import CrownCaptureHead,crown_coverage,crown_continuation
from current_contact_exposure import CurrentContactHead
class ContactCrownTests(unittest.TestCase):
 def test_fractional_coverage_is_not_an_opaque_pixel_count(self):
  crown=np.zeros((1,2,4),np.float32);crown[0,:,3]=[128,255];mask=np.array([[.5,0]],np.float32);before=crown.copy();row=crown_coverage(crown,mask)
  self.assertAlmostEqual(row['beforeCarrierAlphaArea'],383/255);self.assertAlmostEqual(row['afterCarrierAlphaArea'],64/255);self.assertAlmostEqual(row['removedFraction'],319/383);np.testing.assert_array_equal(crown,before)
 def test_counterfactual_continuation_is_only_removed_source_material(self):
  crown=np.full((2,3,4),128,np.float32);mask=np.array([[0,.5,1],[.25,.75,1]],np.float32)
  np.testing.assert_array_equal(crown_continuation(crown,mask,0),np.zeros_like(crown));np.testing.assert_allclose(crown*mask[:,:,None]+crown_continuation(crown,mask,1),crown)
 def test_capture_preserves_mixed_and_full_contact_render(self):
  cv2.setNumThreads(1);old=CurrentContactHead();new=CrownCaptureHead()
  for fv in [.95,1]:
   w=np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv;expected=np.array(old.weights(w));actual=np.array(new.weights(w));np.testing.assert_array_equal(expected,actual);self.assertGreater(new.audit_crown[:,:,3].sum(),0)
if __name__=='__main__':unittest.main()
