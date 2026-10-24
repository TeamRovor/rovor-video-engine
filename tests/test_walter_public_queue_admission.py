"""Synthetic pre-enqueue regression tests: no Mac, SQLite, network or model."""
import copy
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_public_queue_admission import admit

COMMIT = "a" * 40


def task(task_id, path, *, priority=1):
    return {"id": task_id, "title": "Inspect and repair this pinned public source",
            "acceptance": "Identify one specific regression with a reproducible test.",
            "priority": priority, "status": "ready", "owner": None,
            "scopes": [path], "depends_on": []}


def fixture():
    mike = task("mike-source-fix-01", "tools/omniroute_example.py")
    gale = task("gale-source-fix-01", "tools/blender_example.py", priority=2)
    sources = {
        "tools/omniroute_example.py": b"def omniroute_check():\n    return True\n",
        "tools/blender_example.py": b"def blender_check():\n    return True\n",
    }
    return {
        "payload": {"public_task": {
            "id": gale["id"], "title": gale["title"],
            "acceptance": gale["acceptance"], "commit": COMMIT,
            "form": "tests"}},
        "queue": {"version": 1, "tasks": [mike, gale]},
        "routing": {"version": 1, "tasks": {
            t["id"]: {"lane": "operations", "requires": ["hosted-ci"]}
            for t in (mike, gale)}},
        "commit": COMMIT, "source_bytes": sources,
        "source_digests": {p: hashlib.sha256(data).hexdigest()
                           for p, data in sources.items()},
        "seen_dedupe": set(), "attempted_task_ids": set(),
        "claimed_role": "gale",
        "trusted_pinned_snapshot": True, "trusted_seen_ledger": True,
        "trusted_task_ledger": True, "complete_ledger": True,
        "owner_opt_in": True, "stop_present": False,
        "other_job_running": False,
    }


class PublicQueueAdmissionTests(unittest.TestCase):
    def status(self, expected, change):
        args = fixture()
        change(args)
        self.assertEqual(admit(**args)["status"], expected)

    def test_exact_public_task_accepted_only_as_inert_seed(self):
        result = admit(**fixture())
        self.assertEqual(result["status"], "grounded_public_seed_review_only")
        self.assertEqual(result["candidate"]["task_id"], "gale-source-fix-01")
        self.assertEqual(result["candidate"]["role"], "gale")
        self.assertEqual(result["candidate"]["pinned_commit"], COMMIT)
        self.assertEqual(result["candidate"]["payload"], fixture()["payload"])
        self.assertFalse(result["candidate"]["model_use_authorized"])
        self.assertFalse(result["candidate"]["external_effects_allowed"])
        self.assertTrue(result["requires_fresh_atomic_sqlite_claim"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)
        self.assertFalse(result["mac_execution"])

    def test_second_priority_candidate_enumerated(self):
        args = fixture()
        self.assertEqual(args["queue"]["tasks"][0]["priority"], 1)
        self.assertEqual(admit(**args)["candidate"]["role"], "gale")

    def test_all_four_review_forms_are_bounded(self):
        for form in ("plan", "checklist", "handoff", "tests"):
            with self.subTest(form=form):
                args = fixture()
                args["payload"]["public_task"]["form"] = form
                self.assertEqual(admit(**args)["status"],
                                 "grounded_public_seed_review_only")

    def test_existing_task_attempt_never_replayed_across_forms(self):
        self.status("task_already_attempted_no_replay",
                    lambda p: p["attempted_task_ids"].add("gale-source-fix-01"))

    def test_fallback_and_legacy_packets_not_auto_queued(self):
        for payload in ({"assignment": "continuous-v1-gale-0-tests"},
                        {"packet": "walter-v2-gale-render-qa"},
                        {}, {"public_task": {}, "assignment": "extra"}):
            with self.subTest(payload=payload):
                self.status("legacy_or_generic_packet_requires_review",
                            lambda p, payload=payload: p.update(payload=payload))

    def test_stale_or_forged_public_fields_rejected(self):
        for field, value in (("commit", "b" * 40),
                             ("title", "Generic text instead of pinned title"),
                             ("acceptance", "Make things better"),
                             ("form", "arbitrary")):
            with self.subTest(field=field):
                self.status("invalid_or_stale_public_payload",
                            lambda p, field=field, value=value:
                            p["payload"]["public_task"].update({field: value}))

    def test_unknown_payload_field_rejected(self):
        self.status("invalid_or_stale_public_payload",
                    lambda p: p["payload"]["public_task"].update(
                        {"model": "paid-model"}))

    def test_blocked_or_done_tasks_not_reseeded(self):
        for status in ("blocked", "done"):
            with self.subTest(status=status):
                self.status("public_task_not_eligible",
                            lambda p, status=status:
                            p["queue"]["tasks"][1].update(status=status))

    def test_ready_task_with_an_owner_is_not_eligible(self):
        self.status("public_task_not_eligible",
                    lambda p: p["queue"]["tasks"][1].update(
                        owner="Another participant"))

    def test_active_requires_independent_owner_approval(self):
        args = fixture()
        args["queue"]["tasks"][1].update(status="active", owner="Other owner")
        self.assertEqual(admit(**args)["status"], "public_task_not_eligible")
        args["approved_active_ids"] = ("gale-source-fix-01",)
        self.assertEqual(admit(**args)["status"], "source_grounding_refused")
        args["trusted_owner_approval"] = True
        self.assertEqual(admit(**args)["status"],
                         "grounded_public_seed_review_only")

    def test_unmet_dependency_rejected_even_when_ready(self):
        args = fixture()
        dep = task("source-dependency-01", "tools/other_example.py")
        dep["status"] = "blocked"
        args["queue"]["tasks"].append(dep)
        args["routing"]["tasks"][dep["id"]] = {
            "lane": "operations", "requires": ["hosted-ci"]}
        args["queue"]["tasks"][1]["depends_on"] = [dep["id"]]
        self.assertEqual(admit(**args)["status"], "public_task_not_eligible")
        dep["status"] = "done"
        self.assertEqual(admit(**args)["status"],
                         "grounded_public_seed_review_only")

    def test_host_only_route_not_admitted(self):
        self.status("public_task_not_eligible",
                    lambda p: p["routing"]["tasks"]["gale-source-fix-01"].update(
                        requires=["blender-runtime"]))

    def test_wrong_specialist_from_title_heuristic_refused(self):
        args = fixture()
        args["queue"]["tasks"][1]["title"] = "OmniRoute source audit for Blender"
        args["payload"]["public_task"]["title"] = args["queue"]["tasks"][1]["title"]
        args["claimed_role"] = "mike"
        self.assertEqual(admit(**args)["status"], "unverified_specialist_role")

    def test_other_active_scope_overlap_refused(self):
        args = fixture()
        other = task("other-owned-gale-task", "tools/blender_example.py")
        other.update(status="active", owner="Another worker")
        args["queue"]["tasks"].append(other)
        args["routing"]["tasks"][other["id"]] = {
            "lane": "operations", "requires": ["hosted-ci"]}
        self.assertEqual(admit(**args)["status"], "unfinished_scope_conflict")

    def test_other_done_scope_does_not_block(self):
        args = fixture()
        other = task("older-done-gale-task", "tools/blender_example.py")
        other["status"] = "done"
        args["queue"]["tasks"].append(other)
        args["routing"]["tasks"][other["id"]] = {
            "lane": "operations", "requires": ["hosted-ci"]}
        self.assertEqual(admit(**args)["status"],
                         "grounded_public_seed_review_only")

    def test_missing_pinned_source_not_admitted(self):
        args = fixture()
        args["source_bytes"].pop("tools/blender_example.py")
        args["source_digests"].pop("tools/blender_example.py")
        self.assertEqual(admit(**args)["status"], "public_task_not_eligible")

    def test_changed_source_bytes_rejected_globally(self):
        self.status("pinned_snapshot_unverified",
                    lambda p: p["source_bytes"].update(
                        {"tools/omniroute_example.py": b"altered"}))

    def test_bad_digest_or_unsafe_source_path_rejected(self):
        self.status("pinned_snapshot_unverified",
                    lambda p: p["source_digests"].update(
                        {"tools/blender_example.py": "f" * 64}))
        args = fixture()
        args["source_bytes"]["../secret.py"] = b"private"
        args["source_digests"]["../secret.py"] = hashlib.sha256(b"private").hexdigest()
        self.assertEqual(admit(**args)["status"], "pinned_snapshot_unverified")

    def test_unpaired_routing_rejected(self):
        self.status("invalid_or_incomplete_evidence",
                    lambda p: p["routing"]["tasks"].pop("mike-source-fix-01"))

    def test_duplicate_queue_identity_rejected(self):
        self.status("invalid_or_incomplete_evidence",
                    lambda p: p["queue"]["tasks"].append(
                        copy.deepcopy(p["queue"]["tasks"][1])))

    def test_stop_running_and_owner_opt_in_required(self):
        for field, value, expected in (
            ("stop_present", True, "stopped"),
            ("other_job_running", True, "unverified_authority"),
            ("owner_opt_in", False, "unverified_authority")):
            with self.subTest(field=field):
                self.status(expected,
                            lambda p, field=field, value=value:
                            p.update({field: value}))

    def test_each_independent_trust_gate_required(self):
        for field in ("trusted_pinned_snapshot", "trusted_seen_ledger",
                      "trusted_task_ledger", "complete_ledger"):
            with self.subTest(field=field):
                self.status("unverified_authority",
                            lambda p, field=field: p.update({field: False}))

    def test_missing_or_malformed_task_history_refused(self):
        self.status("task_history_unverified",
                    lambda p: p.update(attempted_task_ids=None))
        self.status("task_history_unverified",
                    lambda p: p["attempted_task_ids"].add("bad/id"))

    def test_inputs_are_never_modified(self):
        args = fixture()
        before = copy.deepcopy(args)
        admit(**args)
        self.assertEqual(args, before)

    def test_refusals_do_not_leak_private_data(self):
        args = fixture()
        args["source_bytes"]["tools/blender_example.py"] += b"PRIVATE-SECRET"
        result = admit(**args)
        self.assertNotIn("PRIVATE-SECRET", repr(result))
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)


if __name__ == "__main__":
    unittest.main()
