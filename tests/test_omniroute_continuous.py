from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
import uuid
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import omniroute_continuous as continuous


class ContinuousTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)
        refresh = mock.patch.object(continuous, 'latest_public_tasks', side_effect=ValueError('offline'))
        refresh.start()
        self.addCleanup(refresh.stop)

    def enqueue(self, key):
        return worker.enqueue(self.conn, worker.OMNI_KIND,
                              {'assignment': key}, 'rovor-' + key, now=100)

    def claim(self, **kwargs):
        args = dict(owner='test', now=1000, allow_omniroute_model_use=True,
                    omni_continuous=True, omni_pace_seconds=601, omni_max_24h=144)
        args.update(kwargs)
        return worker.claim(self.conn, **args)

    def test_catalogue_has_168_distinct_outputs_and_balanced_roles(self):
        catalogue = continuous.assignments()
        self.assertEqual(len(catalogue), 168)
        self.assertEqual(len({json.dumps(x, sort_keys=True) for x in catalogue.values()}), 168)
        self.assertEqual([x['role'] for x in list(catalogue.values())[:7]],
                         list(continuous.ROLE_TOPICS))
        for role in continuous.ROLE_TOPICS:
            self.assertEqual(sum(x['role'] == role for x in catalogue.values()), 24)

    def test_existing_three_jobs_and_fourteen_claims_can_resume_with_explicit_new_budget(self):
        keys = list(continuous.assignments())
        for n, key in enumerate(keys[:14]):
            job = self.enqueue(key)
            self.conn.execute("UPDATE jobs SET status='needs_review',result=? WHERE id=?",
                              (json.dumps({'draft_status': 'draft_completed_needs_review'}), job))
            self.conn.execute("INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)",
                              (job, 'claimed', '{}', 200 + n))
        for key in keys[14:17]:
            self.enqueue(key)
        claim = self.claim(now=2000)
        self.assertIsNotNone(claim)
        self.assertIsNone(self.claim(owner='second', now=2000))

    def test_spacing_is_atomic_across_two_connections(self):
        for key in list(continuous.assignments())[:2]:
            self.enqueue(key)
        def attempt(index):
            conn = sqlite3.connect(str(self.state / 'jobs.sqlite3'),
                                   isolation_level=None, timeout=20)
            conn.row_factory = sqlite3.Row
            try:
                return worker.claim(conn, 'thread-' + str(index), 1000,
                    allow_omniroute_model_use=True, omni_continuous=True,
                    omni_max_24h=144, omni_pace_seconds=601)
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertEqual(sum(x is not None for x in results), 1)

    def test_next_claim_waits_after_completed_previous_job(self):
        for key in list(continuous.assignments())[:2]:
            self.enqueue(key)
        first = self.claim()
        self.conn.execute("UPDATE jobs SET status='needs_review',result=?,lease_owner=NULL,lease_until=NULL WHERE id=?",
                          (json.dumps({'draft_status': 'draft_completed_needs_review'}), first['id']))
        self.assertIsNone(self.claim(now=1600))
        self.assertIsNotNone(self.claim(now=1601))

    def test_large_budget_and_new_assignments_require_new_opt_in(self):
        self.enqueue(next(iter(continuous.assignments())))
        with self.assertRaises(ValueError):
            worker.claim(self.conn, 'legacy', 1000, allow_omniroute_model_use=True,
                         omni_max_24h=144)
        self.assertIsNone(worker.claim(self.conn, 'legacy', 1000,
                                      allow_omniroute_model_use=True))
        with self.assertRaises(ValueError):
            self.claim(omni_pace_seconds=1)

    def test_seed_preserves_queued_jobs_and_never_replays_terminal_work(self):
        self.assertEqual(continuous.seed(self.conn, self.state), 'distinct_assignment_queued')
        self.assertEqual(continuous.seed(self.conn, self.state), 'existing_queue')
        self.conn.execute("UPDATE jobs SET status='needs_review'")
        self.assertEqual(continuous.seed(self.conn, self.state), 'distinct_assignment_queued')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM jobs').fetchone()[0], 2)

    def test_catalogue_exhaustion_is_explicit_and_does_not_generate_duplicates(self):
        for key in continuous.assignments():
            self.enqueue(key)
        self.conn.execute("UPDATE jobs SET status='needs_review'")
        self.assertEqual(continuous.seed(self.conn, self.state),
                         'catalogue_exhausted_new_work_required')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM jobs').fetchone()[0], 168)

    def test_stop_prevents_seed_and_tick_without_model_or_state_change(self):
        (self.state / 'STOP').touch()
        with mock.patch.object(continuous.worker, 'run_once', side_effect=AssertionError):
            self.assertEqual(continuous.tick(self.state, self.workspace)['status'], 'stop_requested')
        self.assertEqual(continuous.seed(self.conn, self.state), 'stop_requested')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_failure_circuit_is_not_bypassed_by_larger_quota(self):
        keys = list(continuous.assignments())
        for n, key in enumerate(keys[:3]):
            job = self.enqueue(key)
            self.conn.execute("UPDATE jobs SET status='needs_review',result=? WHERE id=?",
                              (json.dumps({'draft_status': 'needs_review_no_auto_retry'}), job))
            self.conn.execute("INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)",
                              (job, 'claimed', '{}', 200 + n))
        self.enqueue(keys[3])
        self.assertIsNone(self.claim(now=2000))

    def test_dry_tick_mock_executes_only_one_job_and_writes_no_private_text_to_heartbeat(self):
        def complete(conn, workspace, **kw):
            self.assertTrue(kw['omni_continuous'])
            self.assertEqual(kw['omni_max_24h'], 144)
            return {'result': {'review_status': 'draft_ready_for_human_review',
                               'private': 'DO_NOT_EXPOSE'}}
        with mock.patch.object(worker, 'run_once', side_effect=complete) as run:
            result = continuous.tick(self.state, self.workspace, now=1000)
        self.assertEqual(run.call_count, 1)
        self.assertTrue(result['review_ready'])
        self.assertNotIn('DO_NOT_EXPOSE', (self.state / 'continuous-status.json').read_text())

    def test_unknown_assignment_is_rejected_before_queue_write(self):
        with self.assertRaises(ValueError):
            self.enqueue('not-approved')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_live_public_queue_replenishes_without_repeating_unchanged_tasks(self):
        task = {'id': 'real-task', 'title': 'Fix worker', 'status': 'ready', 'priority': 1,
                'acceptance': 'Verify a distinct useful result', 'scopes': ['tools/example.py']}
        with mock.patch.object(continuous, 'pinned_public_tasks', return_value=[task]):
            for form in continuous.DELIVERABLES:
                self.assertEqual(continuous.seed(self.conn, self.state, ('a' * 40, [task])),
                                 'new_public_task_assignment_queued')
                self.conn.execute("UPDATE jobs SET status='needs_review'")
            # Same task from a newer main commit produces no duplicate public assignments.
            self.assertEqual(continuous.seed(self.conn, self.state, ('b' * 40, [task])),
                             'distinct_assignment_queued')
            public_count = self.conn.execute("SELECT count(*) FROM jobs WHERE dedupe_key LIKE 'continuous-public-%'").fetchone()[0]
            self.assertEqual(public_count, 4)

    def test_changed_acceptance_creates_new_work_but_forged_public_text_is_rejected(self):
        task = {'id': 'real-task', 'title': 'Fix worker', 'status': 'ready', 'priority': 1,
                'acceptance': 'Actual pinned acceptance', 'scopes': []}
        payload = continuous.public_payload(task, 'a' * 40, 'plan')
        with mock.patch.object(continuous, 'pinned_public_tasks', return_value=[task]):
            self.assertEqual(continuous.public_assignment(payload)['role'], 'mike')
            forged = json.loads(json.dumps(payload))
            forged['public_task']['acceptance'] = 'Unverified private text'
            with self.assertRaises(ValueError):
                worker.enqueue(self.conn, worker.OMNI_KIND, forged, 'forged')
            continuous.seed(self.conn, self.state, ('a' * 40, [task]))
            self.conn.execute("UPDATE jobs SET status='needs_review'")
            task['acceptance'] = 'A new measurable acceptance criterion'
            self.assertEqual(continuous.seed(self.conn, self.state, ('b' * 40, [task])),
                             'new_public_task_assignment_queued')

    def test_assignment_uses_existing_runner_exactly_once_and_saves_manifest(self):
        import ghost_omniroute_job as gateway
        import omniroute_workpack_runner as workpack
        payload = {'assignment': next(iter(continuous.assignments()))}
        job = str(uuid.uuid4())
        calls = []
        def completion(model, prompt, key):
            calls.append((model, prompt))
            self.assertIn('restart recovery', prompt)
            return ('Proposed implementation plan. These are unrun checks.\n' +
                    'Verify durable ownership and STOP before each operation.\n' * 8,
                    {'prompt_tokens': 100, 'completion_tokens': 100, 'total_tokens': 200})
        with mock.patch.object(gateway, 'verify_route', return_value='rovor-fast-free-v1'), \
             mock.patch.object(workpack, 'access_key', return_value='test-key'):
            result = continuous.execute(self.state, job, payload, catalog=[], completion=completion)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['draft_status'], 'draft_completed_needs_review')
        self.assertTrue(result['user_review_required'])
        self.assertTrue((self.state / 'omniroute-drafts' / job / 'assignment.json').exists())
        with mock.patch.object(gateway, 'verify_route', return_value='rovor-fast-free-v1'), \
             mock.patch.object(workpack, 'access_key', side_effect=AssertionError('No replay')):
            with self.assertRaises(ValueError):
                continuous.execute(self.state, job, payload, catalog=[], completion=completion)

    def test_concise_deliverables_use_proportional_reviewed_source_budgets(self):
        import ghost_omniroute_job as gateway
        import omniroute_workpack_runner as workpack
        cases = [('checklist',9000,250),('handoff',9000,300),
                 ('plan',11000,350),('tests',14500,450)]
        seen=[]
        for form,budget,words in cases:
            with self.subTest(form=form):
                slug='continuous-v1-mike-0-'+form
                job=str(uuid.uuid4())
                def completion(model,prompt,key):
                    self.assertIn('under '+str(words)+' words',prompt)
                    self.assertLess(len(prompt),28000)
                    seen.append(form)
                    return ('Proposed public-source checklist for review; '
                            'tests have not been run.',
                            {'prompt_tokens':500,'completion_tokens':55,
                             'total_tokens':555})
                with mock.patch.object(gateway,'verify_route',
                                       return_value='rovor-fast-free-v1'):
                    with mock.patch.object(workpack,'access_key',
                        return_value='test-key'):
                        result=continuous.execute(self.state,job,
                            {'assignment':slug},catalog=[],completion=completion)
                self.assertEqual(result['review_status'],
                                 'draft_ready_for_human_review')
                receipt=self.state/'omniroute-drafts'/job/(
                    'walter-v2-mike-worker-guard.receipt.json')
                stored=json.loads(receipt.read_text())
                self.assertEqual(stored['source_budget_chars'],budget)
                self.assertEqual(stored['provenance']['source_budget_chars'],budget)
                self.assertFalse(stored['mac_control_verified'])
        self.assertEqual(seen,[x[0] for x in cases])

    def test_pre_inference_errors_are_recorded_and_trip_circuit_after_three_attempts(self):
        keys = list(continuous.assignments())
        for key in keys[:4]:
            self.enqueue(key)
        with mock.patch.object(continuous, 'execute', side_effect=ValueError('private failure')):
            for n in range(3):
                result = worker.run_once(self.conn, self.workspace, owner='test',
                    now=1000 + n * 601, allow_omniroute_model_use=True,
                    omni_continuous=True, omni_max_24h=144, omni_pace_seconds=601)
                self.assertEqual(result['status'], 'needs_review')
        self.assertIsNone(self.claim(now=2803))
        status = continuous.queue_health(self.conn, self.state, now=2803)
        self.assertEqual(status['reason'], 'failure_circuit_requires_review')
        self.assertEqual(status['consecutive_recorded_failures'], 3)


if __name__ == '__main__':
    unittest.main()
