"""Offline compatibility checks for 14 existing-runner-shaped Walter workpacks."""
import copy
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import walter_workpack_compile as compiler
import walter_research_backlog as backlog


class WalterWorkpackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packets = compiler.compile_packets(ROOT)

    def test_all_14_checked_in_packets_identical_to_generator(self):
        result = compiler.verify_checked_in(ROOT)
        self.assertEqual(result["packets"], 14)
        self.assertEqual(result["model_calls"], 0)
        self.assertTrue(result["pending_runner_allowlist"])

    def test_all_seven_breaking_bad_specialists_have_two(self):
        release = backlog.validated(ROOT)
        for role in backlog.ROLES:
            ids = [packet["id"] for packet in self.packets.values()
                   if packet["id"] in [j["id"] for j in release["jobs"]
                                      if j["role"] == role]]
            self.assertEqual(len(ids), 2, role)

    def test_slug_names_under_original_runner_limit(self):
        for slug in self.packets:
            self.assertLessEqual(len(slug), 56)
            self.assertRegex(slug, r"^walter-v1-[a-z0-9-]+$")

    def test_generated_packets_no_side_effects(self):
        for packet in self.packets.values():
            self.assertIs(packet["external_effects_allowed"], False)
            self.assertIs(packet["mac_gui_required"], False)
            self.assertEqual(packet["output_mode"], "draft_review_only")

    def test_workpack_contains_role_and_provenance_reminder(self):
        for packet in self.packets.values():
            self.assertIn("ROVOR ghost specialist:", packet["task"])
            self.assertIn("cite exact supplied files", packet["task"])
            self.assertIn("No model-generated follow-up", packet["task"])

    def test_packet_ids_match_backlog_and_no_legacy_collision(self):
        ids = {j["id"] for j in backlog.validated(ROOT)["jobs"]}
        self.assertEqual(ids, {p["id"] for p in self.packets.values()})
        legacy = {"runner-blocker", "supervisor-resilience", "provider-efficiency",
                  "overnight-acceptance", "unattended-readiness"}
        self.assertFalse(legacy.intersection(self.packets))

    def test_packet_max_input_bytes_and_legacy_limits(self):
        for packet in self.packets.values():
            self.assertLessEqual(len(compiler.validate_legacy_packet(ROOT, packet)
                                     .encode("utf-8")), 10000)
            self.assertEqual(packet["max_input_chars"], 28000)
            self.assertEqual(packet["max_output_chars"], 22000)

    def test_wrong_role_is_not_implicitly_enabled(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["role"] = "walt"
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_unsafe_external_effect_is_refused(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["external_effects_allowed"] = True
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_unsafe_input_traversal_is_refused(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["inputs"] = ["../../private"]
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_unsafe_source_env_is_refused(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["inputs"] = [".env"]
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_slug_length_violation_rejected(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["slug"] = "walter-v1-" + ("a" * 90)
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_extra_schema_key_rejected(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["model_use_authorized"] = True
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_changed_limit_not_accepted(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["max_input_chars"] = 999999
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def test_boolean_cannot_impersonate_integer_limits(self):
        packet = copy.deepcopy(next(iter(self.packets.values())))
        packet["max_input_chars"] = True
        with self.assertRaises(ValueError):
            compiler.validate_legacy_packet(ROOT, packet)

    def sandbox(self):
        temp = tempfile.TemporaryDirectory(prefix="walter-packet-check-")
        dest = Path(temp.name)
        for source in backlog.PUBLIC_SOURCES:
            out = dest / source
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / source, out)
        manifest = dest / backlog.MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / backlog.MANIFEST, manifest)
        for slug in self.packets:
            relative = compiler.OUT / (slug + ".json")
            out = dest / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, out)
        return temp, dest

    def test_changed_checked_in_packet_detected(self):
        temp, folder = self.sandbox()
        try:
            slug = next(iter(self.packets))
            target = folder / compiler.OUT / (slug + ".json")
            target.write_text(target.read_text() + " ", encoding="utf-8")
            with self.assertRaises(ValueError):
                compiler.verify_checked_in(folder)
        finally:
            temp.cleanup()

    def test_missing_checked_in_packet_detected(self):
        temp, folder = self.sandbox()
        try:
            slug = next(iter(self.packets))
            (folder / compiler.OUT / (slug + ".json")).unlink()
            with self.assertRaises(ValueError):
                compiler.verify_checked_in(folder)
        finally:
            temp.cleanup()

    def test_extra_unreviewed_packet_detected(self):
        temp, folder = self.sandbox()
        try:
            (folder / compiler.OUT / "walter-v1-unknown.json").write_text("{}")
            with self.assertRaises(ValueError):
                compiler.verify_checked_in(folder)
        finally:
            temp.cleanup()

    def test_symlinked_workpack_refused(self):
        temp, folder = self.sandbox()
        try:
            slug = next(iter(self.packets))
            target = folder / compiler.OUT / (slug + ".json")
            source = folder / compiler.OUT / "shared"
            target.rename(source)
            target.symlink_to(source)
            with self.assertRaises(ValueError):
                compiler.verify_checked_in(folder)
        finally:
            temp.cleanup()

    def test_public_input_symlink_parent_refused(self):
        temp, folder = self.sandbox()
        try:
            src = folder / "architecture"
            orig = folder / "architecture-original"
            src.rename(orig)
            src.symlink_to(orig, target_is_directory=True)
            packet = next(p for p in self.packets.values()
                          if any(s.startswith("architecture/") for s in p["inputs"]))
            with self.assertRaises(ValueError):
                compiler.validate_legacy_packet(folder, packet)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
