"""Offline regression: public research must target actual code and an eligible owner."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_public_task_grounding import GroundingError, select

COMMIT = "a" * 40
SOURCE = b"def checked_worker():\n    return 'public'\n"
PATH = "tools/omniroute_dispatch_policy.py"


def task(ident="omniroute-issue", *, path=PATH, status="ready", deps=None, priority=1):
    return {"id": ident, "title": "Fix the verified OmniRoute dispatch failure",
            "acceptance": "Verify the worker rejects failed drafts with one deterministic test.",
            "status": status, "owner": "Verified Mac worker" if status == "active" else None,
            "priority": priority, "depends_on": [] if deps is None else deps,
            "scopes": [path]}


def fixtures(tasks=None, sources=None):
    ts = [task()] if tasks is None else tasks
    src = {PATH: SOURCE} if sources is None else sources
    return {"queue": {"version": 1, "tasks": ts},
            "routing": {"version": 1, "tasks": {
                t["id"]: {"lane": "integration", "requires": ["hosted-ci"]}
                for t in ts}},
            "commit": COMMIT, "source_bytes": src,
            "source_digests": {k: hashlib.sha256(v).hexdigest() for k, v in src.items()},
            "trusted_pinned_snapshot": True, "authoritative_ledger": True,
            "seen_dedupe": set(), "stop_present": False}


class GroundedSelectionTests(unittest.TestCase):
    def run_select(self, **changes):
        args = fixtures()
        args.update(changes)
        return select(**args)

    def test_one_real_grounded_candidate(self):
        result = self.run_select()
        self.assertEqual(result["status"], "grounded_proposal_review_only")
        candidate = result["candidate"]
        self.assertEqual(candidate["role"], "mike")
        self.assertEqual(candidate["source_path"], PATH)
        self.assertEqual(candidate["source_sha256"], hashlib.sha256(SOURCE).hexdigest())
        self.assertEqual(candidate["pinned_commit"], COMMIT)
        self.assertFalse(candidate["model_use_authorized"])
        self.assertFalse(candidate["external_effects_allowed"])
        self.assertTrue(candidate["review_required"])
        self.assertNotIn("def checked_worker", repr(candidate))

    def test_dedupe_is_stable_across_unrelated_main_commits(self):
        a = self.run_select()["candidate"]["dedupe_key"]
        b = self.run_select(commit="b" * 40)["candidate"]["dedupe_key"]
        self.assertEqual(a, b)

    def test_source_edit_changes_identity(self):
        a = self.run_select()["candidate"]["dedupe_key"]
        data = b"def checked_worker():\n    return False\n"
        b = self.run_select(source_bytes={PATH: data},
                            source_digests={PATH: hashlib.sha256(data).hexdigest()})["candidate"]["dedupe_key"]
        self.assertNotEqual(a, b)

    def test_seen_dedupe_never_replayed(self):
        key = self.run_select()["candidate"]["dedupe_key"]
        self.assertEqual(self.run_select(seen_dedupe={key})["status"], "no_eligible_grounded_task")

    def test_stop_default_is_fail_closed(self):
        args = fixtures()
        args.pop("stop_present")
        self.assertEqual(select(**args)["status"], "stopped")

    def test_unverified_snapshot_is_not_admitted(self):
        self.assertEqual(self.run_select(trusted_pinned_snapshot=False)["status"], "pinned_snapshot_unverified")

    def test_unverified_commit_is_not_admitted(self):
        self.assertEqual(self.run_select(commit="main")["status"], "pinned_snapshot_unverified")

    def test_ledger_required(self):
        self.assertEqual(self.run_select(authoritative_ledger=False)["status"], "ledger_unverified")
        self.assertEqual(self.run_select(seen_dedupe=None)["status"], "ledger_unverified")

    def test_blocked_task_never_used_even_with_owner_optin(self):
        args = fixtures([task(status="blocked")])
        self.assertEqual(select(**args, approved_active_ids=["omniroute-issue"],
                                trusted_owner_approval=True)["status"], "no_eligible_grounded_task")

    def test_done_task_never_used(self):
        self.assertEqual(select(**fixtures([task(status="done")]))["status"], "no_eligible_grounded_task")

    def test_active_task_requires_explicit_owner_optin(self):
        args = fixtures([task(status="active")])
        self.assertEqual(select(**args)["status"], "no_eligible_grounded_task")
        self.assertEqual(select(**args, approved_active_ids=["omniroute-issue"])["status"],
                         "owner_approval_unverified")
        self.assertEqual(select(**args, approved_active_ids=["omniroute-issue"],
                                trusted_owner_approval=True)["status"], "grounded_proposal_review_only")

    def test_active_owner_must_be_present(self):
        t = task(status="active")
        t["owner"] = ""
        self.assertEqual(select(**fixtures([t]), approved_active_ids=[t["id"]],
                                trusted_owner_approval=True)["status"], "no_eligible_grounded_task")

    def test_ready_with_owner_not_used(self):
        t = task()
        t["owner"] = "Other worker"
        self.assertEqual(select(**fixtures([t]))["status"], "no_eligible_grounded_task")

    def test_unfinished_dependency_blocks(self):
        a = task("omniroute-issue", deps=["upstream-task"])
        b = task("upstream-task", status="blocked")
        self.assertEqual(select(**fixtures([a, b]))["status"], "no_eligible_grounded_task")

    def test_completed_dependency_allows(self):
        a = task("omniroute-issue", deps=["upstream-task"])
        b = task("upstream-task", status="done")
        self.assertEqual(select(**fixtures([a, b]))["status"], "grounded_proposal_review_only")

    def test_unknown_dependency_is_not_silently_ignored(self):
        self.assertEqual(select(**fixtures([task(deps=["missing-task"])]))["status"],
                         "no_eligible_grounded_task")

    def test_host_only_requirement_rejected(self):
        args = fixtures()
        args["routing"]["tasks"]["omniroute-issue"]["requires"] = ["local-exec"]
        self.assertEqual(select(**args)["status"], "no_eligible_grounded_task")

    def test_unknown_capability_rejected(self):
        args = fixtures()
        args["routing"]["tasks"]["omniroute-issue"]["requires"] = ["superuser"]
        self.assertEqual(select(**args)["status"], "no_eligible_grounded_task")

    def test_missing_route_rejected(self):
        args = fixtures()
        args["routing"]["tasks"] = {}
        with self.assertRaisesRegex(GroundingError, "invalid_paired_queue"):
            select(**args)

    def test_duplicate_task_id_rejected(self):
        with self.assertRaisesRegex(GroundingError, "invalid_paired_queue"):
            select(**fixtures([task(), task()]))

    def test_no_code_source_rejects_generic_task(self):
        t = task(path="subsystem:omniroute-general")
        self.assertEqual(select(**fixtures([t]))["status"], "no_eligible_grounded_task")

    def test_no_mike_default_for_unknown_code(self):
        path = "tools/unclassified_utility.py"
        data = b"def helper(): pass\n"
        self.assertEqual(select(**fixtures([task(path=path)], {path: data}))["status"],
                         "no_eligible_grounded_task")

    def test_source_not_in_exact_task_scope(self):
        self.assertEqual(select(**fixtures([task(path="tools/omniroute_other.py")]))["status"],
                         "no_eligible_grounded_task")

    def test_rejects_forged_digest(self):
        with self.assertRaisesRegex(GroundingError, "source_digest_mismatch"):
            self.run_select(source_digests={PATH: "b" * 64})

    def test_rejects_non_utf8(self):
        data = b"\xff\xfe"
        with self.assertRaisesRegex(GroundingError, "source_snapshot_unverified"):
            self.run_select(source_bytes={PATH: data},
                            source_digests={PATH: hashlib.sha256(data).hexdigest()})

    def test_rejects_embedded_nul(self):
        data = b"def f():\x00pass"
        with self.assertRaisesRegex(GroundingError, "source_snapshot_unverified"):
            self.run_select(source_bytes={PATH: data},
                            source_digests={PATH: hashlib.sha256(data).hexdigest()})

    def test_rejects_oversized_source(self):
        data = b"a" * 19001
        with self.assertRaisesRegex(GroundingError, "source_snapshot_unverified"):
            self.run_select(source_bytes={PATH: data},
                            source_digests={PATH: hashlib.sha256(data).hexdigest()})

    def test_rejects_private_env_path(self):
        path = "tools/.env.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["status"],
                         "no_eligible_grounded_task")

    def test_rejects_parent_traversal_path(self):
        path = "tools/../omniroute_dispatch_policy.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["status"],
                         "no_eligible_grounded_task")

    def test_prefers_implementation_over_test_file(self):
        t = task()
        t["scopes"].insert(0, "tests/test_omniroute_dispatch_policy.py")
        src = {"tests/test_omniroute_dispatch_policy.py": b"def test_a(): pass\n", PATH: SOURCE}
        self.assertEqual(select(**fixtures([t], src))["candidate"]["source_path"], PATH)

    def test_tests_only_go_to_hank_without_specific_role(self):
        path = "tests/test_generic_health.py"
        result = select(**fixtures([task(path=path)], {path: SOURCE}))
        self.assertEqual(result["candidate"]["role"], "hank")

    def test_tests_of_specialist_component_not_assigned_to_hank(self):
        path = "tests/test_blender_camera.py"
        result = select(**fixtures([task(path=path)], {path: SOURCE}))
        self.assertEqual(result["candidate"]["role"], "gale")

    def test_jane_specialist(self):
        path = "tools/fcp_isolated_library.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["candidate"]["role"], "jane")

    def test_jesse_specialist(self):
        path = "evan-engine/moho_visemes.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["candidate"]["role"], "jesse")

    def test_gus_business_operations(self):
        path = "business/operations/ops_worker.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["candidate"]["role"], "gus")

    def test_saul_business_marketing(self):
        path = "business/marketing/campaigns.py"
        self.assertEqual(select(**fixtures([task(path=path)], {path: SOURCE}))["candidate"]["role"], "saul")

    def test_ambiguous_specialist_scope_rejected(self):
        t = task()
        t["scopes"].append("tools/fcp_library.py")
        self.assertEqual(select(**fixtures([t], {PATH: SOURCE, "tools/fcp_library.py": SOURCE}))["status"],
                         "no_eligible_grounded_task")

    def test_sorted_priority_and_no_four_generic_variants(self):
        t1 = task("omniroute-low", priority=9)
        t2 = task("omniroute-high", priority=1)
        result = select(**fixtures([t1, t2]))
        self.assertEqual(result["candidate"]["task_id"], "omniroute-high")
        self.assertEqual(result["candidate"]["dedupe_key"].count("grounded-public-v1-"), 1)

    def test_no_mutation_of_caller_inputs(self):
        args = fixtures()
        before = copy.deepcopy(args)
        select(**args)
        self.assertEqual(args, before)

    def test_invalid_source_digest_map_rejected(self):
        with self.assertRaisesRegex(GroundingError, "source_snapshot_unverified"):
            self.run_select(source_digests={})

    def test_rejects_invalid_owner_approval_id(self):
        with self.assertRaisesRegex(GroundingError, "invalid_owner_approval"):
            self.run_select(approved_active_ids=["not-in-queue"], trusted_owner_approval=True)

    def test_sanitized_errors_do_not_echo_source(self):
        secret = b"PRIVATE_TOKEN_SHOULD_NOT_LEAK\n"
        with self.assertRaises(GroundingError) as e:
            self.run_select(source_bytes={PATH: secret}, source_digests={PATH: "0" * 64})
        self.assertNotIn("PRIVATE_TOKEN", str(e.exception))


if __name__ == "__main__":
    unittest.main()
