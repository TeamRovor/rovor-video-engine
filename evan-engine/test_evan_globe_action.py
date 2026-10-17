"""Kinematic quality checks for original Evan/globe animated action."""
import math
import unittest
from evan_globe_action import START,END,hop,framespec,clamped,ease,globe_action_controls,contact_pulse
from cartoon_body import narration_acting
from render_acting_video import actor_controls_fingerprint
from pathlib import Path


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

    def test_fingertip_contact_is_bounded_and_returns_to_normal_path(self):
        self.assertEqual(contact_pulse(3.50),0.)
        self.assertGreater(contact_pulse(3.94),.99)
        self.assertEqual(contact_pulse(4.40),0.)
        self.assertEqual(contact_pulse(5.2),0.)
        # The globe approaches the original posed index finger without being
        # used to replace the character or mouth rig.
        landing=framespec(3.94,False)
        self.assertGreater(landing['y'],520)
        self.assertLess(landing['y'],590)
        self.assertLess(landing['x'],1085)
        portrait=framespec(3.94,True)
        self.assertGreater(portrait['y'],1220)
        self.assertLess(portrait['y'],1335)
        self.assertEqual(framespec(3.50,True)['contact'],0.)

    def test_contact_path_is_continuous_at_60fps(self):
        for vertical in (False,True):
            previous=framespec(3.5,vertical)
            for frame in range(211,264):
                current=framespec(frame/60,vertical)
                distance=math.dist((previous['x'],previous['y']),
                                   (current['x'],current['y']))
                self.assertLess(distance,24)
                previous=current

    def test_body_cache_ignores_only_unrelated_scene_drawings(self):
        source=Path(__file__).with_name('evan_globe_action.py').read_text()
        original=actor_controls_fingerprint(source)
        # A change to scenery may reuse expensive, unchanged FK frames.
        altered_visual=source.replace('        self.set.draw(im,t)',
                                      '        self.set.draw(im,t)\n        pass')
        self.assertEqual(original,actor_controls_fingerprint(altered_visual))
        # A changed FK control must always invalidate the actor cache.
        replacement=source.replace('2.5*surprise','2.6*surprise')
        self.assertNotEqual(original,actor_controls_fingerprint(replacement))

    def test_rejects_unrelated_narration(self):
        with self.assertRaises(ValueError):framespec(-1)
        with self.assertRaises(ValueError):framespec(13)


if __name__=="__main__":unittest.main()
