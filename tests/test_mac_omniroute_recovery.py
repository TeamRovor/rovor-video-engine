import json
from pathlib import Path
import sqlite3
import plistlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import mac_omniroute_recovery as recovery
import ghost_worker as worker
import omniroute_dispatch_pacing as pacing


class RecoveryAuditTests(unittest.TestCase):
    def test_account_attribution_drift_and_no_secret_or_quota_invention(self):
        conn = sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row
        conn.executescript('''
            CREATE TABLE provider_connections(id,provider,is_active,test_status,last_tested,api_key,access_token);
            CREATE TABLE combos(data);
            CREATE TABLE usage_history(provider,connection_id,model,success,tokens_input,tokens_output,timestamp);
        ''')
        for account in ('a', 'b'):
            conn.execute('INSERT INTO provider_connections VALUES(?,?,?,?,?,?,?)',
                (account, 'groq', 1, 'active', '2026-10-26T00:00:00Z', 'DO_NOT_DISCLOSE', None))
        conn.execute('INSERT INTO usage_history VALUES(?,?,?,?,?,?,?)',
            ('groq', 'a', 'openai/gpt-oss-20b', 1, 3, 7, '2026-10-26T00:00:00Z'))
        conn.execute('INSERT INTO usage_history VALUES(?,?,?,?,?,?,?)',
            ('groq', None, 'unattributed', 1, 30, 70, '2026-10-26T00:00:00Z'))
        conn.execute('INSERT INTO combos VALUES(?)', (json.dumps({
            'name': 'rovor-fast-free-v1', 'strategy': 'priority', 'isHidden': False,
            'models': [{'kind': 'model', 'providerId': 'groq', 'model': 'groq/openai/gpt-oss-20b',
                        'connectionId': 'b'}]}),))
        providers, checks = recovery.provider_evidence(conn, 1793065000)
        self.assertEqual(len(providers), 9)
        groq = next(p for p in providers if p['provider'] == 'groq')
        self.assertEqual(groq['configured_accounts'], 2)
        a, b = groq['accounts']
        self.assertEqual(a['recorded_usage'][0]['output_tokens'], 7)
        self.assertEqual(a['recorded_usage'][0]['success_freshness'], 'stale')
        self.assertEqual(a['routes'], [])
        self.assertEqual(b['recorded_usage'], [])
        self.assertEqual(b['routes'][0]['account_binding'], 'explicit')
        self.assertTrue(all(c['status'] == 'route_drift_requires_review' for c in checks))
        for slot in (a, b):
            self.assertFalse(slot['dispatch_eligible'])
            self.assertEqual(slot['inference_verified_now'], 'not_verified')
            self.assertIsNone(slot['quota']['used_percent'])
        self.assertNotIn('DO_NOT_DISCLOSE', json.dumps(providers))
        self.assertNotIn('unattributed', json.dumps(providers))

    def test_database_copy_reads_committed_wal_without_touching_source(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / 'storage.sqlite'
            conn = sqlite3.connect(p)
            self.addCleanup(conn.close)
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('CREATE TABLE evidence(value)')
            conn.execute("INSERT INTO evidence VALUES('committed-wal')")
            conn.commit()
            before = {q.name: q.read_bytes() for q in Path(folder).iterdir()}
            with recovery.database_copy(p) as copied:
                self.assertEqual(copied.execute('SELECT value FROM evidence').fetchone()[0], 'committed-wal')
                with self.assertRaises(sqlite3.OperationalError):
                    copied.execute("INSERT INTO evidence VALUES('forbidden')")
            self.assertEqual(before, {q.name: q.read_bytes() for q in Path(folder).iterdir()})
            conn.close()

    def test_audit_redacts_real_private_job_ids_from_serialized_report(self):
        # Recreate an actual worker DB and installed policy without any model
        # call, service change, credential lookup or public receipt.
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder).resolve()
            state = home / 'private-worker-state'
            marker = 'private-sentinel-id-never-publish-123'
            conn = worker.connect(state)
            try:
                conn.execute(
                    'INSERT INTO jobs(id,kind,payload,dedupe_key,status,result,created_at,updated_at) '
                    'VALUES(?,?,?,?,?,?,?,?)',
                    (marker, worker.OMNI_KIND, '{}', 'sentinel-test',
                     'needs_review',
                     json.dumps({'draft_status': 'needs_review_no_auto_retry'}),
                     900, 900))
                conn.execute(
                    'INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)',
                    (marker, 'claimed', '{}', 900))
            finally:
                conn.close()
            agent = home / 'Library' / 'LaunchAgents'
            agent.mkdir(parents=True)
            (agent / (pacing.LABEL + '.plist')).write_bytes(plistlib.dumps({
                'Label': pacing.LABEL,
                'ProgramArguments': [
                    '/pinned/python', '/safe/omniroute_continuous.py',
                    '--state', str(state), '--workspace', str(home),
                    '--max-claims-per-day', '50',
                    '--min-interval-seconds', '1730']
            }))
            with mock.patch.object(recovery, 'service_evidence', return_value=[]):
                report = recovery.audit(home=home, now=1000)
            self.assertEqual(report['last_three_claims'], [
                {'status': 'needs_review',
                 'draft_status': 'needs_review_no_auto_retry'}])
            self.assertNotIn(marker, json.dumps(report, sort_keys=True))
            self.assertEqual(report['model_requests'], 0)
            self.assertFalse(report['installed_state_modified'])

    def test_offset_and_future_observations_are_not_retimestamped(self):
        utc = recovery.timestamp('2026-10-26T00:00:00Z')
        self.assertEqual(utc, recovery.timestamp('2026-10-25T19:00:00-05:00'))
        self.assertEqual(recovery.freshness(utc + 1000, utc), 'unknown')
        self.assertEqual(recovery.freshness(None, utc), 'unknown')
        self.assertEqual(recovery.freshness(utc - 901, utc), 'stale')


if __name__ == '__main__':
    unittest.main()
