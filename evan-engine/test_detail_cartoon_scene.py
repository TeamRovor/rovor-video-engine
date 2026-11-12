"""Cue matching, control continuity and idle isolation; not acting approval."""
import copy,json,unittest
from pathlib import Path
import numpy as np
from detail_cartoon_scene import detail_event,detail_controls,DetailCartoonHead
from compact_cartoon_scene import compact_controls
from expressive_cartoon_head import brow_controls
class DetailTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.plan=json.loads((Path(__file__).resolve().parents[3]/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json').read_text())
 def test_only_contiguous_phrase_matches(self):
  self.assertEqual(detail_event(self.plan)['scriptIndices'],[43,44,45])
  p=copy.deepcopy(self.plan);p['words'][44]['word']='different';self.assertIsNone(detail_event(p))
 def test_outside_accent_and_missing_phrase_exact(self):
  for p in [self.plan,dict(words=[])]:
   for t in [0.,10.,14.,17.25,22.]:
    self.assertEqual(detail_controls(t,p),compact_controls(t,p))
 def test_continuity_bounds_and_plan_unchanged(self):
  before=copy.deepcopy(self.plan);rows=[]
  for t in np.arange(14.,17.3,1/480):
   c=detail_controls(float(t),self.plan);rows.append(c['right']+c['left']+c['index']+[c['head'],c['body_roll']])
  rows=np.asarray(rows);self.assertTrue(np.isfinite(rows).all());self.assertLess(abs(np.diff(rows,axis=0)).max(),.4);self.assertEqual(before,self.plan)
 def test_brows_use_same_isolated_event(self):
  h=DetailCartoonHead.__new__(DetailCartoonHead)
  for t in [0.,10.,14.,17.25,22.]:self.assertEqual(h.expression_control(t,self.plan),brow_controls(t,self.plan))
  self.assertGreater(h.expression_control(15.6,self.plan)['rightRaise'],3.5)
if __name__=='__main__':unittest.main()
