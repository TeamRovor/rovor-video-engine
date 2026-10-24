"""Adversarial offline coverage policy tests: no network, worker or private state."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_specialist_coverage import CoverageError, choose

NOW = 1792839000
DIGEST = "a" * 64


def candidate(role="gale", task="task-gale-0001", key=None, priority=1):
    return {"role": role, "task_id": task,
            "dedupe_key": key or "packet-" + task,
            "source_sha256": DIGEST, "priority": priority}


def outcome(role="gale", key="packet-prior-0001", job="job-prior-0001",
            status="review_accepted", at=NOW-200, status_at=None):
    return {"role": role, "dedupe_key": key, "job_id": job,
            "status": status, "claimed_at": at,
            "status_at": at if status_at is None else status_at}


def select(candidates=None, outcomes=None, seen=None, **kwargs):
    candidates = [candidate()] if candidates is None else candidates
    outcomes = [] if outcomes is None else outcomes
    seen = {r["dedupe_key"] for r in outcomes} if seen is None else seen
    params = dict(now=NOW, seen_dedupe=seen, trusted_candidates=True,
                  trusted_outcomes=True, authoritative_ledger=True,
                  stop_present=False, other_job_running=False, owner_opt_in=True)
    params.update(kwargs)
    return choose(candidates, outcomes, **params)


class AdmissionTests(unittest.TestCase):
    def reject(self, reason, candidates=None, outcomes=None, seen=None, **kwargs):
        with self.assertRaises(CoverageError) as cm:
            select(candidates, outcomes, seen, **kwargs)
        self.assertEqual(str(cm.exception), reason)

    def test_stop_first_even_if_inputs_invalid(self):
        self.assertEqual(select(None, None, stop_present=True)["status"], "stopped")

    def test_missing_candidate_attestation(self):
        self.assertEqual(select(trusted_candidates=False)["status"], "unverified_authority")

    def test_missing_outcome_attestation(self):
        self.assertEqual(select(trusted_outcomes=False)["status"], "unverified_authority")

    def test_missing_ledger_attestation(self):
        self.assertEqual(select(authoritative_ledger=False)["status"], "unverified_authority")

    def test_missing_owner_opt_in(self):
        self.assertEqual(select(owner_opt_in=False)["status"], "unverified_authority")

    def test_running_worker_blocks(self):
        self.assertEqual(select(other_job_running=True)["status"], "unverified_authority")

    def test_boolean_clock_rejected(self):
        self.reject("invalid_clock", now=True)

    def test_future_outcome_rejected(self):
        self.reject("invalid_outcome_record", outcomes=[outcome(at=NOW+1)])

    def test_untrusted_role_rejected(self):
        self.reject("invalid_grounded_candidate", candidates=[candidate(role="walter")])

    def test_missing_source_digest_rejected(self):
        bad = candidate(); bad["source_sha256"] = "fake"
        self.reject("invalid_grounded_candidate", candidates=[bad])

    def test_bool_priority_rejected(self):
        bad = candidate(); bad["priority"] = True
        self.reject("invalid_grounded_candidate", candidates=[bad])

    def test_extra_candidate_field_rejected(self):
        bad = candidate(); bad["raw_private_text"] = "do not echo"
        self.reject("invalid_grounded_candidate", candidates=[bad])

    def test_duplicate_task_rejected_even_with_distinct_keys(self):
        self.reject("duplicate_grounded_candidate", candidates=[
            candidate(), candidate(key="packet-other-0001")])

    def test_duplicate_key_rejected_even_with_distinct_tasks(self):
        self.reject("duplicate_grounded_candidate", candidates=[
            candidate(), candidate(task="task-other-0001", key="packet-task-gale-0001")])

    def test_outcome_missing_from_seen_rejected(self):
        self.reject("incomplete_seen_ledger", outcomes=[outcome()], seen=set())

    def test_duplicate_outcome_job_rejected(self):
        self.reject("duplicate_or_replayed_outcome", outcomes=[
            outcome(), outcome(role="mike", key="packet-other-0001")])

    def test_duplicate_outcome_dedupe_rejected(self):
        self.reject("duplicate_or_replayed_outcome", outcomes=[
            outcome(), outcome(job="job-other-0001")])

    def test_unhashable_role_rejected_cleanly(self):
        bad = candidate(); bad["role"] = ["gale"]
        self.reject("invalid_grounded_candidate", candidates=[bad])

    def test_unknown_outcome_status_rejected(self):
        self.reject("invalid_outcome_record", outcomes=[outcome(status="success")])

    def test_private_error_text_not_echoed(self):
        bad = outcome(); bad["error"] = "PRIVATE_PROVIDER_SECRET"
        with self.assertRaises(CoverageError) as cm:
            select(outcomes=[bad])
        self.assertNotIn("PRIVATE_PROVIDER_SECRET", str(cm.exception))


class SelectionTests(unittest.TestCase):
    def test_running_outcome_blocks_even_if_caller_says_idle(self):
        result = select(outcomes=[outcome(status="running")])
        self.assertEqual(result["status"], "running_outcome_requires_reconciliation")
        self.assertIsNone(result["candidate"])

    def test_empty_candidates(self):
        self.assertEqual(select([])["status"], "no_unattempted_candidates")

    def test_returns_only_inert_proposal(self):
        result = select()
        self.assertEqual(result["status"], "candidate_only_not_enqueued")
        self.assertEqual(result["candidate"]["role"], "gale")
        self.assertTrue(result["requires_atomic_sqlite_claim"])
        self.assertTrue(result["requires_independent_review"])
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["queue_writes"], 0)


    def test_revised_source_digest_cannot_replay_same_task(self):
        revised = candidate(key="packet-new-digest-0001")
        decision = select(candidates=[revised], seen=set(),
                          attempted_task_ids=frozenset({"task-gale-0001"}),
                          trusted_task_mapping=True)
        self.assertEqual(decision["status"], "task_already_attempted")
        self.assertIsNone(decision["candidate"])

    def test_queued_task_identity_blocks_even_without_claimed_outcome(self):
        decision = select(seen={"sha-" + "a" * 64},
                          attempted_task_ids={"task-gale-0001"},
                          trusted_task_mapping=True)
        self.assertEqual(decision["status"], "task_already_attempted")

    def test_other_task_selected_when_one_was_attempted(self):
        options = [candidate("gale", "task-gale-0001"),
                   candidate("jane", "task-jane-0001")]
        decision = select(candidates=options, attempted_task_ids={"task-gale-0001"},
                          trusted_task_mapping=True)
        self.assertEqual(decision["candidate"]["task_id"], "task-jane-0001")
        self.assertTrue(decision["task_identity_ledger_verified"])
        self.assertFalse(decision["requires_verified_task_identity"])

    def test_unverified_or_invalid_task_mapping_fails_closed(self):
        for ids, trusted in (({"task-gale-0001"}, False),
                             ({"bad"}, True), ({"task-gale-0001"}, None),
                             (["task-gale-0001"], True), (None, True)):
            with self.subTest(ids=ids, trusted=trusted):
                decision = select(attempted_task_ids=ids, trusted_task_mapping=trusted)
                self.assertEqual(decision["status"], "task_identity_ledger_unverified")
                self.assertIsNone(decision["candidate"])

    def test_legacy_proposal_requires_task_identity_check(self):
        decision = select()
        self.assertFalse(decision["task_identity_ledger_verified"])
        self.assertTrue(decision["requires_verified_task_identity"])

    def test_seen_dedupe_never_replayed(self):
        self.assertEqual(select(seen={"packet-task-gale-0001"})["status"],
                         "no_unattempted_candidates")

    def test_less_served_role_wins_even_if_lower_priority(self):
        options = [candidate("gale", "task-gale-0001", priority=1),
                   candidate("jane", "task-jane-0001", priority=5)]
        result = select(options, [outcome("gale")])
        self.assertEqual(result["candidate"]["role"], "jane")

    def test_equal_coverage_oldest_claim_first(self):
        options = [candidate("gale", "task-gale-0001"),
                   candidate("jane", "task-jane-0001")]
        history = [outcome("gale", "packet-old-gale", "job-old-gale", at=NOW-20),
                   outcome("jane", "packet-old-jane", "job-old-jane", at=NOW-300)]
        self.assertEqual(select(options, history)["candidate"]["role"], "jane")

    def test_priority_breaks_same_role_tie(self):
        options = [candidate("gale", "task-gale-0001", priority=5),
                   candidate("gale", "task-gale-0002", priority=1)]
        self.assertEqual(select(options)["candidate"]["task_id"], "task-gale-0002")

    def test_deterministic_independent_of_candidate_order(self):
        options = [candidate("saul", "task-saul-0001"),
                   candidate("gale", "task-gale-0001")]
        self.assertEqual(select(options)["candidate"], select(list(reversed(options)))["candidate"])

    def test_recent_attempts_roll_off(self):
        options = [candidate("gale", "task-gale-0001"),
                   candidate("jane", "task-jane-0001")]
        history = [outcome("gale", at=NOW-86401)]
        self.assertEqual(select(options, history)["candidate"]["role"], "jane")
        self.assertEqual(select(options, history)["coverage"]["gale"]["attempts_24h"], 0)

    def test_one_recent_failure_does_not_cooldown(self):
        result = select(outcomes=[outcome(status="model_failed")])
        self.assertEqual(result["status"], "candidate_only_not_enqueued")
        self.assertFalse(result["coverage"]["gale"]["failure_cooldown"])

    def test_delayed_failure_cooldown_uses_status_time_not_claim(self):
        history = [outcome(key="packet-fail-0001", job="job-fail-0001",
                           status="model_failed", at=NOW-10000, status_at=NOW-200),
                   outcome(key="packet-fail-0002", job="job-fail-0002",
                           status="model_failed", at=NOW-9000, status_at=NOW-20)]
        self.assertEqual(select(outcomes=history)["status"], "failure_cooldown")

    def test_status_time_before_claim_rejected(self):
        with self.assertRaises(CoverageError) as cm:
            select(outcomes=[outcome(status="model_failed", at=NOW-20, status_at=NOW-30)])
        self.assertEqual(str(cm.exception), "invalid_outcome_record")

    def test_two_recent_failures_cooldown_role(self):
        history = [outcome("gale", "packet-fail-0001", "job-fail-0001", "model_failed", NOW-120),
                   outcome("gale", "packet-fail-0002", "job-fail-0002", "review_rejected", NOW-60)]
        options = [candidate("gale", "task-gale-0001"), candidate("jane", "task-jane-0001")]
        result = select(options, history)
        self.assertEqual(result["candidate"]["role"], "jane")
        self.assertTrue(result["coverage"]["gale"]["failure_cooldown"])

    def test_two_failures_without_other_role_returns_cooldown(self):
        history = [outcome(key="packet-fail-0001", job="job-fail-0001", status="model_failed"),
                   outcome(key="packet-fail-0002", job="job-fail-0002", status="model_failed")]
        self.assertEqual(select(outcomes=history)["status"], "failure_cooldown")

    def test_cooldown_expires_after_one_hour(self):
        history = [outcome(key="packet-fail-0001", job="job-fail-0001", status="model_failed", at=NOW-4000),
                   outcome(key="packet-fail-0002", job="job-fail-0002", status="model_failed", at=NOW-3600)]
        self.assertEqual(select(outcomes=history)["status"], "candidate_only_not_enqueued")

    def test_accepted_review_breaks_failure_streak(self):
        history = [outcome(key="packet-fail-0001", job="job-fail-0001", status="model_failed", at=NOW-200),
                   outcome(key="packet-ok-0001", job="job-ok-0001", status="review_accepted", at=NOW-100),
                   outcome(key="packet-fail-0002", job="job-fail-0002", status="model_failed", at=NOW-50)]
        self.assertEqual(select(outcomes=history)["status"], "candidate_only_not_enqueued")

    def test_pending_review_limits_role(self):
        history = [outcome(key="packet-pend-0001", job="job-pend-0001", status="review_ready"),
                   outcome(key="packet-pend-0002", job="job-pend-0002", status="pending_review")]
        self.assertEqual(select(outcomes=history)["status"], "role_review_backpressure")

    def test_pending_review_other_role_can_proceed(self):
        history = [outcome(key="packet-pend-0001", job="job-pend-0001", status="review_ready"),
                   outcome(key="packet-pend-0002", job="job-pend-0002", status="pending_review")]
        options = [candidate(), candidate("mike", "task-mike-0001")]
        self.assertEqual(select(options, history)["candidate"]["role"], "mike")

    def test_global_review_backpressure(self):
        history = [outcome(role=role, key="packet-pend-"+role, job="job-pend-"+role,
                           status="review_ready") for role in ("gale", "gus", "hank", "jane", "jesse", "mike", "saul")]
        self.assertEqual(select(outcomes=history)["status"], "global_review_backpressure")

    def test_completed_human_review_releases_backpressure(self):
        history = [outcome(key="packet-done-0001", job="job-done-0001", status="review_accepted"),
                   outcome(key="packet-done-0002", job="job-done-0002", status="review_rejected")]
        self.assertEqual(select(outcomes=history)["coverage"]["gale"]["awaiting_review"], 0)

    def test_old_unreviewed_draft_still_blocks_role(self):
        history = [outcome(key="packet-pend-0001", job="job-pend-0001", status="review_ready", at=NOW-90000),
                   outcome(key="packet-pend-0002", job="job-pend-0002", status="review_ready", at=NOW-90001)]
        self.assertEqual(select(outcomes=history)["status"], "role_review_backpressure")

    def test_metrics_no_private_job_identifiers(self):
        history = [outcome(key="packet-private-0001", job="job-private-0001")]
        report = str(select(outcomes=history))
        self.assertNotIn("packet-private-0001", report)
        self.assertNotIn("job-private-0001", report)

    def test_counter_accuracy(self):
        history = [outcome(key="packet-ok-0001", job="job-ok-0001", status="review_accepted"),
                   outcome(key="packet-fail-0001", job="job-fail-0001", status="model_failed")]
        stats = select(outcomes=history)["coverage"]["gale"]
        self.assertEqual(stats["attempts_24h"], 2)
        self.assertEqual(stats["accepted_24h"], 1)
        self.assertEqual(stats["failed_24h"], 1)


if __name__ == "__main__":
    unittest.main()
