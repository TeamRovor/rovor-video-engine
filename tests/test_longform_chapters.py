"""Longform source-WAV chapter planning: independent continuity and refusal tests."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import longform_chapters as c


def speech_fixture(seconds, *, word_step=.62, spoken=.55):
    n = int((seconds - .5) // word_step) + 1
    words = []
    phones = []
    for i in range(n):
        a = round(.02 + i * word_step, 7)
        b = round(min(a + spoken, seconds - .02), 7)
        if a >= b:
            break
        word = {"word": "we", "scriptIndex": i, "start": a,
                "end": b, "reviewFlags": []}
        words.append(word)
        phones.append({"word": "we", "scriptIndex": i, "phone": "W",
                       "value": "F", "start": a, "end": b})
    return {
        "script": " ".join("we" for _ in words),
        "alignment": {"status": "acoustic", "wordCoverage": 1.0},
        "words": words, "phonemes": phones, "silences": [],
    }


class ChapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wav = self.root / "source.wav"
        self.plan = self.root / "speech.json"

    def make(self, seconds, *, word_step=.62, spoken=.55):
        samples = round(seconds * 16000)
        with wave.open(str(self.wav), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            block = b"\x18\x00" * 16000
            for _ in range(samples // 16000):
                output.writeframesraw(block)
            output.writeframesraw(block[:(samples % 16000) * 2])
            output.writeframes(b"")
        speech = speech_fixture(samples / 16000, word_step=word_step, spoken=spoken)
        self.plan.write_text(json.dumps(speech), encoding="utf-8")
        return speech, samples

    def test_4m23_complete_narration_without_lost_pcm_or_video_frames(self):
        speech, samples = self.make(262.687313)
        original_wav = self.wav.read_bytes()
        before_hash = hashlib.sha256(original_wav).hexdigest()
        report = c.plan_chapters(self.wav, self.plan)
        self.assertGreaterEqual(report["chapterCount"], 5)
        self.assertLessEqual(report["chapterCount"], 7)
        self.assertEqual(report["sourceSamples"], samples)
        self.assertEqual(report["sourceWavSha256"], before_hash)
        self.assertEqual(report["totalFrames"], c.frames_for_samples(samples))
        self.assertEqual(sum(x["sampleCount"] for x in report["chapters"]), samples)
        self.assertEqual(sum(x["frameCount"] for x in report["chapters"]),
                         report["totalFrames"])
        self.assertEqual(self.wav.read_bytes(), original_wav)
        self.assertFalse(report["nativeMohoRendered"])
        self.assertFalse(report["publicationApproved"])
        self.assertTrue(report["completeSourceSampleCoverage"])
        self.assertTrue(all(900 <= x["frameCount"] <= 3600
                            for x in report["chapters"]))
        self.assertTrue(all(x["startSample"] == p["endSampleExclusive"]
                            for p, x in zip(report["chapters"], report["chapters"][1:])))
        for chapter in report["chapters"][1:]:
            cut = chapter["startFrame"] / 60.
            self.assertFalse(any(w["start"] <= cut <= w["end"] for w in speech["words"]))
            self.assertFalse(any(p["start"] <= cut <= p["end"] for p in speech["phonemes"]))
            self.assertEqual(chapter["cutBefore"]["cutFrame"], chapter["startFrame"])

    def test_eight_and_a_half_minute_recording(self):
        _, samples = self.make(510.013)
        result = c.plan_chapters(self.wav, self.plan)
        self.assertGreater(result["chapterCount"], 9)
        self.assertLess(result["chapterCount"], 15)
        self.assertEqual(result["chapters"][-1]["endSampleExclusive"], samples)
        self.assertEqual(result["chapters"][-1]["endFrameExclusive"],
                         c.frames_for_samples(samples))
        self.assertTrue(all(row["frameCount"] <= 3600
                            for row in result["chapters"]))

    def test_single_55_second_chapter_is_not_called_a_native_render(self):
        self.make(55)
        result = c.plan_chapters(self.wav, self.plan)
        self.assertEqual(result["chapterCount"], 1)
        self.assertEqual(result["chapters"][0]["startFrame"], 0)
        self.assertFalse(result["audioChunksWritten"])

    def test_exact_frame_sample_boundaries_do_not_drift(self):
        samples = round(539.17313 * 16000)
        total = c.frames_for_samples(samples)
        boundaries = list(range(0, total, 237)) + [total]
        ranges = [(c.samples_at_frame(a, samples),
                   c.samples_at_frame(b, samples))
                  for a, b in zip(boundaries, boundaries[1:])]
        self.assertEqual(ranges[0][0], 0)
        self.assertEqual(ranges[-1][1], samples)
        self.assertTrue(all(x[1] == y[0] for x, y in zip(ranges, ranges[1:])))
        self.assertEqual(sum(b - a for a, b in ranges), samples)
        self.assertEqual(sum(b - a for a, b in zip(boundaries, boundaries[1:])), total)

    def test_refuses_80_seconds_when_no_word_gap_can_fit_a_cut(self):
        self.make(80, word_step=.5, spoken=.5)
        with self.assertRaisesRegex(ValueError, "No safe 60fps word-boundary"):
            c.plan_chapters(self.wav, self.plan)

    def test_refuses_fallback_instead_of_fabricating_english_phone_times(self):
        p, _ = self.make(80)
        p["alignment"]["status"] = "fallback"
        self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "Acoustic plan is not reviewed"):
            c.plan_chapters(self.wav, self.plan)

    def test_refuses_unreviewed_word_flags(self):
        p, _ = self.make(65)
        p["words"][0]["reviewFlags"] = ["ambiguous-start"]
        self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "Acoustic plan is not reviewed"):
            c.plan_chapters(self.wav, self.plan)

    def test_refuses_missing_word_and_phone_coverage(self):
        p, _ = self.make(68)
        p["script"] = "unrelated " + p["script"]
        self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "Acoustic plan is not reviewed"):
            c.plan_chapters(self.wav, self.plan)

    def test_reject_truncated_wav(self):
        self.make(65)
        data = self.wav.read_bytes()
        self.wav.write_bytes(data[:-900])
        with self.assertRaisesRegex((ValueError, wave.Error), "Truncated"):
            c.plan_chapters(self.wav, self.plan)

    def test_reject_over_15_minutes_before_processing(self):
        with wave.open(str(self.wav), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            one_second = b"\x00\x00" * 16000
            for _ in range(901):
                output.writeframesraw(one_second)
            output.writeframes(b"")
        with self.assertRaisesRegex(ValueError, "15 minutes"):
            c.pcm_samples(self.wav)

    def test_reject_wrong_source_format(self):
        with wave.open(str(self.wav), "wb") as w:
            w.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            w.writeframes(b"\x00\x00" * 8000)
        with self.assertRaisesRegex(ValueError, "16kHz"):
            c.pcm_samples(self.wav)

    def test_reject_duplicate_and_nan_plan_json(self):
        self.make(32)
        for payload in ('{"script":"hi","script":"bye"}', '{"duration":NaN}'):
            with self.subTest(payload=payload):
                self.plan.write_text(payload)
                with self.assertRaisesRegex(ValueError, "Duplicate|Nonfinite"):
                    c.plan_chapters(self.wav, self.plan)

    def test_cli_never_overwrites_existing_manifest(self):
        self.make(55)
        destination = self.root / "manifest.json"
        self.assertEqual(c.main(["--wav", str(self.wav), "--plan", str(self.plan),
                                 "--out", str(destination)]), 0)
        result = json.loads(destination.read_text())
        self.assertEqual(result["schemaVersion"], 1)
        self.assertIn("originalDurationSeconds", result)
        original = destination.read_bytes()
        self.assertEqual(c.main(["--wav", str(self.wav), "--plan", str(self.plan),
                                 "--out", str(destination)]), 1)
        self.assertEqual(destination.read_bytes(), original)

    def test_source_audit_cannot_be_skipped_by_synthetic_silence_rows(self):
        p, _ = self.make(75)
        p["alignment"]["wordCoverage"] = .99
        p["silences"] = [{"start": 0, "end": 60}]
        self.plan.write_text(json.dumps(p))
        with self.assertRaisesRegex(ValueError, "Acoustic plan is not reviewed"):
            c.plan_chapters(self.wav, self.plan)

    def test_no_private_media_or_model_writes_in_manifest(self):
        self.make(75)
        result = c.plan_chapters(self.wav, self.plan)
        serialized = json.dumps(result)
        self.assertNotIn(str(self.wav), serialized)
        self.assertNotIn(str(self.plan), serialized)
        self.assertNotIn("source.wav", serialized)
        self.assertTrue(all(x.get("cutBefore") is None or
                            "beforeWordIndex" in x["cutBefore"]
                            for x in result["chapters"]))


if __name__ == "__main__":
    unittest.main()
