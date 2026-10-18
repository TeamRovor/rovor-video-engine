"""Basic motion audit tests, including intentional freeze versus visible change."""
import unittest
import visual_motion_audit as m
class AuditTests(unittest.TestCase):
 def test_still_windows_flagged(self):
  data=[dict(time=i/2,changed_fraction=0.0,mae=0) for i in range(1,11)]
  summary=m._window_summary(data,0,5.5)
  self.assertEqual(summary['nearly_still_sample_fraction'],1.)
  self.assertEqual(summary['median_changed_fraction'],0.)
 def test_action_windows_not_flagged(self):
  data=[dict(time=i/2,changed_fraction=.04,mae=4) for i in range(1,11)]
  self.assertEqual(m._window_summary(data,0,5.5)['nearly_still_sample_fraction'],0.)
 def test_cut_detected(self):
  data=[dict(time=i/2,changed_fraction=.45 if i==5 else .03,mae=10) for i in range(1,11)]
  self.assertEqual(m._window_summary(data,0,5.5)['sharp_transition_count'],1)
 def test_excludes_out_of_window(self):
  data=[dict(time=t,changed_fraction=v,mae=2) for t,v in [(1,.1),(6,0)]]
  self.assertEqual(m._window_summary(data,0,5)['median_changed_fraction'],.1)
 def test_validates_window(self):
  for bad in [-1,0,float('nan')]:
   with self.assertRaises(ValueError):m.report('fake.mp4',window=bad)
 def test_constant_sample_area(self):
  self.assertEqual(m.W*m.H,m.FRAME_BYTES)
if __name__=='__main__': unittest.main(verbosity=2)