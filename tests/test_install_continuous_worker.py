from pathlib import Path
import plistlib
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import install_continuous_worker as installer


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state'
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)
        self.plist = self.root / 'worker.plist'
        self.original = {'Label': installer.LABEL, 'UnrelatedSetting': 'preserved',
            'ProgramArguments': ['/pinned/python', '/old/tools/ghost_worker_loop.py',
                                 '--state', str(self.state), '--workspace', '/workspace', 'run']}
        self.blob = plistlib.dumps(self.original)
        self.plist.write_bytes(self.blob)
        self.proposed, _ = installer.build_config(self.original, self.root / 'candidate')
        self.calls = []

    def fake(self, command, **kw):
        self.calls.append(command)
        return SimpleNamespace(returncode=0)

    def test_config_reuses_only_existing_label_state_and_interpreter(self):
        self.assertEqual(self.proposed['Label'], installer.LABEL)
        self.assertEqual(self.proposed['UnrelatedSetting'], 'preserved')
        self.assertEqual(self.proposed['ProgramArguments'][0], '/pinned/python')
        self.assertIn(str(self.state), self.proposed['ProgramArguments'])
        self.assertEqual(self.proposed['StartInterval'], 301)
        self.assertFalse(self.proposed['KeepAlive'])

    def test_301_tick_aligns_with_601_pace_without_extra_daily_claims(self):
        import omniroute_dispatch_pacing as pacing
        proposed = self.proposed
        self.assertEqual(proposed['StartInterval'], 301)
        self.assertIn('--min-interval-seconds', proposed['ProgramArguments'])
        self.assertEqual(proposed['ProgramArguments'][
            proposed['ProgramArguments'].index('--min-interval-seconds')+1], '601')

        # Old 300-second cadence missed the 601-second gate at 10 minutes.
        self.assertFalse(pacing.dispatch_decision(
            now=600,claims=[0],max_claims=144,queued=1,
            pace_seconds=601)['allowed'])
        # New second subsequent tick lands after 601 seconds, not at 900.
        self.assertTrue(pacing.dispatch_decision(
            now=602,claims=[0],max_claims=144,queued=1,
            pace_seconds=601)['allowed'])

        # In a full rolling day no claim bypasses the exact daily cap.
        claims = []
        for now in range(0, 86401, proposed['StartInterval']):
            if pacing.dispatch_decision(
                    now=now,claims=claims,max_claims=144,queued=1,
                    pace_seconds=601)['allowed']:
                claims.append(now)
        self.assertEqual(claims[:4],[0,602,1204,1806])
        self.assertLessEqual(len(claims),144)
        self.assertTrue(all(claims[n]-claims[n-1] >= 601
                            for n in range(1,len(claims))))

    def test_success_activates_one_label_and_clears_only_its_own_stop(self):
        result = installer.activate(self.plist, self.proposed, self.state, run=self.fake, uid=123)
        self.assertEqual(result['status'], 'same_service_activated_receipt_pending')
        self.assertFalse((self.state / 'STOP').exists())
        self.assertEqual(plistlib.loads(self.plist.read_bytes()), self.proposed)
        self.assertEqual(sum(c[1] == 'bootstrap' for c in self.calls), 1)
        self.assertTrue(all('gui/123/' + installer.LABEL in c
                            for c in self.calls if c[1] in ('print', 'bootout', 'kickstart')))

    def test_failed_new_bootstrap_restores_old_service_and_preserves_stop(self):
        count = 0
        def fail_once(command, **kw):
            nonlocal count
            self.calls.append(command)
            if command[1] == 'bootstrap':
                count += 1
                return SimpleNamespace(returncode=int(count == 1))
            return SimpleNamespace(returncode=0)
        with self.assertRaises(ValueError):
            installer.activate(self.plist, self.proposed, self.state, run=fail_once, uid=123)
        self.assertEqual(self.plist.read_bytes(), self.blob)
        self.assertTrue((self.state / 'STOP').exists())
        self.assertEqual(count, 2)

    def test_existing_stop_is_never_cleared(self):
        (self.state / 'STOP').write_text('owner pause')
        with self.assertRaises(ValueError):
            installer.activate(self.plist, self.proposed, self.state, run=self.fake)
        self.assertEqual((self.state / 'STOP').read_text(), 'owner pause')
        self.assertEqual(self.calls, [])

    def test_running_job_blocks_before_service_changes(self):
        job = worker.enqueue(self.conn, 'system.ping', {}, 'running', now=1)
        worker.claim(self.conn, 'active', now=2)
        with self.assertRaises(ValueError):
            installer.activate(self.plist, self.proposed, self.state, run=self.fake)
        self.assertEqual(self.plist.read_bytes(), self.blob)
        self.assertEqual(self.calls, [])

    def test_kickstart_failure_does_not_kill_newly_started_service(self):
        def kickstart_busy(command, **kw):
            self.calls.append(command)
            return SimpleNamespace(returncode=int(command[1] == 'kickstart'))
        result = installer.activate(self.plist, self.proposed, self.state,
                                    run=kickstart_busy, uid=123)
        self.assertFalse(result['first_tick_requested'])
        self.assertFalse((self.state / 'STOP').exists())
        self.assertEqual(sum(c[1] == 'bootout' for c in self.calls), 1)


if __name__ == '__main__':
    unittest.main()
