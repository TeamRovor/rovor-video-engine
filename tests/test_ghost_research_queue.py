import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import interpreter_host_job as host


class ResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        self.state = self.root / 'state'
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)

    def submit(self):
        return worker.enqueue(self.conn, worker.RESEARCH_KIND, {}, 'jane-first')

    def test_default_worker_never_claims_model_job(self):
        job = self.submit()
        with mock.patch.object(host, 'main') as launch:
            self.assertIsNone(worker.run_once(self.conn, self.workspace))
            launch.assert_not_called()
        self.assertEqual(self.conn.execute('SELECT status FROM jobs WHERE id=?', (job,)).fetchone()[0], 'queued')

    def test_dedupe_refuses_second_model_dispatch(self):
        job = self.submit()
        self.assertEqual(self.submit(), job)
        self.conn.execute("UPDATE jobs SET status='succeeded' WHERE id=?", (job,))
        with mock.patch.object(host, 'main') as launch:
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_model_use=True))
            launch.assert_not_called()

    def test_expired_model_lease_requires_review_without_retry(self):
        job = self.submit()
        worker.claim(self.conn, 'crashed', now=100, allow_model_use=True)
        self.assertIsNone(worker.claim(self.conn, 'restart', now=500, allow_model_use=True))
        row = self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?', (job,)).fetchone()
        self.assertEqual(tuple(row), ('needs_review', 1))

    def test_stop_blocks_before_claim(self):
        job = self.submit()
        (self.state / 'STOP').touch()
        self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_model_use=True))
        self.assertEqual(self.conn.execute('SELECT attempts FROM jobs WHERE id=?', (job,)).fetchone()[0], 0)

    def fake_launch(self, args):
        output = Path(args[args.index('--output') + 1])
        self.assertIn('--approve-model-use', args)
        self.assertEqual(args[args.index('--stop-file') + 1], str(self.state / 'STOP'))
        receipts = output / 'receipts'
        receipts.mkdir(parents=True)
        (receipts / 'jane-finalcut-host-001.receipt.json').write_text(json.dumps({'status': 'completed_unverified', 'answer_sha256': 'a' * 64}))
        return 0

    def test_optin_preserves_receipt_and_does_not_claim_fact_approval(self):
        job = self.submit()
        with mock.patch.object(host, 'main', side_effect=self.fake_launch) as launch:
            result = worker.run_once(self.conn, self.workspace, allow_model_use=True)
            self.assertEqual(result['status'], 'succeeded')
            self.assertFalse(result['result']['facts_verified'])
            self.assertFalse(result['result']['app_control_verified'])
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_model_use=True))
            launch.assert_called_once()

    def test_failed_launch_is_not_retried(self):
        self.submit()
        with mock.patch.object(host, 'main', side_effect=ValueError('startup denied')) as launch:
            self.assertEqual(worker.run_once(self.conn, self.workspace, allow_model_use=True)['status'], 'failed')
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_model_use=True))
            launch.assert_called_once()

    def test_research_rejects_arbitrary_parameters(self):
        with self.assertRaises(ValueError):
            worker.enqueue(self.conn, worker.RESEARCH_KIND, {'shell': 'anything'}, 'bad')
