"""Private catalog, ownership, duration and adversarial source tests.

Uses original synthetic fixture audio ONLY. No third-party music or paid tools.
"""
import json
import math
from pathlib import Path
import tempfile
import unittest
import wave

from audio_library import init_library, scan, inspect, AssetRejected, sha256


def generate_pcm(path, seconds=.4, hz=330):
    # Synthetic fixture, not released music or a Rovor sound effect.
    sample_rate=8000
    count=round(sample_rate*seconds)
    with wave.open(str(path),"wb") as wavefile:
        wavefile.setnchannels(1)
        wavefile.setsampwidth(2)
        wavefile.setframerate(sample_rate)
        # Deterministic original test bytes.
        wavefile.writeframes(b"".join(int(500*math.sin(2*math.pi*hz*i/sample_rate)).to_bytes(
            2, byteorder="little", signed=True) for i in range(count)))


class SoundLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        init_library(self.root)
        self.sfx=self.root/"SoundEffects"/"click.wav"
        self.music=self.root/"BackgroundMusic"/"underscore.wav"
        generate_pcm(self.sfx)
        generate_pcm(self.music,2)
        self.sfxmeta={
            "schemaVersion":1,
            "category":"sound-effect",
            "description":"An original quiet computer click",
            "eventTags":["browser-click","interface","subtle"],
            "mood":"curious",
            "license":{"kind":"original-owned","ownerConfirmedRights":True,
                       "source":"Original test sound recorded/created for this test"},
        }
        self.musicmeta={
            "schemaVersion":1,
            "category":"background-music",
            "description":"An original instrumental fixture only",
            "eventTags":["calm","dialogue-support"],
            "vocalContent":"instrumental",
            "loopable":False,
            "license":{"kind":"original-owned","ownerConfirmedRights":True,
                       "source":"Original test waveform created for this test"},
        }
        self.save()
    def tearDown(self):
        self.tmp.cleanup()
    def save(self):
        self.sfx.with_name("click.wav.asset.json").write_text(json.dumps(self.sfxmeta))
        self.music.with_name("underscore.wav.asset.json").write_text(json.dumps(self.musicmeta))
    def test_creates_two_dedicated_sound_folders_and_guides(self):
        self.assertTrue((self.root/"SoundEffects"/"_HOW_TO_ADD_AUDIO.txt").is_file())
        self.assertTrue((self.root/"BackgroundMusic"/"_HOW_TO_ADD_AUDIO.txt").is_file())
        init_library(self.root)
        self.assertTrue(self.sfx.exists())
        self.assertTrue(self.music.exists())
    def test_only_verified_original_records_selectable(self):
        report=scan(self.root)
        self.assertEqual(len(report["assets"]),2)
        self.assertEqual(len(report["rejected"]),0)
        self.assertFalse(report["approvedForAutomatedPublishing"])
        self.assertEqual(len({x["assetId"] for x in report["assets"]}),2)
        self.assertFalse(any(x["editorialApproved"] for x in report["assets"]))
        self.assertTrue((self.root/"catalog.json").is_file())
    def test_unverified_sound_is_rejected_without_sidecar(self):
        self.sfx.with_name("click.wav.asset.json").unlink()
        r=scan(self.root)
        self.assertEqual(len(r["assets"]),1)
        self.assertIn("Sidecar rights",r["rejected"][0]["reason"])
    def test_unsigned_rights_do_not_pass(self):
        self.sfxmeta["license"]["ownerConfirmedRights"]=False
        self.save()
        with self.assertRaises(AssetRejected):inspect(self.sfx,"sound-effect",self.root)
    def test_cc0_requires_evidence(self):
        self.sfxmeta["license"]["kind"]="cc0"
        self.sfxmeta["license"]["evidence"]=""
        self.save()
        with self.assertRaises(AssetRejected):inspect(self.sfx,"sound-effect",self.root)
        self.sfxmeta["license"]["evidence"]="Verified archived CC0 license declaration for exact file"
        self.save()
        self.assertEqual(inspect(self.sfx,"sound-effect",self.root)["licenseKind"],"cc0")
    def test_audio_sha_integrity(self):
        self.sfxmeta["sourceSha256"]=sha256(self.sfx)
        self.save()
        self.assertEqual(inspect(self.sfx,"sound-effect",self.root)["sha256"],
                         self.sfxmeta["sourceSha256"])
        generate_pcm(self.sfx,.6)
        with self.assertRaises(AssetRejected):inspect(self.sfx,"sound-effect",self.root)
    def test_wrong_category_rejected(self):
        self.sfxmeta["category"]="background-music"
        self.save()
        with self.assertRaises(AssetRejected):inspect(self.sfx,"sound-effect",self.root)
    def test_music_vocal_content_explicit(self):
        self.musicmeta["vocalContent"]="not sure"
        self.save()
        with self.assertRaises(AssetRejected):inspect(self.music,"background-music",self.root)
    def test_unsafe_audio_symlink_rejected(self):
        external=self.root/"outside.wav"
        generate_pcm(external)
        (self.root/"SoundEffects"/"evil.wav").symlink_to(external)
        r=scan(self.root)
        self.assertTrue(any("evil.wav"==x["filename"] for x in r["rejected"]))
    def test_music_folder_does_not_accept_90second_sfx(self):
        generate_pcm(self.sfx,90.1)
        self.save()
        with self.assertRaises(AssetRejected):inspect(self.sfx,"sound-effect",self.root)
    def test_no_invented_licensing_or_metadata_for_bare_music(self):
        self.music.with_name("underscore.wav.asset.json").unlink()
        r=scan(self.root)
        self.assertEqual(len(r["assets"]),1)
        self.assertTrue(any(x["category"]=="background-music" for x in r["rejected"]))

if __name__=="__main__":
    unittest.main()
