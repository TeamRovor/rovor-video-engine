"""Verified private chapter -> actual native Moho switch archive, source-free tests."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import chapter_package
import longform_chapters
import moho_compile as moho
import native_chapter_switch as subject
from tests.test_longform_chapters import speech_fixture
from tests.test_moho_compile import fixture as moho_fixture


class NativeChapterSwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wav = self.root / "source.wav"
        self.speech = self.root / "speech.json"
        self.manifest = self.root / "chapters.json"
        self.package = self.root / "private-chapters"
        self.original = self.root / "existing-master.moho"
        self.calibration = self.root / "approved-mapping.json"
        self.result = self.root / "new-chapter.moho"
        self.make()

    def make(self, seconds=88.07):
        samples = round(seconds * 16000)
        with wave.open(str(self.wav), "wb") as out:
            out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            piece = b"\x16\x00" * 16000
            for _ in range(samples // 16000):
                out.writeframesraw(piece)
            out.writeframesraw(piece[:2 * (samples % 16000)])
            out.writeframes(b"")
        self.speech.write_text(json.dumps(speech_fixture(samples / 16000)))
        self.manifest.write_text(json.dumps(
            longform_chapters.plan_chapters(self.wav, self.speech)))
        chapter_package.package(self.wav, self.speech, self.manifest, self.package)
        self.choose(0)

    def choose(self, index, *, fps=60, frame_override=None, switch_name="mouth",
               setup_rest="Rest", available_child="AI"):
        evidence = chapter_package.load_json(
            self.package / ("chapter-%03d" % index) / "chapter.json")
        frames = evidence["chapterPlan"]["frameCount"]
        doc = moho_fixture()
        doc["project_data"]["fps"] = fps
        doc["project_data"]["end_frame"] = (frame_override if frame_override is not None
                                            else frames)
        mouth = doc["layers"][0]["layers"][0]
        mouth["uuid"] = switch_name
        mouth["layers"][1]["name"] = available_child
        mouth["switch_keys"]["val"][0] = setup_rest
        with zipfile.ZipFile(self.original, "w") as archive:
            archive.writestr(moho.PAYLOAD, json.dumps(doc))
            archive.writestr("artwork.bin", b"original-art-must-be-preserved")
            archive.comment = b"source-rig-identity"
        self.calibration.write_text(json.dumps({
            "schemaVersion": 1, "chapterIndex": index,
            "templateSha256": hashlib.sha256(self.original.read_bytes()).hexdigest(),
            "sourceWavSha256": json.loads((self.package / "bundle.json").read_text())["sourceWavSha256"],
            "mouthLayerUuid": switch_name,
            "restChild": "Rest",
            "phoneToChild": {"W": available_child},
        }))
        return frames

    def compile(self, chapter=0):
        return subject.compile_chapter(self.package, chapter, self.original,
                                       self.calibration, self.result)

    def test_original_art_and_setup_preserved_real_native_zip_compiled(self):
        original_bytes = self.original.read_bytes()
        report = self.compile()
        self.assertTrue(self.result.exists())
        self.assertEqual(self.original.read_bytes(), original_bytes)
        self.assertTrue(report["frameZeroPreserved"])
        self.assertFalse(report["nativeMohoCliRenderPerformed"])
        self.assertFalse(report["studioApproval"])
        self.assertEqual(report["originalNativeTemplateSha256"],
                         hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual(report["compiledArchiveSha256"],
                         hashlib.sha256(self.result.read_bytes()).hexdigest())
        doc, _, comment = moho.load_archive(self.result)
        self.assertEqual(comment, b"source-rig-identity")
        mouth = doc["layers"][0]["layers"][0]
        self.assertEqual(mouth["switch_keys"]["when"][0], 0)
        self.assertEqual(mouth["switch_keys"]["val"][0], "Rest")
        self.assertIn("AI", mouth["switch_keys"]["val"])
        self.assertEqual(doc["project_data"]["end_frame"], report["chapterFrames"])
        with zipfile.ZipFile(self.result) as archive:
            self.assertEqual(archive.read("artwork.bin"),
                             b"original-art-must-be-preserved")
        self.assertEqual(report["targetNativeSwitchLayerUuid"], "mouth")

    def test_second_chapter_has_own_pcm_clock_and_mouth_keys(self):
        frames = self.choose(1)
        result = self.compile(chapter=1)
        self.assertEqual(result["chapterIndex"], 1)
        self.assertEqual(result["chapterFrames"], frames)
        doc, _, _ = moho.load_archive(self.result)
        keys = doc["layers"][0]["layers"][0]["switch_keys"]["when"]
        self.assertEqual(keys[0], 0)
        self.assertLessEqual(max(keys), frames)

    def test_source_zip_is_not_retimed_24fps_to_60(self):
        self.choose(0, fps=24)
        with self.assertRaisesRegex(ValueError, "exact chapter frame count at native 60fps"):
            self.compile()
        self.assertFalse(self.result.exists())

    def test_native_template_must_already_match_this_chapter(self):
        self.choose(0, frame_override=60)
        with self.assertRaisesRegex(ValueError, "exact chapter frame count"):
            self.compile()

    def test_unknown_rig_switch_uuid_rejected(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["mouthLayerUuid"] = "guess-mouth-not-real"
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "mouth layer UUID"):
            self.compile()

    def test_unmapped_english_phone_rejected(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["phoneToChild"] = {"M": "AI"}
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "No calibrated switch mapping for phoneme W"):
            self.compile()

    def test_missing_calibrated_child_rejected(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["phoneToChild"]["W"] = "InventedLipShape"
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "absent switch child"):
            self.compile()

    def test_wrong_template_hash_rejected(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["templateSha256"] = "0" * 64
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "template.*binding changed"):
            self.compile()

    def test_wrong_original_audio_binding_rejected(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["sourceWavSha256"] = "0" * 64
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "audio binding changed"):
            self.compile()

    def test_template_mouth_setup_frame_zero_is_never_silently_replaced(self):
        self.choose(0, setup_rest="Other")
        with self.assertRaisesRegex(ValueError, "mouth-rest frame zero"):
            self.compile()

    def test_duplicate_viseme_child_names_are_unsafe(self):
        self.choose(0, available_child="Rest")
        with self.assertRaisesRegex(ValueError, "ambiguous child names"):
            self.compile()

    def test_existing_destination_is_never_overwritten(self):
        self.choose(0)
        self.result.write_bytes(b"someone else's project")
        with self.assertRaises(FileExistsError):
            self.compile()
        self.assertEqual(self.result.read_bytes(), b"someone else's project")

    def test_interrupted_archive_copy_removes_only_partial_new_output(self):
        self.choose(0)
        preserved = self.original.read_bytes()
        def partial_copy(src, dst, *args, **kwargs):
            dst.write(b"partial-archive")
            raise OSError("synthetic interrupted copy")
        with patch.object(subject.shutil, "copyfileobj", side_effect=partial_copy):
            with self.assertRaisesRegex(OSError, "synthetic interrupted copy"):
                self.compile()
        self.assertFalse(self.result.exists())
        self.assertEqual(self.original.read_bytes(), preserved)

    def test_reject_private_package_mutation(self):
        self.choose(0)
        audio = self.package / "chapter-000" / "narration.wav"
        b = bytearray(audio.read_bytes())
        b[-3] ^= 1
        audio.write_bytes(b)
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            self.compile()
        self.assertFalse(self.result.exists())

    def test_reject_tampered_or_forged_calibration_fields(self):
        self.choose(0)
        mapping = json.loads(self.calibration.read_text())
        mapping["artisticApproval"] = True
        self.calibration.write_text(json.dumps(mapping))
        with self.assertRaisesRegex(ValueError, "Unexpected rig calibration schema"):
            self.compile()

    def test_native_compilation_schema_1045(self):
        frames = self.choose(0)
        with zipfile.ZipFile(self.original) as source:
            doc = json.loads(source.read(moho.PAYLOAD))
        doc["version"] = 1045
        with zipfile.ZipFile(self.original, "w") as out:
            out.writestr(moho.PAYLOAD, json.dumps(doc))
            out.writestr("artwork.bin", b"original-art-must-be-preserved")
            out.comment = b"source-rig-identity"
        mapping = json.loads(self.calibration.read_text())
        mapping["templateSha256"] = hashlib.sha256(self.original.read_bytes()).hexdigest()
        self.calibration.write_text(json.dumps(mapping))
        result = self.compile()
        self.assertEqual(result["chapterFrames"], frames)
        compiled, _, _ = moho.load_archive(self.result)
        self.assertEqual(compiled["version"], 1045)

    def test_cli_source_free_compilation_with_verified_evidence(self):
        self.choose(0)
        code = subject.main(["--package", str(self.package), "--chapter", "0",
                             "--template", str(self.original),
                             "--calibration", str(self.calibration),
                             "--out", str(self.result)])
        self.assertEqual(code, 0)
        self.assertTrue(self.result.exists())

    def test_no_native_render_approval_claim_in_report(self):
        self.choose(0)
        report = self.compile()
        self.assertFalse(report["nativeMohoCliRenderPerformed"])
        self.assertFalse(report["animatedCharacterArtValidated"])
        self.assertFalse(report["phonemeLipSyncVisuallyApproved"])
        self.assertFalse(report["studioApproval"])


if __name__ == "__main__":
    unittest.main()
