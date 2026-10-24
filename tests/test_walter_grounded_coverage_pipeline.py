"""Offline, synthetic integration: never uses real Mac receipts or providers."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_grounded_coverage_pipeline import propose

NOW = 1800000000
JOB = "123e4567-e89b-12d3-a456-426614174000"


def task(task_id, path, priority=1, status="ready", owner=None):
    return {"id": task_id, "title": "Inspect and repair public source safely",
            "acceptance": "Identify one concrete regression and a tested fix.",
            "priority": priority, "status": status, "owner": owner,
            "scopes": [path], "depends_on": []}


def fixture():
    mike = "tools/omniroute_example.py"
    gale = "tools/blender_example.py"
    sources = {mike: b"def check_omniroute():\n    return True\n",
               gale: b"def check_blender():\n    return True\n"}
    tasks = [task("mike-safe-source-01", mike), task("gale-safe-source-01", gale)]
    return {
        "queue": {"version": 1, "tasks": tasks},
        "routing": {"version": 1, "tasks": {
            t["id"]: {"lane": "operations", "requires": ["hosted-ci"]}
            for t in tasks}},
        "commit": "a" * 40,
        "source_bytes": sources,
        "source_digests": {p: hashlib.sha256(b).hexdigest()
                           for p, b in sources.items()},
        "jobs": [], "claims": [], "job_roles": {}, "job_tasks": {},
        "human_reviews": [], "now": NOW, "stop_present": False,
        "other_job_running": False, "owner_opt_in": True,
        "trusted_pinned_snapshot": True, "trusted_sqlite_copy": True,
        "trusted_role_mapping": True, "trusted_human_reviews": True,
        "complete_ledger": True, "trusted_task_mapping": True,
    }


def add_job(params, *, role="gale", task_id="gale-older-task-01",
            status="needs_review", result=None, index=0):
    jid = JOB if index == 0 else f"{index:08x}-e89b-12d3-a456-426614174000"
    if result is None:
        result = {"draft_status": "draft_completed_needs_review",
                  "review_status": "draft_ready_for_human_review",
                  "private": "/Users/SECRET/private-draft"}
    params["jobs"].append({
        "id": jid, "kind": "research.omniroute",
        "dedupe_key": f"{index+1:064x}", "status": status,
        "result": json.dumps(result), "updated_at": NOW - 40})
    params["claims"].append({"job_id": jid, "event": "claimed",
                              "timestamp": NOW - 100})
    params["job_roles"][jid] = role
    params["job_tasks"][jid] = task_id
    return jid


class GroundedCoveragePipelineTests(unittest.TestCase):
    def test_proposes_one_grounded_unsubmitted_task(self):
        result = propose(**fixture())
        self.assertEqual(result["status"], "review_only_not_dispatched")
        self.assertEqual(result["candidate"]["role"], "gale")
        self.assertEqual(result["candidate"]["pinned_commit"], "a" * 40)
        self.assertFalse(result["candidate"]["model_use_authorized"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)
        self.assertFalse(result["mac_execution"])

    def test_deterministic_across_input_order(self):
        a = fixture()
        b = fixture()
        b["queue"]["tasks"].reverse()
        self.assertEqual(propose(**a), propose(**b))

    def test_existing_role_attempt_prioritizes_other_role(self):
        p = fixture()
        add_job(p, role="gale")
        result = propose(**p)
        self.assertEqual(result["candidate"]["role"], "mike")
        self.assertEqual(result["coverage"]["gale"]["awaiting_review"], 1)

    def test_same_task_blocked_across_changed_source(self):
        p = fixture()
        add_job(p, task_id="gale-safe-source-01")
        result = propose(**p)
        self.assertEqual(result["candidate"]["task_id"], "mike-safe-source-01")

    def test_all_tasks_previously_attempted_are_refused(self):
        p = fixture()
        add_job(p, task_id="gale-safe-source-01")
        add_job(p, role="mike", task_id="mike-safe-source-01", index=1)
        self.assertEqual(propose(**p)["status"], "no_unattempted_grounded_task")

    def test_missing_task_identity_map_refuses_even_without_jobs(self):
        p = fixture()
        p["trusted_task_mapping"] = False
        self.assertEqual(propose(**p)["status"], "task_identity_ledger_unverified")
        p = fixture()
        p["job_tasks"] = None
        self.assertEqual(propose(**p)["status"], "task_identity_ledger_unverified")

    def test_incomplete_task_identity_map_refused(self):
        p = fixture()
        add_job(p)
        p["job_tasks"].clear()
        self.assertEqual(propose(**p)["status"], "invalid_or_incomplete_evidence")

    def test_stop_and_active_job_fail_closed(self):
        for field, value, expected in (
            ("stop_present", True, "stopped"),
            ("other_job_running", True, "unverified_authority"),
            ("owner_opt_in", False, "unverified_authority")):
            with self.subTest(field=field):
                p = fixture()
                p[field] = value
                self.assertEqual(propose(**p)["status"], expected)

    def test_each_untrusted_evidence_source_refused(self):
        for field in ("trusted_pinned_snapshot", "trusted_sqlite_copy",
                      "trusted_role_mapping", "trusted_human_reviews",
                      "complete_ledger"):
            with self.subTest(field=field):
                p = fixture()
                p[field] = False
                self.assertEqual(propose(**p)["status"], "unverified_authority")

    def test_source_tampering_fails_closed(self):
        p = fixture()
        p["source_bytes"]["tools/blender_example.py"] += b"secret"
        self.assertEqual(propose(**p)["status"], "invalid_pinned_public_snapshot")

    def test_unpaired_source_refused(self):
        p = fixture()
        p["source_digests"].pop("tools/blender_example.py")
        self.assertEqual(propose(**p)["status"], "invalid_pinned_public_snapshot")

    def test_no_groundable_source_refused(self):
        p = fixture()
        p["source_bytes"].clear()
        p["source_digests"].clear()
        self.assertEqual(propose(**p)["status"], "no_unattempted_grounded_task")

    def test_public_active_owner_not_automatically_claimed(self):
        p = fixture()
        p["queue"]["tasks"][1]["status"] = "active"
        p["queue"]["tasks"][1]["owner"] = "Different worker"
        self.assertEqual(propose(**p)["candidate"]["role"], "mike")
        p["approved_active_ids"] = ("gale-safe-source-01",)
        p["trusted_owner_approval"] = True
        self.assertEqual(propose(**p)["candidate"]["role"], "gale")

    def test_unverified_owner_approval_refused(self):
        p = fixture()
        p["approved_active_ids"] = ("gale-safe-source-01",)
        self.assertEqual(propose(**p)["status"], "public_grounding_refused")

    def test_duplicate_claims_do_not_leak_private_data(self):
        p = fixture()
        add_job(p)
        p["claims"].append(dict(p["claims"][0]))
        result = propose(**p)
        self.assertEqual(result["status"], "invalid_or_incomplete_evidence")
        self.assertNotIn("SECRET", repr(result))

    def test_private_model_text_never_returned(self):
        p = fixture()
        add_job(p)
        self.assertNotIn("/Users/SECRET", repr(propose(**p)))

    def test_global_review_backpressure(self):
        p = fixture()
        for i in range(7):
            add_job(p, index=i, task_id=f"other-unique-task-{i:02d}")
        result = propose(**p)
        self.assertEqual(result["status"], "global_review_backpressure")
        self.assertIsNone(result["candidate"])

    def test_queued_job_identity_also_blocks_repeat(self):
        p = fixture()
        jid = "223e4567-e89b-12d3-a456-426614174000"
        p["jobs"].append({"id": jid, "kind": "research.omniroute",
                          "dedupe_key": "f" * 64, "status": "queued",
                          "result": None, "updated_at": NOW - 10})
        p["job_tasks"][jid] = "gale-safe-source-01"
        self.assertEqual(propose(**p)["candidate"]["role"], "mike")

    def test_bad_role_and_invalid_clock_fail_content_free(self):
        p = fixture()
        add_job(p)
        p["job_roles"][JOB] = "Walter"
        self.assertEqual(propose(**p)["status"], "invalid_or_incomplete_evidence")
        p = fixture()
        p["now"] = "2026"
        self.assertEqual(propose(**p)["status"], "invalid_or_incomplete_evidence")

    def test_invalid_paired_routing_fails_closed(self):
        p = fixture()
        p["routing"]["tasks"].pop("gale-safe-source-01")
        self.assertEqual(propose(**p)["status"], "invalid_or_incomplete_evidence")

    def test_never_changes_input_snapshots(self):
        p = fixture()
        before = copy.deepcopy(p)
        propose(**p)
        self.assertEqual(p, before)


if __name__ == "__main__":
    unittest.main()
