"""Original 60fps audio-based mouth fallback never claims exact English phones."""
import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from build_acoustic_fallback_plan import build
from speech_planner import planned_weights


def cues():
    return {"mouthCues":[
        {"start":0,"end":.25,"value":"X"},
        {"start":.25,"end":.55,"value":"A"},
        {"start":.55,"end":.9,"value":"D"},
        {"start":.9,"end":1.2,"value":"X"}]}


class AcousticFallbackPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.wav=self.root/"original.wav"
        t=np.arange(16000*40,dtype=np.float32)/16000
        pcm=np.rint(.18*np.sin(2*np.pi*250*t)*32767).astype("<i2")
        with wave.open(str(self.wav),"wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(pcm.tobytes())
    def tearDown(self):
        self.tmp.cleanup()
    def test_production_duration_voice_remains_source_matched(self):
        plan=build(self.wav,cues())
        self.assertTrue(plan["isProductionEligibleByDuration"])
        self.assertEqual(plan["sourceNarrationSha256"],hashlib.sha256(self.wav.read_bytes()).hexdigest())
        self.assertFalse(plan["phonemeTimingVerified"])
        self.assertFalse(plan["pronunciationVerified"])
        self.assertEqual(len(plan["phonemes"]),0)
        self.assertEqual(len(plan["fallbackCues"]),4)
    def test_real_painted_mouth_targets_are_different(self):
        plan=build(self.wav,cues())
        mbp=planned_weights(.4,plan,plan["fallbackCues"])
        ah=planned_weights(.73,plan,plan["fallbackCues"])
        self.assertAlmostEqual(float(sum(mbp)),1,places=5)
        self.assertAlmostEqual(float(sum(ah)),1,places=5)
        self.assertGreater(float(mbp[1]),float(ah[1]))
        self.assertGreater(float(ah[4]),float(mbp[4]))
    def test_original_audio_evidence_matches_existing_renderer(self):
        from render_acting_video import verify_audio_plan
        plan=build(self.wav,cues())
        result=verify_audio_plan(plan,self.wav)
        self.assertTrue(result["rmsEnvelopeMatched"])
        self.assertFalse(result["phonemeTimingVerified"])
    def test_22_second_fixture_is_development_only(self):
        original=self.wav
        with wave.open(str(original),"rb") as f:
            pcm=f.readframes(16000*22)
        other=self.root/"22second.wav"
        with wave.open(str(other),"wb") as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
        plan=build(other,cues())
        self.assertFalse(plan["isProductionEligibleByDuration"])
    def test_audio_renamed_or_changed_is_not_same_shot(self):
        a=build(self.wav,cues())
        with wave.open(str(self.wav),"r+b") as f:
            f.setpos(3);f.writeframes(b"\0\0"*100)
        b=build(self.wav,cues())
        self.assertNotEqual(a["sourceNarrationSha256"],b["sourceNarrationSha256"])
    def test_invalid_cues_do_not_make_fake_speech(self):
        bad={"mouthCues":[{"start":1,"end":45,"value":"D"}]}
        with self.assertRaises(ValueError):
            build(self.wav,bad)
    def test_empty_shape_plan_does_not_guarantee_lip_sync(self):
        with self.assertRaises(ValueError):build(self.wav,{"mouthCues":[]})


if __name__=="__main__":
    unittest.main()
