"""Real queue/loop/packet checks; inference is always mocked."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import ghost_worker as worker
import ghost_worker_loop as loop
import ghost_omniroute_feed as feed
import ghost_omniroute_job as omni
import omniroute_workpack_runner as workpack
import omniroute_draft_review as review


class FeedTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name).resolve() / 'state'
        self.db = worker.connect(self.state); self.addCleanup(self.db.close)

    def test_stop_blocks_submission_and_default_loop_does_not_feed(self):
        loop.request_stop(self.state)
        self.assertEqual(feed.feed(self.db, self.state, ROOT)['status'], 'stopped')
        self.assertEqual(loop.poll(self.db, ROOT, self.state, worker_id='test',
                                  allow_omniroute_model_use=True)['executed'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 0)

    def test_packet_is_bounded_and_validated_before_enqueue(self):
        packet, prompt, _ = workpack.load_packet(ROOT, feed.PLAN[0][0])
        self.assertEqual(packet['id'], feed.PLAN[0][1])
        self.assertLess(len(prompt), 38000)
        with mock.patch.object(workpack, 'load_packet', side_effect=ValueError('missing')):
            with self.assertRaises(ValueError): feed.feed(self.db, self.state, ROOT)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 0)

    def test_existing_queue_is_preserved_and_all_terminal_states_never_replay(self):
        job = worker.enqueue(self.db, worker.OMNI_KIND, {'packet': 'runner-blocker'}, 'existing')
        self.assertEqual(feed.feed(self.db, self.state, ROOT)['status'], 'existing_work')
        self.db.execute("UPDATE jobs SET status='needs_review' WHERE id=?", (job,))
        new = feed.feed(self.db, self.state, ROOT)
        self.assertEqual(new['submitted'], 1)
        for status in ('queued', 'running', 'failed', 'needs_review', 'succeeded'):
            self.db.execute('UPDATE jobs SET status=? WHERE id=?', (status, new['job_id']))
            self.assertEqual(feed.feed(self.db, self.state, ROOT)['submitted'], 0)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 2)

    def test_loop_requires_separate_approval(self):
        for options in ({}, {'allow_omniroute_model_use': True, 'allow_model_use': True}):
            with self.assertRaises(ValueError):
                loop.poll(self.db, ROOT, self.state, worker_id='test',
                          allow_omniroute_work_plan=True, **options)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0], 0)

    def test_real_loop_executes_one_plan_job_and_never_retries_failed_inference(self):
        with mock.patch.object(omni, 'execute', side_effect=ValueError('offline')) as execute:
            result = loop.poll(self.db, ROOT, self.state, worker_id='test', max_jobs=1,
                               allow_omniroute_model_use=True, allow_omniroute_work_plan=True)
        self.assertEqual(result['work_plan']['submitted'], 1)
        self.assertEqual(result['executed'], 1)
        execute.assert_called_once()
        row = self.db.execute('SELECT * FROM jobs').fetchone()
        self.assertEqual((row['status'], row['attempts']), ('needs_review', 1))
        self.assertEqual(json.loads(row['payload']), {'packet': 'unattended-readiness'})
        self.assertEqual(feed.feed(self.db, self.state, ROOT)['status'], 'plan_exhausted_review_required')

    def test_feeder_does_not_bypass_existing_rolling_quota(self):
        for i in range(5):
            job = worker.enqueue(self.db, worker.OMNI_KIND, {'packet': 'runner-blocker'}, str(i))
            worker.claim(self.db, 'quota', allow_omniroute_model_use=True)
            self.db.execute("UPDATE jobs SET status='needs_review' WHERE id=?", (job,))
        feed.feed(self.db, self.state, ROOT)
        self.assertIsNone(worker.claim(self.db, 'capped', allow_omniroute_model_use=True))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0], 1)

    def test_full_plan_to_private_receipt_and_review_with_mock_completion(self):
        catalog = [{'name': name, 'strategy': 'priority', 'isHidden': False,
                    'models': [{'kind': 'model', 'providerId': 'openrouter', 'model': m}
                               for m in models]}
                   for name, models in dict.fromkeys(omni.ROUTES.values())]
        with mock.patch.object(omni, 'read_combo_catalog', return_value=catalog), \
             mock.patch.object(workpack, 'access_key', return_value='fixture-key'), \
             mock.patch.object(workpack, 'http_completion', return_value=(
                 'Finite plan requires review; no host execution asserted.',
                 {'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130})) as completion:
            result = loop.poll(self.db, ROOT, self.state, worker_id='test', max_jobs=1,
                               allow_omniroute_model_use=True, allow_omniroute_work_plan=True)
        completion.assert_called_once()
        row = self.db.execute('SELECT * FROM jobs').fetchone()
        output = json.loads(row['result'])
        self.assertEqual(output['draft_status'], 'draft_completed_needs_review')
        self.assertEqual(output['review_status'], 'draft_ready_for_human_review')
        receipt = Path(output['receipt'])
        self.assertFalse(review.inspect(ROOT, receipt.parent, 'unattended-readiness')['approval_granted'])
        self.assertEqual(receipt.parent.stat().st_mode & 0o777, 0o700)
        self.assertNotIn('fixture-key', receipt.read_text())
        self.assertEqual(feed.feed(self.db, self.state, ROOT)['submitted'], 0)


if __name__ == '__main__': unittest.main()
