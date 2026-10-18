"""Source-preserving lip cue timing and false-phoneme confidence prevention."""
import unittest
from lip_cue_audit import validate


def cues(rows):
    return {"mouthCues":[{"start":a,"end":b,"value":c} for a,b,c in rows]}


class LipCueAuditTests(unittest.TestCase):
    def test_real_time_acoustic_cues_are_review_only(self):
        result=validate(cues([(0,.12,"X"),(.12,.3,"A"),(.3,.62,"D"),(.62,1,"X")]),30)
        self.assertEqual(result["cueCount"],4)
        self.assertTrue(result["mouthCueTimingTechnicallyValidated"])
        self.assertFalse(result["nativePhonemeAlignmentCertified"])
        self.assertFalse(result["wordPronunciationVerified"])
        self.assertFalse(result["publicationApproved"])
    def test_empty_is_honest_not_phonetic(self):
        result=validate(cues([]),40)
        self.assertEqual(result["cueCount"],0)
        self.assertEqual(result["nonRestDurationSec"],0)
        self.assertFalse(result["nativePhonemeAlignmentCertified"])
    def test_mouth_never_runs_past_source_audio(self):
        with self.assertRaises(ValueError):validate(cues([(0,24,"A")]),22.047375)
    def test_small_decoder_padding_clipped_and_flagged(self):
        r=validate(cues([(0,.3,"X"),(.3,22.08,"D")]),22.047375)
        self.assertEqual(r["shapeCues"][-1]["end"],22.04737)
        self.assertEqual(r["reviewFlags"][0]["reason"],"minor-end-padding-truncated")
    def test_bad_letters_rejected(self):
        with self.assertRaises(ValueError):validate(cues([(0,2,"J")]),30)
    def test_overlap_rejected(self):
        with self.assertRaises(ValueError):validate(cues([(0,2,"A"),(1.5,4,"D")]),30)
    def test_shorter_than_single_60fps_frame_marked_for_review(self):
        r=validate(cues([(0,.004,"A"),(.004,.05,"X")]),30)
        self.assertTrue(any(x["reason"]=="under-one-60fps-frame" for x in r["reviewFlags"]))
    def test_nonfinite_or_reverse_times_rejected(self):
        for row in ((0,float("inf"),"A"),(3,2,"A"),(-.2,.1,"B"),(1,1,"X")):
            with self.assertRaises(ValueError):validate(cues([row]),30)
    def test_9minute_metadata_and_60fps_boundaries(self):
        rows=[(n,n+.12,"A") for n in range(540)]
        r=validate(cues(rows),540)
        self.assertEqual(r["cueCount"],540)
        self.assertAlmostEqual(r["nonRestDurationSec"],64.8,places=2)
        self.assertFalse(r["publicationApproved"])


if __name__=="__main__":
    unittest.main()
