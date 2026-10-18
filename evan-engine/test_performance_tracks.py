"""Longform real Evan control-channel tests, no fake rig motions."""
import math
import unittest
from performance_tracks import EvanPerformance,validate


def authored(duration=507.8726875):
    end=math.ceil(duration*60-1e-9)
    return {"schemaVersion":1,"sourceRig":"original-evan-layered",
            "durationSec":duration,
            "channels":{
                "right.shoulder":[{"frame":0,"degrees":0},
                    {"frame":120,"degrees":7},{"frame":180,"degrees":7,"interpolation":"hold"},
                    {"frame":240,"degrees":0},{"frame":end,"degrees":0}],
                "right.elbow":[{"frame":0,"degrees":0},{"frame":120,"degrees":-12},
                    {"frame":240,"degrees":0},{"frame":end,"degrees":0}],
                "head":[{"frame":0,"degrees":0},{"frame":120,"degrees":1.7},
                    {"frame":240,"degrees":0},{"frame":end,"degrees":0}],
                "brow_left":[{"frame":0,"degrees":0},{"frame":120,"degrees":2},
                    {"frame":240,"degrees":0},{"frame":end,"degrees":0}]
            },
            "rightHandKeys":[{"frame":0,"pose":"open"},{"frame":110,"pose":"relaxed"},
                             {"frame":135,"pose":"point"},{"frame":240,"pose":"open"}]}


class LongformActingTests(unittest.TestCase):
    def test_exact_frame_range_for_actual_eight_minute_duration(self):
        a=EvanPerformance(authored())
        self.assertEqual(a.end,30473)
        self.assertEqual(len(a.at_frame(30473)["right"]),3)
        self.assertEqual(a.at_frame(30473)["right_hand"],"open")
        self.assertTrue(all(abs(x)<1e-6 for x in a.at_frame(30473)["right"]))
    def test_holds_do_not_repeat_wave_forever(self):
        a=EvanPerformance(authored())
        self.assertEqual(a.at_frame(145)["right_hand"],"point")
        self.assertAlmostEqual(a.at_frame(180)["right"][0],7,places=5)
        self.assertAlmostEqual(a.at_frame(195)["right"][0],7,places=5)
        self.assertAlmostEqual(a.at_frame(241)["right"][0],0,places=5)
        self.assertAlmostEqual(a.at_frame(19000)["right"][0],0,places=5)
        self.assertFalse(any(a.at_frame(23000)["right"]))
    def test_independent_joint_tracks_and_brows(self):
        a=EvanPerformance(authored())
        start=a.at_frame(0)
        active=a.at_frame(120)
        self.assertNotEqual(active["right"],start["right"])
        self.assertTrue(active["brow_left"]>0)
        self.assertEqual(active["left"],(0,0,0))
        self.assertLessEqual(abs(active["head"]),2.5)
    def test_does_not_interpolate_discrete_hand_drawing(self):
        a=EvanPerformance(authored())
        self.assertEqual(a.at_frame(109)["right_hand"],"open")
        self.assertEqual(a.at_frame(110)["right_hand"],"relaxed")
        self.assertEqual(a.at_frame(134)["right_hand"],"relaxed")
        self.assertEqual(a.at_frame(135)["right_hand"],"point")
    def test_bounded_art_motions(self):
        x=authored()
        x["channels"]["right.elbow"][1]["degrees"]=90
        with self.assertRaises(ValueError):EvanPerformance(x)
        x=authored()
        x["channels"]["head"][1]["degrees"]=7
        with self.assertRaises(ValueError):EvanPerformance(x)
    def test_false_nonexistent_controls_rejected(self):
        x=authored()
        x["channels"]["evan.eyeline"]=[{"frame":0,"degrees":0},{"frame":30473,"degrees":0}]
        with self.assertRaises(ValueError):EvanPerformance(x)
    def test_duplicate_and_unsorted_keyframes_rejected(self):
        x=authored()
        x["channels"]["head"][2]["frame"]=120
        with self.assertRaises(ValueError):EvanPerformance(x)
    def test_every_track_must_cover_entire_original_narration(self):
        x=authored()
        x["channels"]["head"][-1]["frame"]=240
        with self.assertRaises(ValueError):EvanPerformance(x)
    def test_never_accepts_under30s_narration(self):
        x=authored(22)
        with self.assertRaises(ValueError):EvanPerformance(x)
    def test_60fps_and_explicit_approximation(self):
        a=EvanPerformance(authored())
        self.assertEqual(a.at_seconds(120/60)["head"],a.at_frame(120)["head"])
        with self.assertRaises(ValueError):a.at_frame(30474)
        with self.assertRaises(ValueError):a.at_seconds(float("nan"))


if __name__=="__main__":unittest.main()
