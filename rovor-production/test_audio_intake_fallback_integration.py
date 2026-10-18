"""Integration test: Rovor private WAV analysis creates original Evan face plan."""
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np

from audio_intake import original_evan_mouth_fallback


class ProductionFaceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.source=self.root/"original.wav"
        t=np.arange(16000*40,dtype=np.float32)/16000
        pcm=np.rint(.17*np.sin(2*np.pi*218*t)*32767).astype("<i2")
        with wave.open(str(self.source),"wb") as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
            f.writeframes(pcm.tobytes())
        self.cues={"mouthCues":[{"start":0,"end":.2,"value":"X"},
                                {"start":.2,"end":.5,"value":"A"},
                                {"start":.5,"end":.9,"value":"D"},
                                {"start":.9,"end":1.2,"value":"X"}]}
        (self.root/"rhubarb-mouth-DRAFT.json").write_text(json.dumps(self.cues))
        self.sha=hashlib.sha256(self.source.read_bytes()).hexdigest()
    def tearDown(self):
        self.tmp.cleanup()
    def test_integrated_original_face_data_is_persisted_without_modifying_source(self):
        result=original_evan_mouth_fallback(self.source,self.root)
        self.assertEqual(result["status"],"original-evan-mouth-fallback-renderable-needs-review")
        self.assertTrue(result["productionEligibleDuration"])
        self.assertFalse(result["phonemeTimingCertified"])
        plan=json.loads((self.root/result["plan"]).read_text())
        self.assertEqual(plan["sourceNarrationSha256"],self.sha)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.sha)
        self.assertFalse(plan["pronunciationVerified"])
        self.assertEqual(plan["kind"],"ROVOR_ORIGINAL_EVAN_ACOUSTIC_MOUTH_FALLBACK")
    def test_missing_rhubarb_doesnt_make_up_fake_phonemes(self):
        (self.root/"rhubarb-mouth-DRAFT.json").unlink()
        state=original_evan_mouth_fallback(self.source,self.root)
        self.assertFalse(state["phonemeTimingCertified"])
        self.assertEqual(state["status"],"unavailable-no-source-mouth-cues")
    def test_fake_extraneous_lip_audio_time_rejected(self):
        self.cues["mouthCues"][0]["end"]=50
        (self.root/"rhubarb-mouth-DRAFT.json").write_text(json.dumps(self.cues))
        with self.assertRaises(ValueError):original_evan_mouth_fallback(self.source,self.root)


if __name__=="__main__":unittest.main()
