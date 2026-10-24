"""Offline end-to-end composition of the existing SQLite ghost queue and OmniRoute.

Uses the real PR #41 ghost queue, PR #51 workpack loader and receipt reviewer.
Every inference/key/catalog call is mocked: no billing, native Mac work, network,
shell execution, auto-replay or external state changes.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))

import ghost_worker
import ghost_worker_loop
import ghost_omniroute_job as omni
import omniroute_workpack_runner as workpack
import omniroute_draft_review as reviewer


def fixed_catalog():
    return [
        {'name': name,'strategy':'priority','isHidden':False,
         'models':[{'kind':'model','providerId':'openrouter','model':m}
                   for m in models]}
        for name,models in dict.fromkeys(omni.ROUTES.values())
    ]


class CompositeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # macOS temporary paths may traverse /var -> /private/var.
        self.home=Path(tmp.name).resolve()
        self.state=self.home/'private-state'
        self.workspace=self.home/'workspace'
        self.workspace.mkdir()
        self.conn=ghost_worker.connect(self.state)
        self.addCleanup(self.conn.close)

    def enqueue(self,packet='provider-efficiency',suffix='one'):
        return ghost_worker.enqueue(self.conn,ghost_worker.OMNI_KIND,
                                    {'packet':packet},'composite-'+suffix)

    def test_canonical_fixture_still_rejects_redirected_receipt_parent(self):
        self.assertEqual(self.home,self.home.resolve())
        alias=self.home/'redirected-state'
        alias.symlink_to(self.state,target_is_directory=True)
        with self.assertRaises(ValueError):
            workpack.safe_private_root(alias/'receipts')
        self.assertFalse((self.state/'receipts').exists())

    def test_both_composed_modules_are_importable_and_public_inputs_parse(self):
        for slug in ('provider-efficiency','supervisor-resilience'):
            packet,prompt,provenance=workpack.load_packet(ROOT,slug)
            self.assertEqual(packet['slug'],slug)
            self.assertTrue(prompt)
            self.assertTrue(provenance['sources'])
            self.assertFalse(packet['external_effects_allowed'])

    def test_direct_api_rejects_external_private_symlinks_before_inference(self):
        target=self.home/'external-private'
        target.mkdir(mode=0o700)
        alias=self.home/'private-alias'
        alias.symlink_to(target,target_is_directory=True)
        for destination in (alias,alias/'receipts'):
            with self.subTest(destination=destination):
                with mock.patch.object(workpack,'http_completion') as completion:
                    with self.assertRaises(ValueError):
                        workpack.run_packet(ROOT,destination,'provider-efficiency',
                                            'rovor-reason-free-v1','fixture-key')
                    completion.assert_not_called()
        self.assertEqual(list(target.iterdir()),[])

    def test_one_queued_job_writes_private_reviewed_receipt_with_real_modules(self):
        jid=self.enqueue()
        calls=[]
        def local_inference(model,prompt,key):
            calls.append((model,prompt,key))
            self.assertIn('OmniRoute',prompt)
            return ('## Research observations\nPublic-source evidence only; no Mac control.',
                    {'prompt_tokens':100,'completion_tokens':65,'total_tokens':165})
        with mock.patch.object(omni,'read_combo_catalog',return_value=fixed_catalog()):
            with mock.patch.object(workpack,'access_key',return_value='mock-private-key'):
                with mock.patch.object(workpack,'http_completion',side_effect=local_inference):
                    result=ghost_worker.run_once(self.conn,self.workspace,
                         owner='composite-test',allow_omniroute_model_use=True)
        self.assertEqual(result['status'],'needs_review')
        self.assertEqual(result['result']['draft_status'],'draft_completed_needs_review')
        self.assertEqual(result['result']['review_status'],'draft_ready_for_human_review')
        self.assertFalse(result['result']['facts_verified'])
        self.assertFalse(result['result']['mac_app_control_verified'])
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][0],'rovor-reason-free-v1')
        self.assertEqual(calls[0][2],'mock-private-key')
        receipt=self.state/'omniroute-drafts'/jid/'provider-efficiency.receipt.json'
        self.assertTrue(receipt.is_file())
        self.assertNotIn('mock-private-key',receipt.read_text())
        saved=json.loads(receipt.read_text())
        self.assertEqual(saved['usage_reported']['completion_tokens'],65)
        assessed=reviewer.inspect(ROOT,receipt.parent,'provider-efficiency')
        self.assertEqual(assessed['status'],'draft_ready_for_human_review')
        self.assertFalse(assessed['approval_granted'])
        stored=self.conn.execute('SELECT status,attempts,result FROM jobs WHERE id=?',
                                (jid,)).fetchone()
        self.assertEqual((stored['status'],stored['attempts']),('needs_review',1))
        self.assertNotIn('mock-private-key',stored['result'])
        self.assertNotIn('Research observations',stored['result'])
        self.assertIsNone(ghost_worker.run_once(self.conn,self.workspace,
                            allow_omniroute_model_use=True))
        self.assertEqual(len(calls),1)

    def test_composed_review_gate_rejects_probable_cutoff_and_old_date(self):
        jid=self.enqueue()
        def near_cap(model,prompt,key):
            return ('**Date:** 2025-01-15 (analysis date)\n'
                    'A proposed architecture requires human review.',
                    {'prompt_tokens':100,'completion_tokens':2400,'total_tokens':2500})
        with mock.patch.object(omni,'read_combo_catalog',return_value=fixed_catalog()):
            with mock.patch.object(workpack,'access_key',return_value='fake-key'):
                with mock.patch.object(workpack,'http_completion',side_effect=near_cap):
                    result=ghost_worker.run_once(self.conn,self.workspace,
                        allow_omniroute_model_use=True)
        self.assertEqual(result['status'],'needs_review')
        self.assertEqual(result['result']['review_status'],'content_quality_needs_review')
        receipt=self.state/'omniroute-drafts'/jid/'provider-efficiency.receipt.json'
        findings=reviewer.inspect(ROOT,receipt.parent,'provider-efficiency')
        self.assertIn('report_header_year_mismatch',findings['reasons'])
        self.assertIn('near_completion_token_cap_truncation_unknown',findings['reasons'])

    def test_known_missing_runner_workflow_never_spends_or_requeues(self):
        # Removed public self-hosted Actions proof workflow MUST NOT be recreated
        # just to satisfy a stale workpack manifest.
        missing=ROOT/'.github/workflows/rovor-mac-exec-proof.yml'
        if missing.exists():
            self.skipTest('Workflow source restored; do not infer missing prerequisite')
        jid=self.enqueue('runner-blocker')
        with mock.patch.object(omni,'read_combo_catalog',return_value=fixed_catalog()):
            with mock.patch.object(workpack,'access_key',return_value='fake-key'):
                with mock.patch.object(workpack,'http_completion') as call:
                    result=ghost_worker.run_once(self.conn,self.workspace,
                        allow_omniroute_model_use=True)
                    call.assert_not_called()
        self.assertEqual(result['status'],'needs_review')
        self.assertNotIn('fake-key',json.dumps(result))
        self.assertEqual(self.conn.execute(
            'SELECT attempts FROM jobs WHERE id=?',(jid,)).fetchone()[0],1)
        self.assertIsNone(ghost_worker.claim(self.conn,'worker',
                         allow_omniroute_model_use=True))

    def test_separate_approval_and_stop_leave_job_unclaimed(self):
        jid=self.enqueue('supervisor-resilience')
        self.assertIsNone(ghost_worker.run_once(self.conn,self.workspace,
                         allow_model_use=True))
        (self.state/'STOP').write_text('stop')
        self.assertIsNone(ghost_worker.run_once(self.conn,self.workspace,
                         allow_omniroute_model_use=True))
        state=self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?',
                                (jid,)).fetchone()
        self.assertEqual((state['status'],state['attempts']),('queued',0))


if __name__=='__main__':
    unittest.main()
