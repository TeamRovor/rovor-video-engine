"""Timing and independent storyboard identity tests; artwork checked by Mac preview."""
import unittest
from storyboard_favicon import BEATS, DURATION, shot_at, smooth


class StoryboardTimingTests(unittest.TestCase):
    def test_full_22_second_coverage(self):
        self.assertEqual(BEATS[0][0],0.)
        self.assertAlmostEqual(BEATS[-1][1],DURATION)
        for a,b in zip(BEATS,BEATS[1:]):
            self.assertAlmostEqual(a[1],b[0])
            self.assertGreater(a[1],a[0])
        self.assertEqual(len(set(s[2] for s in BEATS)),6)

    def test_actual_scene_changes(self):
        for start,end,kind in BEATS:
            sample=(start+end)/2
            self.assertEqual(shot_at(sample)[2],kind)
            self.assertEqual(shot_at(start)[2],kind)

    def test_no_wrong_duration(self):
        with self.assertRaises(ValueError):shot_at(-0.01)
        with self.assertRaises(ValueError):shot_at(DURATION+0.1)

    def test_transition_easing_is_bounded(self):
        self.assertEqual(smooth(-999),0)
        self.assertEqual(smooth(999),1)
        self.assertAlmostEqual(smooth(.5),.5)
        self.assertTrue(all(smooth(i/100)<=smooth((i+1)/100) for i in range(100)))


if __name__=="__main__":
    unittest.main()
