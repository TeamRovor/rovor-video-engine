"""Kinematic quality checks for original Evan/globe animated action."""
import math
import unittest
from evan_globe_action import START,END,hop,framespec,clamped,ease,globe_action_controls
from cartoon_body import narration_acting


class GlobeActionTests(unittest.TestCase):
    def test_covers_original_speech_segment(self):
        self.assertAlmostEqual(START,141/60)
        self.assertAlmostEqual(END,339/60)
        for t in [START,2.75,3.,4.,4.5,5.,END]:
            self.assertTrue(math.isfinite(hop(t)[0]))

    def test_physically_distinct_beats(self):
        self.assertEqual(hop(2.5)[-1],"hatch")
        self.assertEqual(hop(3.45)[-1],"run")
        self.assertEqual(hop(4.65)[-1],"dodge")
        self.assertEqual(hop(5.2)[-1],"settle")

    def test_real_screen_motion_not_static_character(self):
        for vertical in (False,True):
            a=framespec(2.35,vertical)
            b=framespec(2.95,vertical)
            c=framespec(3.6,vertical)
            d=framespec(4.7,vertical)
            self.assertGreater(abs(b["x"]-a["x"]),200)
            self.assertGreater(abs(c["x"]-b["x"]),100)
            self.assertGreater(abs(d["x"]-c["x"]),70)
            self.assertGreater(b["r"]-a["r"],50)

    def test_continuity_of_path_except_directed_skid(self):
        for vertical in (False,True):
            for frame in range(142,339):
                t=frame/60
                prev=framespec(t-1/60,vertical)
                curr=framespec(t,vertical)
                self.assertLess(math.dist((prev["x"],prev["y"]),
                                          (curr["x"],curr["y"])),65)

    def test_bounded_easing(self):
        self.assertEqual(ease(-1),0)
        self.assertEqual(ease(2),1)
        for i in range(100):
            self.assertLessEqual(ease(i/100),ease((i+1)/100))

    def test_action_is_actual_independent_joint_motion(self):
        # The old body held right elbow at -25 degrees for over a second.
        # New staging actively retracts, points at, and misses the moving prop.
        surprise=globe_action_controls(3.2)
        reach=globe_action_controls(3.85)
        self.assertGreater(abs(surprise['right'][1]-reach['right'][1]),12)
        self.assertNotEqual(surprise['head'],reach['head'])
        self.assertEqual(globe_action_controls(2.35),narration_acting(2.35))
        self.assertEqual(globe_action_controls(5.65),narration_acting(5.65))

    def test_joint_velocities_are_continuous_and_bounded(self):
        previous=None
        for frame in range(round(START*60),round(END*60)):
            c=globe_action_controls(frame/60)
            self.assertLess(abs(c['head']),5)
            self.assertLess(abs(c['body_roll']),3)
            self.assertEqual(c['right_hand'],narration_acting(frame/60)['right_hand'])
            for side in ('left','right'):
                self.assertTrue(all(abs(angle)<40 for angle in c[side]))
            if previous is not None:
                self.assertLess(max(abs(a-b) for side in ('left','right')
                                    for a,b in zip(c[side],previous[side])),1.5)
            previous=c

    def test_rejects_unrelated_narration(self):
        with self.assertRaises(ValueError):framespec(-1)
        with self.assertRaises(ValueError):framespec(13)


if __name__=="__main__":unittest.main()
