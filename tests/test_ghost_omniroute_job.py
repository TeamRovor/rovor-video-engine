"""Offline fail-closed OmniRoute-to-existing-ghost-queue regressions.

No external network, model credits, Keychain, Mac UI or system scheduler.
"""
from pathlib import Path
import json
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker
import ghost_worker_loop
import ghost_omniroute_job as omni


def catalog():
    return [
        {'name': route, 'strategy': 'priority', 'isHidden': False,
         'models': [{'kind': 'model', 'providerId': 'openrouter',
                     'model': name} for name in members]}
        for route, members in dict.fromkeys(omni.ROUTES.values())
    ]


class GhostOmniRouteJobTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.state = self.home / 'private-state'
        self.workspace = self.home / 'read-only-workspace'
        self.workspace.mkdir()
        self.conn = ghost_worker.connect(self.state)
        self.addCleanup(self.conn.close)

    def queue(self, packet='provider-efficiency', index=1):
        return ghost_worker.enqueue(self.conn, ghost_worker.OMNI_KIND,
                                    {'packet': packet}, 'omni-fixture-' + str(index))

    def test_reject_unknown_model_route_and_arbitrary_payload(self):
        for payload in ({}, {'packet':'untrusted'},
                        {'packet':'provider-efficiency','shell':'whoami'},
                        {'packet':'provider-efficiency','model':'paid/gpt'}):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    ghost_worker.enqueue(self.conn, ghost_worker.OMNI_KIND,
                                         payload, 'invalid')
        self.assertEqual(self.conn.execute(
            'SELECT COUNT(*) FROM jobs').fetchone()[0], 0)

    def test_without_separate_approval_job_remains_queued(self):
        jid = self.queue()
        self.assertIsNone(ghost_worker.run_once(
            self.conn, self.workspace, owner='worker',
            allow_model_use=True))
        row = self.conn.execute(
            'SELECT status, attempts FROM jobs WHERE id=?', (jid,)).fetchone()
        self.assertEqual((row['status'], row['attempts']), ('queued', 0))

    def test_route_catalog_rejects_paid_or_changed_fallback(self):
        c = catalog()
        self.assertEqual(omni.verify_route('provider-efficiency', c),
                         'rovor-reason-free-v1')
        c[2]['models'][0]['model']='openrouter/nvidia/paid-model'
        with self.assertRaisesRegex(ValueError, 'Non-free'):
            omni.verify_route('provider-efficiency', c)
        c = catalog()
        c[2]['models'].reverse()
        with self.assertRaisesRegex(ValueError, 'order changed'):
            omni.verify_route('provider-efficiency', c)
        c = catalog()
        c[2]['models'].append({'kind':'model','providerId':'openrouter',
                               'model':'openrouter/paid:free'})
        with self.assertRaisesRegex(ValueError, 'models changed'):
            omni.verify_route('provider-efficiency', c)

    def test_model_job_requires_review_not_success_and_does_not_replay(self):
        jid = self.queue()
        calls=[]
        worker_module = types.ModuleType('omniroute_workpack_runner')
        worker_module.access_key = lambda: 'private-key-for-test'
        def model_call(repo, out, packet, route, key):
            calls.append((packet, route, key, str(out)))
            return {'status':'draft_completed_needs_review'}
        worker_module.run_packet = model_call
        review_module = types.ModuleType('omniroute_draft_review')
        review_module.inspect = lambda repo,out,packet: {
            'status':'content_quality_needs_review', 'approval_granted':False}
        with mock.patch.object(omni, 'read_combo_catalog', return_value=catalog()):
            with mock.patch.dict(sys.modules, {
                'omniroute_workpack_runner':worker_module,
                'omniroute_draft_review':review_module,
            }):
                result = ghost_worker.run_once(
                    self.conn, self.workspace, owner='worker',
                    allow_omniroute_model_use=True)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['result']['review_status'], 'content_quality_needs_review')
        self.assertFalse(result['result']['facts_verified'])
        self.assertFalse(result['result']['mac_app_control_verified'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:3], ('provider-efficiency',
                          'rovor-reason-free-v1','private-key-for-test'))
        self.assertIsNone(ghost_worker.run_once(
            self.conn, self.workspace, owner='worker',
            allow_omniroute_model_use=True))
        self.assertEqual(len(calls), 1)
        row=self.conn.execute('SELECT status,attempts,result FROM jobs WHERE id=?',
                              (jid,)).fetchone()
        self.assertEqual((row['status'],row['attempts']),('needs_review',1))
        self.assertNotIn('private-key-for-test',row['result'])

    def test_five_per_rolling_day_are_claimed_atomically(self):
        for i in range(1,7):
            self.queue(index=i)
        for i in range(5):
            claimed=ghost_worker.claim(self.conn,'w',allow_omniroute_model_use=True)
            self.assertEqual(claimed['kind'],ghost_worker.OMNI_KIND)
            self.conn.execute('UPDATE jobs SET status=\'needs_review\',lease_owner=NULL WHERE id=?',
                              (claimed['id'],))
        self.assertIsNone(ghost_worker.claim(
            self.conn,'w',allow_omniroute_model_use=True))
        queued=self.conn.execute("SELECT COUNT(*) FROM jobs WHERE status='queued'").fetchone()[0]
        self.assertEqual(queued,1)

    def test_stop_blocks_claim_and_no_model_call(self):
        jid=self.queue()
        (self.state/'STOP').write_text('stop')
        self.assertIsNone(ghost_worker.run_once(
            self.conn, self.workspace, allow_omniroute_model_use=True))
        self.assertEqual(self.conn.execute(
            'SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()[0], 'queued')

    def test_provider_failure_needs_review_without_raw_exception_leak(self):
        jid=self.queue()
        failing=types.ModuleType('omniroute_workpack_runner')
        failing.access_key=lambda: 'fixture-secret'
        def fail(*args):
            raise RuntimeError('SECRET PROVIDER RESPONSE SHOULD BE PRIVATE')
        failing.run_packet=fail
        reviewer=types.ModuleType('omniroute_draft_review')
        reviewer.inspect=lambda *args: {'status':'draft_ready_for_human_review'}
        with mock.patch.object(omni,'read_combo_catalog',return_value=catalog()):
            with mock.patch.dict(sys.modules,{'omniroute_workpack_runner':failing,
                                              'omniroute_draft_review':reviewer}):
                outcome=ghost_worker.run_once(self.conn,self.workspace,
                       allow_omniroute_model_use=True)
        self.assertEqual(outcome['status'],'needs_review')
        self.assertNotIn('SECRET',json.dumps(outcome))
        self.assertEqual(self.conn.execute(
            'SELECT attempts FROM jobs WHERE id=?',(jid,)).fetchone()[0],1)
        self.assertIsNone(ghost_worker.claim(self.conn,'worker',
                          allow_omniroute_model_use=True))

    def test_loop_default_never_claims_omni(self):
        jid=self.queue()
        # One bounded poll; no sleeping or external operation.
        result=ghost_worker_loop.poll(self.conn,self.workspace,self.state,
            worker_id='test',max_jobs=1,max_seconds=0.01,
            poll_seconds=0.1,monotonic=iter((1.0,1.1,1.2)).__next__,
            sleeper=lambda *_:None)
        self.assertEqual(result['executed'],0)
        self.assertEqual(self.conn.execute(
            'SELECT status FROM jobs WHERE id=?',(jid,)).fetchone()[0],'queued')
        self.assertFalse(result['omniroute_model_use_enabled'])


if __name__ == '__main__':
    unittest.main()
