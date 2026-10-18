"""Authored original Evan comic acting beats, no perpetual random gestures."""
import unittest
from choreograph_story_beats import build
from performance_tracks import EvanPerformance


def sheet(duration=507.8726875):
    return {"schemaVersion":1,"sourceRig":"original-evan-layered",
            "durationSec":duration,"moments":[
                {"atFrame":120,"kind":"present",
                 "visualPurpose":"Evan points toward the globe leaving the browser",
                 "intensity":.8},
                {"atFrame":470,"kind":"recoil",
                 "visualPurpose":"The illustrated browser object unexpectedly bounces at Evan",
                 "intensity":.9},
                {"atFrame":900,"kind":"notice",
                 "visualPurpose":"Evan notices a second visual clue on the monitor",
                 "intensity":.6},
                {"atFrame":1400,"kind":"punchline",
                 "visualPurpose":"The original illustrated object makes a visual joke",
                 "intensity":.9},
            ]}


class NarrativeActingTests(unittest.TestCase):
    def test_actual_8min_original_recording_has_safe_fk_tracks(self):
        output=build(sheet())
        actor=EvanPerformance(output)
        self.assertEqual(actor.end,30473)
        self.assertEqual(output["storyBeatCount"],4)
        self.assertFalse(output["actingArtistApproved"])
        self.assertFalse(output["continuousIdleWiggling"])
        self.assertNotEqual(actor.at_frame(120)["right"],(0,0,0))
        self.assertEqual(actor.at_frame(300)["right"],(0.,0.,0.))
        self.assertEqual(actor.at_frame(30472)["right"],(0.,0.,0.))
    def test_real_original_hand_pose_changes_with_pointing_action(self):
        actor=EvanPerformance(build(sheet()))
        self.assertEqual(actor.at_frame(116)["right_hand"],"open")
        self.assertEqual(actor.at_frame(117)["right_hand"],"point")
        self.assertEqual(actor.at_frame(149)["right_hand"],"point")
        self.assertEqual(actor.at_frame(150)["right_hand"],"open")
    def test_recoil_has_anticipation_and_recovery(self):
        actor=EvanPerformance(build(sheet()))
        before=actor.at_frame(448)
        peak=actor.at_frame(470)
        after=actor.at_frame(530)
        self.assertTrue(peak["brow_left"]<0)
        self.assertNotEqual(before["right"],peak["right"])
        self.assertEqual(after["right"],(0.,0.,0.))
    def test_short_under_thirty_seconds_not_choreographed_for_delivery(self):
        with self.assertRaises(ValueError):build(sheet(22))
    def test_no_fictional_body_or_finger_gesture(self):
        spec=sheet()
        spec["moments"][0]["kind"]="full-body-spin-kick"
        with self.assertRaises(ValueError):build(spec)
    def test_gesture_cannot_fall_outside_original_voiceover(self):
        spec=sheet(40)
        spec["moments"][-1]["atFrame"]=2390
        with self.assertRaises(ValueError):build(spec)
    def test_repetitive_or_overlapping_events_rejected(self):
        spec=sheet()
        spec["moments"][1]["atFrame"]=138
        with self.assertRaises(ValueError):build(spec)
    def test_unnaturally_dense_generic_arm_waving_rejected(self):
        spec=sheet(30)
        spec["moments"]=[]
        for i in range(22):
            spec["moments"].append({"atFrame":60+i*60,"kind":"present",
                                     "visualPurpose":"An original hand gesture matches real action"})
        with self.assertRaises(ValueError):build(spec)
    def test_unmotivated_or_missing_story_direction_rejected(self):
        spec=sheet()
        spec["moments"][0]["visualPurpose"]="wave"
        with self.assertRaises(ValueError):build(spec)
    def test_intensity_never_exceeds_source_drawing_limits(self):
        spec=sheet()
        spec["moments"][0]["intensity"]=3
        with self.assertRaises(ValueError):build(spec)
    def test_source_original_evan_must_be_preserved(self):
        spec=sheet()
        spec["sourceRig"]="replacement-character"
        with self.assertRaises(ValueError):build(spec)


if __name__=="__main__":unittest.main()
