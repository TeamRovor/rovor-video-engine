"""Original PCM exactness, local phoneme timing and safe chapter packaging."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import chapter_package as p
import longform_chapters as c
from speech_plan_gate import audit as acoustic_audit
from tests.test_longform_chapters import speech_fixture


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.wav = self.root / "narration.wav"
        self.plan = self.root / "phones.json"
        self.chapters = self.root / "manifest.json"
        self.destination = self.root / "native-payloads"

    def make(self, duration=85.103):
        samples = round(duration * 16000)
        # Vary the PCM amplitude by second: content preservation matters, not
        # just matching WAV frame counts full of zero samples.
        with wave.open(str(self.wav), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            for i in range(samples // 16000):
                output.writeframesraw(int(i % 1700).to_bytes(2, "little") * 16000)
            output.writeframesraw(b"\x38\x00" * (samples % 16000))
            output.writeframes(b"")
        self.plan.write_text(json.dumps(speech_fixture(samples / 16000)))
        manifest = c.plan_chapters(self.wav, self.plan)
        self.chapters.write_text(json.dumps(manifest))
        return manifest

    def pcm(self, path):
        with wave.open(str(path), "rb") as f:
            self.assertEqual((f.getnchannels(), f.getsampwidth(), f.getframerate()),
                             (1, 2, 16000))
            return f.readframes(f.getnframes())

    def test_four_minute_twenty_three_preserves_exact_source_and_phones(self):
        planned = self.make(262.687313)
        wav_before, phone_before = self.wav.read_bytes(), self.plan.read_bytes()
        manifest = p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertEqual(manifest["chapterCount"], planned["chapterCount"])
        self.assertEqual(manifest["totalVideoFrames"], planned["totalFrames"])
        self.assertFalse(manifest["nativeMohoRendered"])
        self.assertFalse(manifest["publishable"])
        self.assertEqual(manifest["originalPcmSha256"], manifest["reassembledChapterPcmSha256"])
        self.assertEqual(self.wav.read_bytes(), wav_before)
        self.assertEqual(self.plan.read_bytes(), phone_before)
        self.assertEqual(self.pcm(self.wav), b"".join(
            self.pcm(self.destination / row["directory"] / "narration.wav")
            for row in manifest["chapters"]))
        seen = []
        for row in manifest["chapters"]:
            folder = self.destination / row["directory"]
            local = json.loads((folder / "acoustic-plan.json").read_text())
            chapter = json.loads((folder / "chapter.json").read_text())
            self.assertEqual(chapter["narrationPcmSha256"], row["narrationPcmSha256"])
            self.assertEqual(chapter["speechPlanSha256"], row["speechPlanSha256"])
            self.assertEqual(chapter["localMohoFirstFrame"], 1)
            self.assertEqual(chapter["localMohoLastFrame"], row["frameCount"])
            self.assertEqual(acoustic_audit(local, row["sampleCount"] / 16000, 60,
                                           wav_header_checked=True)["status"],
                             "technical_pass_pending_visual_review")
            for word in local["words"]:
                self.assertGreaterEqual(word["start"], 0)
                self.assertLessEqual(word["end"], row["sampleCount"] / 16000 + .000001)
                seen.append(word["word"])
        self.assertEqual(seen, speech_fixture(len(self.pcm(self.wav)) / 32000)["script"].split())

    def test_eight_and_half_minute_payloads_have_exact_boundaries(self):
        planned = self.make(510.013)
        report = p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertGreater(report["chapterCount"], 9)
        self.assertEqual(report["audioSampleCount"], planned["sourceSamples"])
        self.assertEqual(report["originalPcmSha256"], report["reassembledChapterPcmSha256"])
        self.assertTrue(all(row["frameCount"] <= 3600 for row in report["chapters"]))
        self.assertTrue(all(row["sampleCount"] > 0 for row in report["chapters"]))

    def test_first_and_last_acoustic_times_are_relative_to_chapter_audio(self):
        self.make()
        report = p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertGreater(report["chapterCount"], 1)
        for row in report["chapters"]:
            sub = json.loads((self.destination / row["directory"] / "acoustic-plan.json").read_text())
            self.assertEqual(sub["words"][0]["scriptIndex"], 0)
            self.assertEqual(sub["phonemes"][0]["scriptIndex"], 0)
            self.assertLess(sub["words"][-1]["end"], row["sampleCount"] / 16000 + 1e-6)

    def test_manifest_tamper_refused_without_output(self):
        self.make()
        data = json.loads(self.chapters.read_text())
        data["chapters"][0]["sampleCount"] -= 1
        self.chapters.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertFalse(self.destination.exists())

    def test_manifest_extra_untrusted_fields_refused(self):
        self.make()
        data = json.loads(self.chapters.read_text())
        data["fakeApproval"] = True
        self.chapters.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            p.package(self.wav, self.plan, self.chapters, self.destination)

    def test_original_wav_mutation_refused(self):
        self.make()
        raw = bytearray(self.wav.read_bytes())
        raw[50] = (raw[50] + 1) % 256
        self.wav.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "manifest differs"):
            p.package(self.wav, self.plan, self.chapters, self.destination)

    def test_original_speech_plan_mutation_refused(self):
        self.make()
        data = json.loads(self.plan.read_text())
        data["script"] = "different " + data["script"]
        self.plan.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "not reviewed|manifest differs"):
            p.package(self.wav, self.plan, self.chapters, self.destination)

    def test_no_output_overwrite_after_success(self):
        self.make()
        p.package(self.wav, self.plan, self.chapters, self.destination)
        original = (self.destination / "bundle.json").read_bytes()
        with self.assertRaises(FileExistsError):
            p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertEqual((self.destination / "bundle.json").read_bytes(), original)

    def test_existing_unrelated_directory_never_deleted(self):
        self.make()
        self.destination.mkdir()
        token = self.destination / "do-not-touch"
        token.write_text("owner data")
        with self.assertRaises(FileExistsError):
            p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertEqual(token.read_text(), "owner data")

    def test_injected_write_failure_cleans_only_new_package(self):
        self.make()
        with patch.object(p, "write_new", side_effect=OSError("synthetic disk failure")):
            with self.assertRaisesRegex(OSError, "synthetic disk"):
                p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertTrue(self.wav.exists())
        self.assertTrue(self.plan.exists())

    def test_no_package_when_no_safe_speech_gap(self):
        self.make(85)
        data = json.loads(self.plan.read_text())
        for i, word in enumerate(data["words"]):
            word["end"] = min(85., word["start"] + .62)
            data["phonemes"][i]["end"] = word["end"]
        self.plan.write_text(json.dumps(data))
        with self.assertRaises(ValueError):
            p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertFalse(self.destination.exists())

    def test_invalid_wav_format_refused(self):
        self.make()
        with wave.open(str(self.wav), "wb") as out:
            out.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            out.writeframes(b"\x00\x00" * 1000)
        with self.assertRaises(ValueError):
            p.package(self.wav, self.plan, self.chapters, self.destination)

    def test_cli_writes_privately_and_does_not_claim_animation(self):
        self.make(55)
        code = p.main(["--wav", str(self.wav), "--plan", str(self.plan),
                       "--chapters", str(self.chapters), "--out", str(self.destination)])
        self.assertEqual(code, 0)
        report = json.loads((self.destination / "bundle.json").read_text())
        self.assertFalse(report["audioMuxed"])
        self.assertFalse(report["artisticApproval"])
        self.assertEqual(report["chapterCount"], 1)
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_manifest_duplicate_json_field_rejected(self):
        self.make()
        self.chapters.write_text('{"schemaVersion":1,"schemaVersion":2}')
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            p.package(self.wav, self.plan, self.chapters, self.destination)
        self.assertFalse(self.destination.exists())

    def test_duplicate_output_paths_never_user_controlled(self):
        self.make()
        report = p.package(self.wav, self.plan, self.chapters, self.destination)
        paths = [x["directory"] for x in report["chapters"]]
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(all(s.startswith("chapter-") and "/" not in s and
                            "\\" not in s for s in paths))


if __name__ == "__main__":
    unittest.main()
