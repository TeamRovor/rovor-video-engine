"""Independent anchor/control regressions, not artistic or timing acceptance."""
import json,unittest
from pathlib import Path
import cv2,numpy as np
from independent_chin_cartoon_head import IndependentChinCartoonHead,chin_weights,CHIN_ANCHORS
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
from duration_cartoon_head import duration_jaw_weights
class IndependentChinTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cv2.setNumThreads(1);cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text());cls.old=DrawnDentalCartoonHead();cls.new=IndependentChinCartoonHead()
 def test_only_three_skin_anchors_change(self):
  t=742/48;w=duration_jaw_weights(t,self.plan);target=self.old.target_points(w);self.new._chin_weights=chin_weights(t,self.plan)
  try:
   original=target.copy();changed=target.copy();a=self.old.skin_target(w,original);b=self.new.skin_target(w,changed)
   np.testing.assert_array_equal(original,changed)
  finally:self.new._chin_weights=None
  untouched=np.ones(len(a),bool);untouched[CHIN_ANCHORS]=False;np.testing.assert_array_equal(a[untouched],b[untouched]);self.assertGreater(abs(a[46,1]-b[46,1]),.1)
 def test_direct_controls_and_settled_rest_exact(self):
  for i in [0,1,7,8]:np.testing.assert_array_equal(self.old.weights(np.eye(9)[i]),self.new.weights(np.eye(9)[i]))
  np.testing.assert_array_equal(self.old.at(23,self.plan),self.new.at(23,self.plan))
 def test_release_chin_step_reduced_without_negative_weights(self):
  old=[];new=[]
  for i in range(737,747):
   a=duration_jaw_weights(i/48,self.plan);b=chin_weights(i/48,self.plan);self.assertGreaterEqual(b.min(),0);self.assertAlmostEqual(b.sum(),1)
   old.append(self.old.target_points(a)[46,1]);new.append(self.new.target_points(b)[46,1])
  self.assertLess(max(abs(np.diff(new))),max(abs(np.diff(old)))*.8)
 def test_context_resets_after_failure_and_fallback_is_unchanged(self):
  p=dict(self.plan);p['alignment']={'status':'rejected'};self.assertIsNone(chin_weights(14,p))
  broken=dict(self.plan);del broken['words']
  with self.assertRaises(KeyError):self.new.at(1,broken)
  self.assertIsNone(self.new._chin_weights)
 def test_unaligned_render_falls_back_exactly(self):
  p=dict(self.plan);p['alignment']={'status':'rejected'}
  np.testing.assert_array_equal(self.old.at(14,p),self.new.at(14,p))
if __name__=='__main__':unittest.main()
