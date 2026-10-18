"""Sound-placement safety, event-driven editing, dialogue and silence tests."""
import copy
import unittest
from soundtrack_editor import propose


def asset(aid, category, tags, vocal="instrumental", duration=2):
    return {"assetId":aid,"category":category,"eventTags":tags,
            "mood":tags[0],"durationSeconds":duration,
            "ownerConfirmedRights":True,"vocalContent":vocal}


def library():
    return {"schemaVersion":1,"approvedForAutomatedPublishing":False,
            "assets":[asset("sound-effect-aaa","sound-effect",["browser-click"],duration=.7),
                      asset("sound-effect-bbb","sound-effect",["object-impact"],duration=.45),
                      asset("background-music-ccc","background-music",["curious"],duration=34),
                      asset("background-music-ddd","background-music",["energetic"],"vocals",duration=55)]}


def story():
    shots=[]
    for i in range(4):
        direction={}
        if i==0:
            direction={"physicalEvents":[{"atSec":2,"eventTag":"browser-click",
                                         "visualAction":"Visible character presses browser icon",
                                         "overDialogue":"quiet-underlay"}],
                       "musicMood":"curious"}
        if i==1:
            direction={"physicalEvents":[{"atSec":15,"eventTag":"object-impact",
                                         "visualAction":"Animated icon lands on the desktop"}],
                       "musicMood":"curious"}
        if i==2:
            direction={"intentionalSilence":True,
                       "physicalEvents":[{"atSec":24,"eventTag":"browser-click",
                                         "visualAction":"Animated character taps browser"}],
                       "musicMood":"curious"}
        if i==3:
            direction={"musicMood":"energetic"}
        shots.append({"start":10*i,"end":10*(i+1),"scene":"shot-"+str(i),
                      "soundDirection":direction})
    return {"durationSec":40,"shots":shots}


class EditorialAudioTests(unittest.TestCase):
    def test_explicit_action_plus_audio_license_proposes_one_quiet_effect(self):
        x=propose(story(),library())
        self.assertEqual(len(x["effectCues"]),1)
        self.assertEqual(x["effectCues"][0]["assetId"],"sound-effect-aaa")
        self.assertEqual(x["effectCues"][0]["gainDbProposal"],-24)
        self.assertTrue(x["effectCues"][0]["underDialogue"])
        self.assertFalse(x["mixApproved"])
        self.assertTrue(x["noAutomaticPublishing"])
    def test_missing_timing_or_action_rejected(self):
        s=story()
        s["shots"][0]["soundDirection"]["physicalEvents"][0].pop("visualAction")
        with self.assertRaises(ValueError):propose(s,library())
        s=story()
        s["shots"][0]["soundDirection"]["physicalEvents"][0]["atSec"]=400
        with self.assertRaises(ValueError):propose(s,library())
    def test_intentional_silence_wins_over_music_and_effect(self):
        x=propose(story(),library())
        self.assertTrue(any(r["shot"]==3 and "silence" in r["reason"].lower()
                            for r in x["skippedForClarity"]))
        self.assertFalse(any(r["shot"]==3 for r in x["effectCues"]))
        self.assertFalse(any(r["shot"]==3 for r in x["musicBeds"]))
    def test_no_effects_without_animated_action_just_script_keywords(self):
        s=story()
        for shot in s["shots"]:
            shot.pop("soundDirection")
        x=propose(s,library())
        self.assertFalse(x["effectCues"])
        self.assertFalse(x["musicBeds"])
    def test_no_unlicensed_or_unknown_vocal_background_under_dialogue(self):
        x=propose(story(),library())
        self.assertTrue(any(q.get("musicMood")=="energetic" for q in x["missingAssets"]))
        self.assertFalse(any(m["assetId"]=="background-music-ddd" for m in x["musicBeds"]))
    def test_music_beds_under_voices_are_restrained(self):
        x=propose(story(),library())
        self.assertTrue(x["musicBeds"])
        self.assertEqual(x["musicBeds"][0]["gainDbProposal"],-30)
        self.assertTrue(x["musicBeds"][0]["underDialogue"])
        self.assertTrue(all(m["approvalRequired"] for m in x["musicBeds"]))
    def test_explicitly_missing_catalog_is_dry_plan_only(self):
        empty={"schemaVersion":1,"approvedForAutomatedPublishing":False,"assets":[]}
        x=propose(story(),empty)
        self.assertEqual(len(x["effectCues"]),0)
        self.assertEqual(len(x["musicBeds"]),0)
        self.assertGreater(len(x["missingAssets"]),0)
    def test_verified_nonspeech_interval_allows_louder_foley(self):
        s=story()
        s["verifiedSpeechIntervals"]=[{"start":0,"end":1},{"start":8,"end":40}]
        s["speechIntervalsHumanReviewed"]=True
        x=propose(s,library())
        self.assertEqual(x["effectCues"][0]["gainDbProposal"],-15)
        self.assertEqual(x["speechEvidence"],"human-reviewed-timed-speech")
    def test_unreviewed_silence_is_not_certified_from_machine_transcript(self):
        s=story()
        s["verifiedSpeechIntervals"]=[]
        s["speechIntervalsHumanReviewed"]=False
        x=propose(s,library())
        self.assertEqual(x["effectCues"][0]["gainDbProposal"],-24)
        self.assertIn("unreviewed",x["speechEvidence"])
    def test_would_not_spam_effects_in_two_seconds(self):
        s=story()
        s["shots"][0]["soundDirection"]["physicalEvents"].append({
            "atSec":2.6,"eventTag":"browser-click",
            "visualAction":"Character clicks another icon",
            "overDialogue":"quiet-underlay"})
        x=propose(s,library())
        self.assertEqual(len(x["effectCues"]),1)
        self.assertTrue(any("repetitive" in r["reason"] for r in x["skippedForClarity"]))
    def test_bad_or_nonmatching_timeline_rejected(self):
        s=story()
        s["shots"][1]["start"]=11
        with self.assertRaises(ValueError):propose(s,library())
        s=story()
        s["durationSec"]=22
        with self.assertRaises(ValueError):propose(s,library())
    def test_duplicate_asset_ids_rejected(self):
        lib=library()
        lib["assets"].append(copy.deepcopy(lib["assets"][0]))
        with self.assertRaises(ValueError):propose(story(),lib)

if __name__=="__main__":
    unittest.main()
