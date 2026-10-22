"""Queue and stop/recovery checks; native app calls are simulated."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import ghost_worker_loop as loop
import fcp_native_auto_import as native
import jane_native_worker as launcher


class NativeQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        (self.workspace / 'candidates').mkdir()
        self.state = self.root / 'state'
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)

    def submit(self, payload=None):
        return worker.enqueue(self.conn, worker.NATIVE_KIND,
                              payload or {'candidates': 'candidates'}, 'native-test')

    def row(self, job):
        return self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?', (job,)).fetchone()

    def prepare(self, candidates, output):
        self.assertEqual(candidates, self.workspace / 'candidates')
        output.mkdir()
        return {'status': 'ready_to_dispatch_not_launched'}

    def dispatch(self, output, report, **kwargs):
        self.assertEqual(kwargs['stop_file'], self.state / 'STOP')
        report['status'] = 'apple_events_sent_timeline_unverified'
        (output / 'native-auto-import-receipt.json').write_text(json.dumps(report))
        return report

    def test_default_and_model_only_worker_skip_native_jobs(self):
        job = self.submit()
        with mock.patch.object(native, 'prepare') as start:
            self.assertIsNone(worker.run_once(self.conn, self.workspace))
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_model_use=True))
            start.assert_not_called()
        self.assertEqual(tuple(self.row(job)), ('queued', 0))

    def test_opt_in_dispatches_once_and_retains_unverified_state(self):
        job = self.submit()
        self.assertEqual(job, self.submit())
        with mock.patch.object(native, 'prepare', side_effect=self.prepare), \
             mock.patch.object(native, 'dispatch', side_effect=self.dispatch) as dispatched:
            result = worker.run_once(self.conn, self.workspace, allow_native_import=True)
            self.assertEqual(result['status'], 'succeeded')
            self.assertFalse(result['result']['native_timeline_verified'])
            self.assertTrue(Path(result['result']['native_receipt']).is_file())
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_native_import=True))
            dispatched.assert_called_once()
        self.assertEqual(tuple(self.row(job)), ('succeeded', 1))

    def test_crashed_native_lease_never_requeues(self):
        job = self.submit()
        self.assertIsNotNone(worker.claim(self.conn, 'crashed', now=100, allow_native_import=True))
        self.assertIsNone(worker.claim(self.conn, 'restart', now=521, allow_native_import=True))
        self.assertEqual(tuple(self.row(job)), ('needs_review', 1))

    def test_native_failure_requires_review_without_retry(self):
        job = self.submit()
        with mock.patch.object(native, 'prepare', side_effect=ValueError('DTD rejected')):
            self.assertEqual(worker.run_once(self.conn, self.workspace, allow_native_import=True)['status'], 'needs_review')
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_native_import=True))
        self.assertEqual(tuple(self.row(job)), ('needs_review', 1))

    def test_stop_before_claim_leaves_job_queued(self):
        job = self.submit()
        (self.state / 'STOP').touch()
        self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_native_import=True))
        self.assertEqual(tuple(self.row(job)), ('queued', 0))

    def test_invalid_payloads_rejected(self):
        for payload in ({'candidates': '../outside'}, {'candidates': '/outside'},
                        {'candidates': 1}, {'candidates': 'candidates', 'shell': 'anything'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                worker.enqueue(self.conn, worker.NATIVE_KIND, payload, 'bad')

    def test_symlink_escape_never_reaches_preparation(self):
        (self.workspace / 'alias').symlink_to(self.root, target_is_directory=True)
        self.submit({'candidates': 'alias'})
        with mock.patch.object(native, 'prepare') as start:
            self.assertEqual(worker.run_once(self.conn, self.workspace, allow_native_import=True)['status'], 'needs_review')
            start.assert_not_called()

    def test_loop_forwards_native_opt_in_and_reports_mutation_capability(self):
        self.submit()
        with mock.patch.object(native, 'prepare', side_effect=self.prepare), \
             mock.patch.object(native, 'dispatch', side_effect=self.dispatch):
            result = loop.poll(self.conn, self.workspace, self.state, worker_id='native',
                               max_jobs=1, max_seconds=1, allow_native_import=True)
        self.assertEqual(result['succeeded'], 1)
        self.assertTrue(result['native_import_enabled'])
        self.assertFalse(result['read_only'])
        self.assertFalse(result['model_use_enabled'])

    def test_stop_between_native_events_prevents_portrait(self):
        output = self.workspace / 'prepared'
        output.mkdir()
        for label, _, _ in native.LABELS:
            (output / (label + '-auto.fcpxml')).write_text(label)
        target = output / 'ROVOR-Jane-Test.fcpbundle'
        report = {'status': 'ready_to_dispatch_not_launched', 'target_library': str(target),
                  'xml_hashes': {label: native.sha(output / (label + '-auto.fcpxml'))
                                 for label, _, _ in native.LABELS}}
        native.receipt_write(output, report)
        calls = []
        def first_event(command, **kwargs):
            calls.append(command)
            target.mkdir()
            (self.state / 'STOP').touch()
            return subprocess.CompletedProcess(command, 0)
        with mock.patch.object(native, 'APP', self.workspace):
            result = native.dispatch(output, report, run=first_event, stop_file=self.state / 'STOP')
        self.assertEqual(result['status'], 'cancelled_before_next_event')
        self.assertEqual(len(calls), 1)
        self.assertFalse(result['native_timeline_verified'])

    def test_launcher_preview_does_not_create_state(self):
        with mock.patch.object(launcher, 'candidate_folder', return_value=self.workspace / 'candidates'):
            (self.workspace / 'candidates/native-candidate-receipt.json').write_text(
                json.dumps({'fcpxml_sha256': {'landscape': 'a'*64, 'portrait': 'b'*64}}))
            result = launcher.run(self.workspace)
        self.assertFalse(result['execute'])
        self.assertFalse((self.workspace / 'jane-native-worker-state').exists())

    def test_launcher_restart_never_redispatches_terminal_job(self):
        (self.workspace / 'candidates/native-candidate-receipt.json').write_text(
            json.dumps({'fcpxml_sha256': {'landscape': 'a'*64, 'portrait': 'b'*64}}))
        def local_dispatch(output, report, **kwargs):
            report['status'] = 'apple_events_sent_timeline_unverified'
            (output / 'native-auto-import-receipt.json').write_text(json.dumps(report))
            return report
        with mock.patch.object(launcher, 'candidate_folder', return_value=self.workspace / 'candidates'), \
             mock.patch.object(native, 'prepare', side_effect=self.prepare), \
             mock.patch.object(native, 'dispatch', side_effect=local_dispatch) as dispatched:
            first = launcher.run(self.workspace, True)
            second = launcher.run(self.workspace, True)
        self.assertEqual(first['job_id'], second['job_id'])
        self.assertEqual(second['job']['attempts'], 1)
        self.assertEqual(second['job']['status'], 'succeeded')
        dispatched.assert_called_once()

    def test_identical_candidates_in_new_folder_do_not_import_twice(self):
        receipt = json.dumps({'fcpxml_sha256': {'landscape': 'a'*64, 'portrait': 'b'*64}})
        first = self.workspace / 'candidates'
        second = self.workspace / 'recreated'
        second.mkdir()
        for folder in (first, second):
            (folder / 'native-candidate-receipt.json').write_text(receipt)
        def dispatch(output, report, **kwargs):
            return {'status': 'apple_events_sent_timeline_unverified'}
        with mock.patch.object(launcher, 'candidate_folder', side_effect=[first, second]), \
             mock.patch.object(native, 'prepare', side_effect=self.prepare), \
             mock.patch.object(native, 'dispatch', side_effect=dispatch) as called:
            one = launcher.run(self.workspace, True)
            two = launcher.run(self.workspace, True)
        self.assertEqual(one['job_id'], two['job_id'])
        self.assertEqual(two['job']['attempts'], 1)
        called.assert_called_once()

    def test_status_does_not_initialize_or_dispatch(self):
        with mock.patch.object(native, 'dispatch') as called:
            result = launcher.status(self.workspace)
        self.assertEqual(result['status'], 'not_initialized')
        self.assertFalse((self.workspace / 'jane-native-worker-state').exists())
        called.assert_not_called()

    def test_status_includes_existing_manual_checkpoint(self):
        folder = self.workspace / 'fcp-jane-auto-20261022-183000'
        folder.mkdir()
        (folder / 'native-auto-import-receipt.json').write_text(json.dumps({
            'status': 'sending_landscape_apple_event', 'native_timeline_verified': False}))
        result = launcher.status(self.workspace)
        self.assertEqual(result['receipts'][0]['receipt']['status'], 'sending_landscape_apple_event')
        self.assertFalse(result['native_timeline_verified'])

    def test_existing_manual_attempt_prevents_new_queue_dispatch(self):
        folder = self.workspace / 'fcp-jane-auto-20261022-183000'
        folder.mkdir()
        (folder / 'native-auto-import-receipt.json').write_text(json.dumps({
            'status': 'ready_to_dispatch_not_launched'}))
        (self.workspace / 'candidates/native-candidate-receipt.json').write_text(
            json.dumps({'fcpxml_sha256': {'landscape': 'a'*64, 'portrait': 'b'*64}}))
        with mock.patch.object(launcher, 'candidate_folder', return_value=self.workspace / 'candidates'), \
             mock.patch.object(native, 'dispatch') as dispatch:
            with self.assertRaisesRegex(ValueError, 'earlier manual native import'):
                launcher.run(self.workspace, True)
            dispatch.assert_not_called()

    def test_discovery_skips_invalid_newer_directory(self):
        valid = self.workspace / 'fcp-native-import-20261022-100000'
        invalid = self.workspace / 'fcp-native-import-20261022-200000'
        valid.mkdir()
        invalid.mkdir()
        def validate(folder):
            if folder == invalid:
                raise ValueError('not a validated candidate')
        with mock.patch.object(native, 'candidates_from_receipt', side_effect=validate):
            self.assertEqual(launcher.candidate_folder(self.workspace), valid)


if __name__ == '__main__':
    unittest.main()
