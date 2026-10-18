"""No-license-cost, non-overwriting 48 kHz original SFX generation tests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import wave

from generate_original_sfx import produce, SOUNDS, RATE
from audio_library import scan


class GeneratedSoundTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def test_seven_unique_source_hash_audio_clips(self):
        names=produce(self.root)
        self.assertEqual(len(names),len(SOUNDS))
        report=scan(self.root)
        self.assertEqual(len(report["assets"]),7,report["rejected"])
        self.assertEqual(len(report["rejected"]),0)
        self.assertEqual(len(set(row["sha256"] for row in report["assets"])),7)
        self.assertEqual({row["category"] for row in report["assets"]},{"sound-effect"})
        self.assertFalse(report["approvedForAutomatedPublishing"])
    def test_audio_is_48k_pcm_and_has_safe_dynamic_range(self):
        produce(self.root)
        for name in SOUNDS:
            with wave.open(str(self.root/"SoundEffects"/name),"rb") as f:
                self.assertEqual(f.getframerate(),RATE)
                self.assertEqual(f.getnchannels(),1)
                self.assertEqual(f.getsampwidth(),2)
                audio=f.readframes(f.getnframes())
                self.assertGreater(len(audio),1000)
                import struct
                integers=struct.unpack("<"+str(len(audio)//2)+"h",audio)
                self.assertGreater(max(abs(n) for n in integers),100)
                self.assertLess(max(abs(n) for n in integers),27000)
    def test_non_destructive_repeat(self):
        produce(self.root)
        path=self.root/"SoundEffects"/"soft-browser-click.wav"
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        second=produce(self.root)
        self.assertEqual(second,[])
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
    def test_do_not_assume_existing_foreign_file_is_in_house(self):
        (self.root/"SoundEffects").mkdir(parents=True)
        target=self.root/"SoundEffects"/"soft-browser-click.wav"
        target.write_bytes(b"someone else's audio is not automatically licensed")
        with self.assertRaises(ValueError):produce(self.root)
        self.assertEqual(target.read_bytes(),b"someone else's audio is not automatically licensed")
    def test_sidecar_has_source_hash_and_requires_listening(self):
        produce(self.root)
        sidecar=self.root/"SoundEffects"/"logo-shimmer.wav.asset.json"
        data=json.loads(sidecar.read_text())
        self.assertEqual(data["license"]["kind"],"original-owned")
        self.assertIn("no third-party",data["license"]["source"].lower())
        self.assertEqual(data["listeningReviewStatus"],"NOT_ARTISTICALLY_APPROVED")
        self.assertFalse(data["automatedPublishingApproved"])
        audio=self.root/"SoundEffects"/"logo-shimmer.wav"
        self.assertEqual(data["sourceSha256"],hashlib.sha256(audio.read_bytes()).hexdigest())
    def test_no_music_created_without_creative_direction(self):
        produce(self.root)
        songs=list((self.root/"BackgroundMusic").glob("*.wav"))
        self.assertFalse(songs)

if __name__=="__main__":
    unittest.main()
