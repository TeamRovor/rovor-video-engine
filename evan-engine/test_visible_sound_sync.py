"""Sound must correspond to actual original 2D motion, never keywords alone."""
import copy
import tempfile
import unittest
from pathlib import Path
from visible_sound_sync import verify
from test_directed_scene import fixture
from test_performance_tracks import authored


class PhysicalAudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.scenes,self.art=fixture(self.root)
        self.sheet={"status":"EDITORIAL_AUDIO_CUE_PROPOSALS",
            "sourceNarrationSeconds":40,"fps":60,
            "mixApproved":False,"noAutomaticPublishing":True,
            "effectCues":[{"shot":1,"timeFrame":120,
                           "animatedAssetId":"globe",
                           "type":"sound-effect",
                           "syncsWithVisibleAction":"Moving globe bounces against the illustrated desktop"}],
            "musicBeds":[]}
        self.actor=authored(40)
    def tearDown(self):
        self.tmp.cleanup()
    def gate(self):
        return verify(self.scenes,self.art,self.root,self.sheet,self.actor)
    def test_prop_motion_exists_in_both_outputs(self):
        r=self.gate()
        self.assertEqual(r["verifiedEffects"],1)
        self.assertGreater(r["evidence"][0]["verifiedMotion"]["portrait"],.008)
        self.assertFalse(r["creativeSyncApproved"])
    def test_unregistered_effect_object_not_acceptable(self):
        self.sheet["effectCues"][0]["animatedAssetId"]="fake-prop"
        with self.assertRaises(ValueError):self.gate()
    def test_static_desk_cannot_produce_impact(self):
        self.sheet["effectCues"][0]["animatedAssetId"]="desk"
        with self.assertRaises(ValueError):self.gate()
    def test_wrong_shot_number_rejected(self):
        self.sheet["effectCues"][0]["shot"]=4
        with self.assertRaises(ValueError):self.gate()
    def test_actor_action_requires_actual_joint_change(self):
        fx=self.sheet["effectCues"][0]
        fx["animatedAssetId"]="original-evan-rig"
        fx["syncActorChannels"]=["right","right_hand"]
        self.assertEqual(self.gate()["verifiedEffects"],1)
    def test_actor_mouth_or_unknown_eye_channel_not_fake_motion(self):
        fx=self.sheet["effectCues"][0]
        fx["animatedAssetId"]="original-evan-rig"
        fx["syncActorChannels"]=["evan.eyeline"]
        with self.assertRaises(ValueError):self.gate()
    def test_actor_which_isnt_performing_cannot_cause_sound(self):
        fx=self.sheet["effectCues"][0]
        fx["animatedAssetId"]="original-evan-rig"
        fx["syncActorChannels"]=["left"]
        with self.assertRaises(ValueError):self.gate()
    def test_unbound_actor_effect_rejected(self):
        self.sheet["effectCues"][0]["animatedAssetId"]="original-evan-rig"
        with self.assertRaises(ValueError):self.gate()
    def test_cue_manifest_must_match_real_narration_length(self):
        self.sheet["sourceNarrationSeconds"]=22
        with self.assertRaises(ValueError):self.gate()
    def test_silence_is_a_valid_artistic_decision(self):
        self.sheet["effectCues"]=[]
        report=self.gate()
        self.assertEqual(report["verifiedEffects"],0)
        self.assertFalse(report["mixRendered"])
    def test_effect_must_follow_physical_action_in_portrait(self):
        self.scenes["shots"][0]["compositions"]["portrait"]["elements"][-1]["keys"][-1]["x"]=.17
        with self.assertRaises(ValueError):self.gate()


if __name__=="__main__":unittest.main()
