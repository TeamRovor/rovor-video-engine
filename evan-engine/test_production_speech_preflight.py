"""Isolated tests: original audio and art must not be needed for metadata QA."""
import ast
import json
from pathlib import Path
import tempfile
import unittest
import wave

from production_speech_preflight import check_speech_plan

HERE = Path(__file__).resolve().parent


def phone_plan():
    return {
        "script": "phone",
        "alignment": {"status": "acoustic", "wordCoverage": 1.0},
        "words": [
            {"start": 0.1, "end": 0.7, "word": "phone", "scriptIndex": 0,
             "reviewFlags": []}
        ],
        "phonemes": [
            {"start": 0.1, "end": 0.2, "word": "phone", "scriptIndex": 0, "phone": "F", "value": "G"},
            {"start": 0.2, "end": 0.5, "word": "phone", "scriptIndex": 0, "phone": "OW1", "value": "E"},
            {"start": 0.5, "end": 0.7, "word": "phone", "scriptIndex": 0, "phone": "N", "value": "B"}
        ],
        "silences": []
    }


class SpeechPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wav = Path(self.tmp.name) / "narration.wav"
        with wave.open(str(self.wav), "wb") as source:
            source.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            source.writeframes(bytes(32000))

    def test_strict_good_metadata_is_not_approval(self):
        result = check_speech_plan(phone_plan(), self.wav)
        self.assertEqual(result["status"], "technical_pass_pending_visual_review")
        self.assertFalse(result["cartoonActingApproved"])
        self.assertFalse(result["acousticBoundariesPerceptuallyApproved"])
        self.assertTrue(result["readOnly"])
        self.assertFalse(result["audioContentCompared"])

    def test_rejected_unknown_spelling_phone_before_render(self):
        bad = phone_plan()
        bad["phonemes"][0]["phone"] = "PH"
        with self.assertRaisesRegex(ValueError, "rejected plan before render"):
            check_speech_plan(bad, self.wav)

    def test_rejected_unreviewed_acoustic_word(self):
        bad = phone_plan()
        bad["words"][0]["reviewFlags"] = ["word-anchor-disagreement"]
        with self.assertRaisesRegex(ValueError, "pending-review"):
            check_speech_plan(bad, self.wav)

    def test_rejected_fallback_with_no_acoustic_alignment(self):
        bad = phone_plan()
        bad["alignment"] = {"status": "fallback", "wordCoverage": 1.0}
        with self.assertRaisesRegex(ValueError, "rejected plan"):
            check_speech_plan(bad, self.wav)

    def test_rejected_mismatched_written_script(self):
        bad = phone_plan()
        bad["script"] = "phony"
        with self.assertRaisesRegex(ValueError, "rejected plan"):
            check_speech_plan(bad, self.wav)

    def test_report_mode_does_not_block_diagnostic_review(self):
        bad = phone_plan()
        bad["alignment"] = {"status": "fallback"}
        report = check_speech_plan(bad, self.wav, mode="report")
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["requestedMode"], "report")
        self.assertFalse(report["cartoonActingApproved"])

    def test_invalid_wav_rejected(self):
        with wave.open(str(self.wav), "wb") as source:
            source.setparams((2, 2, 16000, 0, "NONE", "not compressed"))
            source.writeframes(bytes(64000))
        with self.assertRaisesRegex(ValueError, "16kHz mono"):
            check_speech_plan(phone_plan(), self.wav)

    def test_no_output_or_source_modifications(self):
        p = phone_plan()
        old_plan = json.dumps(p, sort_keys=True)
        old_wav = self.wav.read_bytes()
        report = check_speech_plan(p, self.wav)
        self.assertEqual(json.dumps(p, sort_keys=True), old_plan)
        self.assertEqual(self.wav.read_bytes(), old_wav)
        self.assertEqual(sorted(x.name for x in Path(self.tmp.name).iterdir()), ["narration.wav"])
        self.assertEqual(report["requestedMode"], "require")

    def test_reject_wrong_frame_rate(self):
        for bad in (24, 30, 48, 120, True):
            with self.assertRaisesRegex(ValueError, "60fps"):
                check_speech_plan(phone_plan(), self.wav, fps=bad)

    def test_static_renderer_entrypoint_before_expensive_render(self):
        # This checks integration placement only; it is NOT a runtime MP4 test.
        tree = ast.parse((HERE / "render_acting_video.py").read_text())
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [(n.lineno, n.func.id) for n in ast.walk(main)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        qa_lines = [line for line, name in calls if name == "check_speech_plan"]
        self.assertEqual(len(qa_lines), 1)
        cache_lines = [line for line, name in calls if name == "body_cache_key"]
        self.assertEqual(len(cache_lines), 1)
        self.assertLess(qa_lines[0], cache_lines[0])
        text = (HERE / "render_acting_video.py").read_text()
        self.assertIn("--speech-qa", text)


if __name__ == "__main__":
    unittest.main()
