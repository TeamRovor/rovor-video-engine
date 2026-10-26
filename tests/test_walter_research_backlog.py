"""Offline regression tests for Walter's public-source research release."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import walter_research_backlog as walter


class WalterResearchBacklogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = walter.validated(ROOT)

    def gates(self, **overrides):
        params = {
            "seen_dedupe": set(),
            "authoritative_ledger": True,
            "stop_present": False,
            "separate_model_approval": True,
            "verified_free_route": True,
            "remaining_claims": 1,
        }
        params.update(overrides)
        return walter.select_next(self.base, **params)

    def test_public_release_is_valid_and_balanced(self):
        self.assertEqual(len(self.base["jobs"]), 14)
        self.assertEqual(len({j["dedupe_key"] for j in self.base["jobs"]}), 14)
        self.assertEqual({j["role"] for j in self.base["jobs"]}, walter.ROLES)

    def test_explicit_host_gates_default_to_STOP(self):
        self.assertEqual(walter.select_next(self.base)["status"], "stopped")

    def test_requires_authoritative_sqlite_ledger(self):
        self.assertEqual(self.gates(authoritative_ledger=False)["status"], "ledger_unverified")
        self.assertEqual(self.gates(seen_dedupe=None)["status"], "ledger_unverified")

    def test_requires_separate_live_model_approval(self):
        self.assertEqual(self.gates(separate_model_approval=False)["status"], "model_use_not_authorized")

    def test_requires_live_verified_free_route(self):
        self.assertEqual(self.gates(verified_free_route=False)["status"], "free_route_unverified")

    def test_still_obeys_STOP_marker(self):
        self.assertEqual(self.gates(stop_present=True)["status"], "stopped")

    def test_no_claims_remaining_cannot_submit(self):
        self.assertEqual(self.gates(remaining_claims=0)["status"], "quota_unavailable")
        self.assertEqual(self.gates(remaining_claims=6)["status"], "quota_unavailable")
        self.assertEqual(self.gates(remaining_claims=True)["status"], "quota_unavailable")

    def test_candidate_is_not_a_queued_or_executed_job(self):
        chosen = self.gates()
        self.assertEqual(chosen["status"], "candidate_only_not_enqueued")
        self.assertEqual(chosen["candidate"]["role"], "mike")
        self.assertEqual(set(chosen["candidate"]), {"id", "role", "stage", "dedupe_key"})

    def test_seven_roles_then_second_research_wave(self):
        seen = set()
        roles = []
        for _ in range(14):
            selected = self.gates(seen_dedupe=seen)
            self.assertEqual(selected["status"], "candidate_only_not_enqueued")
            item = selected["candidate"]
            roles.append(item["role"])
            self.assertNotIn(item["dedupe_key"], seen)
            seen.add(item["dedupe_key"])
        self.assertEqual(set(roles[:7]), walter.ROLES)
        self.assertEqual(set(roles[7:]), walter.ROLES)
        self.assertEqual(self.gates(seen_dedupe=seen)["status"], "exhausted_review_required")

    def test_all_prior_attempts_in_ledger_never_replayed(self):
        # A failed/needs_review item is still seen; no status-based replay.
        first = self.base["jobs"][0]["dedupe_key"]
        selected = self.gates(seen_dedupe={first})
        self.assertEqual(selected["candidate"]["role"], "jane")
        self.assertNotEqual(selected["candidate"]["dedupe_key"], first)

    def test_selector_does_not_mutate_release_or_seen_set(self):
        orig = copy.deepcopy(self.base)
        seen = {"some-past-id"}
        before = set(seen)
        self.gates(seen_dedupe=seen)
        self.assertEqual(orig, self.base)
        self.assertEqual(seen, before)

    def staged(self):
        temp = tempfile.TemporaryDirectory(prefix="walter-backlog-test-")
        base = Path(temp.name)
        doc = copy.deepcopy(self.base)
        for filename in walter.PUBLIC_SOURCES:
            dest = base / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / filename, dest)
        manifest = base / walter.MANIFEST
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(doc), encoding="utf-8")
        return temp, base, doc, manifest

    def test_duplicate_ids_rejected(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["jobs"][1]["id"] = doc["jobs"][0]["id"]
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_path_escape_rejected(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["jobs"][0]["sources"] = ["../../etc/passwd"]
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_unapproved_external_effects_rejected(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["jobs"][0]["external_effects_allowed"] = True
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_auto_generated_followups_rejected(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["policy"]["auto_generate_followups"] = True
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_integer_quota_policy_cannot_be_boolean(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["policy"]["max_jobs_per_tick"] = True
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_symlinked_public_source_parent_rejected(self):
        temp, base, doc, manifest = self.staged()
        try:
            source = base / "architecture"
            moved = base / "architecture-original"
            source.rename(moved)
            source.symlink_to(moved, target_is_directory=True)
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_private_source_not_allowed(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["jobs"][0]["sources"] = [".env"]
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()

    def test_no_code_or_model_use_approval_via_manifest(self):
        temp, base, doc, manifest = self.staged()
        try:
            doc["jobs"][0]["model_inference_authorized_by_manifest"] = True
            manifest.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaises(ValueError):
                walter.validated(base)
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
