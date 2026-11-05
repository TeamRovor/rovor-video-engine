"""Short rounded control isolation/geometry checks, not speech acceptance."""
import copy,json,unittest
from pathlib import Path
import cv2,numpy as np
from rounded_duration_cartoon_head import RoundedDurationCartoonHead,rounded_duration_budget,rounded_duration_jaw_weights
from independent_chin_cartoon_head import IndependentChinCartoonHead,chin_weights
from duration_cartoon_head import duration_jaw_weights
from rounded_cartoon_head import rounding_identity
from speech_planner import planned_weights
class RoundedDurationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text());cls.old=IndependentChinCartoonHead();cls.new=RoundedDurationCartoonHead()
 def test_budget_bounded_long_and_other_phones_unchanged(self):
  for d in [.04,.06,.1,.19,.22,.3]:
   p={'phonemes':[{'phone':'AO','value':'E','start':0,'end':d}]};b=rounded_duration_budget(d/2,p);self.assertGreaterEqual(b,.75);self.assertLessEqual(b,1)
   if d>=.22:self.assertEqual(b,1)
  self.assertEqual(rounded_duration_budget(.05,{'phonemes':[{'phone':'OW','value':'E','start':0,'end':.1}]}),1)
 def test_contacts_identity_and_plan_not_mutated(self):
  saved=copy.deepcopy(self.plan)
  for i in range(1059):
   t=i/48;w=planned_weights(t,self.plan,self.plan['fallbackCues']);old=duration_jaw_weights(t,self.plan,w);new=rounded_duration_jaw_weights(t,self.plan,w)
   np.testing.assert_array_equal(new[[0,1,3,4,6,7,8]],old[[0,1,3,4,6,7,8]]);self.assertGreaterEqual(new.min(),0);self.assertAlmostEqual(new.sum(),1)
  self.assertEqual(self.plan,saved)
 def test_width_corners_chin_and_skin_exact(self):
  t=742/48;old=duration_jaw_weights(t,self.plan);new=rounded_duration_jaw_weights(t,self.plan);shape=rounding_identity(t,self.plan);a=self.old.target_points(old,shape);self.new._rounded_reference=old
  try:
   b=self.new.target_points(new,shape);np.testing.assert_array_equal(a[:,0],b[:,0]);np.testing.assert_array_equal(a[32:],b[32:]);np.testing.assert_array_equal(a[[0,8]],b[[0,8]]);self.assertLess(np.ptp(b[:32,1]),np.ptp(a[:32,1]))
   self.old._chin_weights=chin_weights(t,self.plan);self.new._chin_weights=self.old._chin_weights
   np.testing.assert_array_equal(self.old.skin_target(old,a.copy()),self.new.skin_target(new,b.copy()))
  finally:self.new._rounded_reference=None;self.old._chin_weights=None;self.new._chin_weights=None
 def test_pure_controls_full_contact_and_inactive_render_exact(self):
  for i in range(9):np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
  for i in [0,680,738]:np.testing.assert_array_equal(self.old.at(i/48,self.plan),self.new.at(i/48,self.plan))
 def test_fallback_and_exception_cleanup(self):
  p=dict(self.plan);p['alignment']={'status':'rejected'};np.testing.assert_array_equal(rounded_duration_jaw_weights(15.45,p),duration_jaw_weights(15.45,p));np.testing.assert_array_equal(self.old.at(15.45,p),self.new.at(15.45,p))
  broken=dict(self.plan);del broken['words']
  with self.assertRaises(KeyError):self.new.at(15.45,broken)
  self.assertIsNone(self.new._rounded_reference)
if __name__=='__main__':unittest.main()
