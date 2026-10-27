import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import omniroute_circuit_recovery as recovery


class CircuitRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'state'
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)
        self.ids = []
        for n in range(3):
            job_id = str(uuid.uuid4())
            self.ids.append(job_id)
            self.conn.execute(
                "INSERT INTO jobs(id,kind,payload,dedupe_key,status,result,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (job_id, worker.OMNI_KIND, '{}', 'failed-' + str(n), 'needs_review',
                 json.dumps({'draft_status': 'needs_review_no_auto_retry',
                             'error_class': 'ContinuousAssignmentFailure'}), 100 + n, 100 + n))
            self.conn.execute(
                "INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)",
                (job_id, 'claimed', '{}', 100 + n))
        self.ids.reverse()

    def test_noninteractive_release_is_rejected(self):
        with mock.patch('sys.stdin.isatty', return_value=False), \
             mock.patch('ghost_omniroute_job.background_preflight') as preflight:
            with self.assertRaisesRegex(ValueError, 'interactive'):
                recovery.release(self.conn, self.state, now=200)
        preflight.assert_not_called()
        self.assertFalse(recovery.release_is_valid(self.conn, self.ids, now=200))

    def test_non_owner_cannot_release(self):
        with mock.patch('sys.stdin.isatty', return_value=True), \
             mock.patch.object(recovery.os, 'getuid', return_value=os.getuid() + 1):
            with self.assertRaisesRegex(ValueError, 'owner-private'):
                recovery.release(self.conn, self.state, now=200)

    def test_failed_authenticated_preflight_does_not_release(self):
        with mock.patch('sys.stdin.isatty', return_value=True), \
             mock.patch('ghost_omniroute_job.background_preflight',
                        side_effect=ValueError('preflight unavailable')):
            with self.assertRaisesRegex(ValueError, 'preflight unavailable'):
                recovery.release(self.conn, self.state, now=200)
        self.assertFalse(recovery.release_is_valid(self.conn, self.ids, now=200))

    def test_owner_release_records_audit_and_opens_only_current_circuit(self):
        ok = {'ok': True, 'read_only': True, 'free_routes_verified': True,
              'endpoint_key_available': True, 'loopback_auth_verified': True,
              'model_requests': 0}
        with mock.patch('sys.stdin.isatty', return_value=True), \
             mock.patch('ghost_omniroute_job.background_preflight', return_value=ok), \
             mock.patch('builtins.input', side_effect=[','.join(self.ids), 'RELEASE CIRCUIT']):
            receipt = recovery.release(self.conn, self.state, now=200)
        self.assertEqual(receipt['reviewed_job_ids'], self.ids)
        self.assertTrue(recovery.release_is_valid(self.conn, self.ids, now=201))
        self.assertFalse(recovery.release_is_valid(self.conn, self.ids[1:], now=201))
        (self.state / 'STOP').touch()
        self.assertFalse(recovery.release_is_valid(self.conn, self.ids, now=201))


if __name__ == '__main__':
    unittest.main()
