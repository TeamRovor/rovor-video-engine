"""Regression test: no Rovor user-visible MP4 shorter than 30s."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from video_handoff_gate import check,validate_pair,HandoffRejected,MIN_USER_VIDEO_SECONDS,MIN_USER_VIDEO_FRAMES


class DurationHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)
        self.videos={}
        self.reports={}
        for orient,dims in (("landscape",[1920,1080]),("portrait",[1080,1920])):
            movie=self.path/f"{orient}.mp4"
            movie.write_bytes(b"TEST ONLY NO REAL VIDEO"+orient.encode())
            report=self.path/f"{orient}.json"
            self.videos[orient]=movie
            self.reports[orient]=report
            self.write_report(orient,1800)
    def tearDown(self):
        self.tmp.cleanup()
    def write_report(self,orient,count):
        seconds=count/60
        movie=self.videos[orient]
        self.reports[orient].write_text(json.dumps({
            "video":movie.name,"videoSha256":hashlib.sha256(movie.read_bytes()).hexdigest(),
            "fps":60,"decodedFrames":count,
            "dimensions":[1920,1080] if orient=="landscape" else [1080,1920],
            "continuousTimestamps":True,"referenceCorrelation":.999,
            "offsetSamples":0,"decodedAudioSeconds":seconds,
            "referenceAudioSeconds":seconds,
            "phonemeTimingVerified":False,
        }))
    def pair(self):
        return validate_pair(self.videos["landscape"],self.reports["landscape"],
                             self.videos["portrait"],self.reports["portrait"])
    def test_30_exactly_allowed_technically(self):
        result=self.pair()
        self.assertEqual(result["minimumDecodedFrames"],1800)
        self.assertEqual(result["minimumVideoSeconds"],30)
        self.assertTrue(result["technicalHandoffReady"])
        self.assertFalse(result["publicationApproved"])
    def test_22_second_baseline_rejected(self):
        self.write_report("landscape",1323)
        self.write_report("portrait",1323)
        with self.assertRaises(HandoffRejected):self.pair()
    def test_3_second_diagnostic_rejected(self):
        self.write_report("landscape",198)
        self.write_report("portrait",198)
        with self.assertRaises(HandoffRejected):self.pair()
    def test_just_under_30_rejected(self):
        self.write_report("landscape",1799)
        with self.assertRaises(HandoffRejected):self.pair()
    def test_8_minute_dual_format_accepted(self):
        self.write_report("landscape",28800)
        self.write_report("portrait",28800)
        self.assertAlmostEqual(self.pair()["outputs"][1]["durationSec"],480)
    def test_missing_second_orientation(self):
        self.reports["portrait"].unlink()
        with self.assertRaises(HandoffRejected):self.pair()
    def test_mismatched_frame_count_rejected(self):
        self.write_report("portrait",1900)
        with self.assertRaises(HandoffRejected):self.pair()
    def test_wrong_sha_rejected(self):
        self.videos["landscape"].write_bytes(b"changed")
        with self.assertRaises(HandoffRejected):self.pair()
    def test_audio_mismatch_rejected(self):
        payload=json.loads(self.reports["landscape"].read_text())
        payload["referenceCorrelation"]=.5
        self.reports["landscape"].write_text(json.dumps(payload))
        with self.assertRaises(HandoffRejected):self.pair()
    def test_unverified_frame_continuity_rejected(self):
        payload=json.loads(self.reports["landscape"].read_text())
        payload["continuousTimestamps"]=False
        self.reports["landscape"].write_text(json.dumps(payload))
        with self.assertRaises(HandoffRejected):self.pair()
    def test_short_original_audio_cannot_be_padded(self):
        payload=json.loads(self.reports["landscape"].read_text())
        payload["referenceAudioSeconds"]=22.047
        self.reports["landscape"].write_text(json.dumps(payload))
        with self.assertRaises(HandoffRejected):self.pair()


if __name__ == "__main__":
    unittest.main()
