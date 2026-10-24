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
import fcp_jane_native_probe as probe


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

    def test_opt_in_records_review_without_legacy_dispatch_or_replay(self):
        job = self.submit()
        self.assertEqual(job, self.submit())
        with mock.patch.object(native, 'prepare', side_effect=self.prepare) as prepared, \
             mock.patch.object(native, 'dispatch', side_effect=self.dispatch) as dispatched:
            result = worker.run_once(self.conn, self.workspace, allow_native_import=True)
            self.assertEqual(result['status'], 'needs_review')
            self.assertIn('disabled', result['error'])
            self.assertIsNone(worker.run_once(self.conn, self.workspace, allow_native_import=True))
            prepared.assert_not_called()
            dispatched.assert_not_called()
        self.assertEqual(tuple(self.row(job)), ('needs_review', 1))

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

    def test_disabled_native_job_does_not_prevent_read_only_work(self):
        self.submit()
        ping = worker.enqueue(self.conn, 'system.ping', {}, 'next-ping')
        with mock.patch.object(native, 'dispatch') as dispatch:
            results = [worker.run_once(self.conn, self.workspace, allow_native_import=True)
                       for _ in range(2)]
        self.assertEqual([r['status'] for r in results], ['needs_review', 'succeeded'])
        self.assertEqual(results[1]['id'], ping)
        dispatch.assert_not_called()
        self.assertEqual(list(self.workspace.glob('native-import-*')), [])

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
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['succeeded'], 0)
        self.assertFalse(result['native_import_enabled'])
        self.assertTrue(result['native_import_requested'])
        self.assertTrue(result['read_only'])
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
        self.assertFalse(result['native_import_enabled'])
        self.assertIn('disabled', result['native_import_disabled_reason'])
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
        self.assertEqual(second['job']['status'], 'needs_review')
        dispatched.assert_not_called()

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
        called.assert_not_called()

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

    def test_diagnosis_reuses_existing_probe_without_native_dispatch(self):
        job = self.workspace / 'fcp-jane-auto-20261022-183007'
        with mock.patch.object(launcher.sys, 'platform', 'darwin'), \
             mock.patch.object(launcher, 'status', return_value={'jobs': [], 'receipts': [
                 {'path': str(job / 'native-auto-import-receipt.json'), 'receipt': {}}]}), \
             mock.patch.object(probe, 'inspect', return_value={'native_timeline_verified': False}) as inspect, \
             mock.patch.object(native, 'dispatch') as dispatch:
            result = launcher.diagnose(self.workspace)
        inspect.assert_called_once_with(self.workspace, job)
        dispatch.assert_not_called()
        self.assertFalse(result['native_timeline_verified'])

    def test_diagnosis_does_not_infer_native_state_on_linux(self):
        with mock.patch.object(launcher.sys, 'platform', 'linux'), \
             mock.patch.object(probe, 'inspect') as inspect:
            with self.assertRaisesRegex(ValueError, 'must run on the Mac'):
                launcher.diagnose(self.workspace)
            inspect.assert_not_called()

    def queued_attempt(self, with_receipt=True):
        state = self.workspace / 'jane-native-worker-state'
        with worker.connect(state) as conn:
            job_id = worker.enqueue(conn, worker.NATIVE_KIND,
                                    {'candidates': 'candidates'}, 'diagnostic')
        folder = self.workspace / ('native-import-' + job_id)
        if with_receipt:
            folder.mkdir()
            (folder / 'native-auto-import-receipt.json').write_text(json.dumps({
                'status': 'native_library_not_observed',
                'target_library': str(folder / 'ROVOR-Jane-Test.fcpbundle'),
                'apple_event_sent': True, 'last_dispatched': 'landscape'}))
        return folder

    def test_diagnosis_finds_queue_attempt_without_manual_directory(self):
        folder = self.queued_attempt()
        before = launcher.status(self.workspace)
        with mock.patch.object(launcher.sys, 'platform', 'darwin'), \
             mock.patch.object(worker, 'connect', side_effect=AssertionError('must not initialize queue')), \
             mock.patch.object(native, 'dispatch') as dispatch:
            result = launcher.diagnose(self.workspace)
        self.assertEqual(result['job_dir'], str(folder))
        self.assertEqual(result['original_job_status'], 'native_library_not_observed')
        self.assertFalse(result['native_timeline_verified'])
        dispatch.assert_not_called()
        self.assertEqual(before, launcher.status(self.workspace))

    def test_corrupt_queue_id_cannot_escape_workspace(self):
        state = self.workspace / 'jane-native-worker-state'
        with worker.connect(state) as conn:
            job = worker.enqueue(conn, worker.NATIVE_KIND, {'candidates': 'candidates'}, 'bad-id')
            conn.execute('UPDATE jobs SET id=? WHERE id=?', ('../../outside', job))
        with self.assertRaises(ValueError):
            launcher.status(self.workspace)

    def test_symlinked_queue_evidence_is_reported_without_following(self):
        folder = self.queued_attempt()
        receipt = folder / 'native-auto-import-receipt.json'
        receipt.unlink()
        outside = self.root / 'private-receipt.json'
        outside.write_text('{"private": "must not read"}')
        receipt.symlink_to(outside)
        with mock.patch.object(launcher.sys, 'platform', 'darwin'):
            result = launcher.diagnose(self.workspace)
        self.assertEqual(result['status'], 'invalid_native_evidence')
        self.assertNotIn('must not read', json.dumps(result))

    def test_undispatched_queue_attempt_does_not_look_like_missing_job(self):
        folder = self.queued_attempt(with_receipt=False)
        with mock.patch.object(launcher.sys, 'platform', 'darwin'), \
             mock.patch.object(native, 'dispatch') as dispatch:
            result = launcher.diagnose(self.workspace)
        self.assertEqual(result['job_dir'], str(folder))
        self.assertEqual(result['status'], 'no_native_receipt_recorded')
        self.assertEqual(result['queue_status'], 'queued')
        self.assertFalse(folder.exists())
        dispatch.assert_not_called()

    def test_diagnosis_keeps_both_queue_and_manual_evidence(self):
        self.queued_attempt()
        folder = self.workspace / 'fcp-jane-auto-20261022-183007'
        folder.mkdir()
        (folder / 'native-auto-import-receipt.json').write_text(json.dumps({
            'status': 'native_library_not_observed',
            'target_library': str(folder / 'ROVOR-Jane-Test.fcpbundle')}))
        with mock.patch.object(launcher.sys, 'platform', 'darwin'):
            result = launcher.diagnose(self.workspace)
        self.assertEqual(len(result['attempts']), 2)
        self.assertEqual({a['source'] for a in result['attempts']}, {'queue', 'manual'})
        self.assertFalse(result['native_timeline_verified'])

    def test_diagnosis_preserves_corrupt_receipt_as_evidence_error(self):
        folder = self.queued_attempt()
        (folder / 'native-auto-import-receipt.json').write_text('{broken')
        with mock.patch.object(launcher.sys, 'platform', 'darwin'):
            result = launcher.diagnose(self.workspace)
        self.assertEqual(result['status'], 'invalid_native_evidence')
        self.assertEqual(result['job_dir'], str(folder))
        self.assertFalse(result['native_timeline_verified'])

    def test_diagnosis_empty_root_does_not_initialize_queue(self):
        with mock.patch.object(launcher.sys, 'platform', 'darwin'), \
             mock.patch.object(native, 'dispatch') as dispatch:
            result = launcher.diagnose(self.workspace)
        self.assertEqual(result['status'], 'no_native_attempt_recorded')
        self.assertFalse((self.workspace / 'jane-native-worker-state').exists())
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
