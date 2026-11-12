import unittest,numpy as np
from postroll_brow_review import postroll_brow_accent
class PostrollBrowTests(unittest.TestCase):
 def test_recording_and_guard_stay_exactly_off_then_independent_sides_hold(self):
  end=22.047375
  for t in np.linspace(0,end+.08,1064):self.assertEqual(set(postroll_brow_accent(t,end).values()),{0.})
  for boundary in [0.,.25,22.047375]:self.assertEqual(set(postroll_brow_accent(boundary+.08,boundary).values()),{0.})
  first=postroll_brow_accent(end+.10,end);self.assertGreater(first['leftRaise'],0);self.assertEqual(first['rightRaise'],0)
  self.assertEqual(postroll_brow_accent(end+1,end),dict(leftRaise=3.,rightRaise=4.,leftTilt=-1.5,rightTilt=1.))
 def test_continuity_and_invalid_recording_end(self):
  rows=np.array([list(postroll_brow_accent(float(t),2).values())for t in np.arange(1.9,2.5,1/480)])
  self.assertLess(float(abs(np.diff(rows,axis=0)).max()),.06)
  for t,end in [(float('nan'),2),(2,float('inf')),(2,-1)]:
   with self.assertRaises(ValueError):postroll_brow_accent(t,end)
if __name__=='__main__':unittest.main()
