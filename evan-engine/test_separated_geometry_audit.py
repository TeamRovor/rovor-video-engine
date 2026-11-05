"""Captured targets must equal actual raster pipeline targets."""
import unittest,cv2,numpy as np
from types import SimpleNamespace
from unittest.mock import Mock
from separated_oral_review import SeparatedOralReview
from audit_separated_geometry import GeometryCapture,GeometryCaptured,capture,audit
from english_articulation import phone_gestures
from cartoon_head import POINTS

class GeometryAuditTests(unittest.TestCase):
 def test_oral_foldover_and_nonfinite_points_fail_even_with_valid_jaw(self):
  oral=POINTS['C'].copy();head=SimpleNamespace(at=Mock(side_effect=GeometryCaptured),current_oral=oral,exposure_skin=oral.copy(),current_fv=0.)
  rig=SimpleNamespace(head=head,jaw_target=Mock(return_value=(np.ones((169,2)),1.)))
  self.assertGreater(capture(rig,0,{})['minimumOralTriangleArea2'],0)
  oral[[17,18]]=oral[[18,17]]
  with self.assertRaisesRegex(ValueError,'Oral mesh triangle foldover'):capture(rig,0,{})
  oral[18,1]=np.nan
  with self.assertRaisesRegex(ValueError,'Non-finite oral geometry'):capture(rig,0,{})
 def test_capture_matches_full_pipeline_with_contact_and_open_pose(self):
  cv2.setNumThreads(1);real=SeparatedOralReview();fast=SeparatedOralReview();fast.head=GeometryCapture()
  for phone,value in [('F','G'),('AO','E')]:
   phones=[dict(start=.1,end=.5,phone=phone,value=value,word='test')];plan=dict(alignment={'status':'acoustic'},words=phones,phonemes=phones,gestures=phone_gestures(phones),audio=dict(step=.01,energy=[.8]*100),fallbackCues=[])
   image,row=real.at(.3,plan);got=capture(fast,.3,plan)
   np.testing.assert_array_equal(real.head.current_oral,fast.head.current_oral)
   np.testing.assert_array_equal(real.head.exposure_skin,fast.head.exposure_skin)
   np.testing.assert_array_equal(real.last_target,fast.jaw_target()[0])
   self.assertEqual(row['minimumTriangleArea2'],got['minimumTriangleArea2'])
 def test_short_phone_midpoint_is_included_between_output_frames(self):
  phones=[dict(start=.01,end=.015,phone='P',value='A',word='test')];plan=dict(alignment={'status':'acoustic'},words=phones,phonemes=phones,gestures=phone_gestures(phones),audio=dict(step=.01,energy=[.8]*100),fallbackCues=[])
  for duration in [0,-1,float('nan')]:
   with self.assertRaises(ValueError):audit(plan,duration)
  result=audit(plan,.04);self.assertTrue(result['allRequestedSamplesPassed']);self.assertEqual(len(result['rows']),3)
  self.assertAlmostEqual(result['rows'][-1]['time'],.0125);self.assertFalse(result['pixelOwnershipChecked'])

if __name__=='__main__':unittest.main()
