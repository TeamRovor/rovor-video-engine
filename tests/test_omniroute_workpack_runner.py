"""Offline stdlib tests for OmniRoute draft-only local agent workpacks."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import omniroute_workpack_runner as worker

REAL_ROOT=Path(__file__).resolve().parents[1]


class OmniRouteWorkpackTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name)
        self.repo=self.base/'rovor-public'
        self.repo.mkdir()
        self.out=self.base/'private-receipts'
        (self.repo/'WORK.md').write_text('# test repo')
        for slug in worker.PACKETS:
            raw=json.loads((REAL_ROOT/'coordination'/'omniroute-workpacks'/
                            (slug+'.json')).read_text())
            to=self.repo/'coordination'/'omniroute-workpacks'/(slug+'.json')
            to.parent.mkdir(parents=True,exist_ok=True)
            to.write_text(json.dumps(raw))
            for rel in raw['inputs']:
                file=self.repo/rel
                file.parent.mkdir(parents=True,exist_ok=True)
                if not file.exists():
                    file.write_text('Public ROVOR fixture for '+rel)

    def test_curated_packets_load_and_stay_narrow(self):
        for slug in worker.PACKETS:
            packet,prompt,provenance=worker.load_packet(self.repo,slug)
            self.assertFalse(packet['external_effects_allowed'])
            self.assertFalse(packet['mac_gui_required'])
            self.assertIn(packet['task'],prompt)
            self.assertTrue(provenance['sources'])
            self.assertLess(len(prompt),38001)

    def test_default_cli_does_not_create_files_or_call_models(self):
        output=io.StringIO()
        with mock.patch.object(worker,'http_completion') as call:
            with redirect_stdout(output):
                rc=worker.main(['--repo',str(self.repo),'--all',
                                '--out',str(self.out)])
        self.assertEqual(rc,0)
        self.assertEqual(json.loads(output.getvalue())['status'],
                         'dry_run_no_model_calls')
        self.assertFalse(self.out.exists())
        call.assert_not_called()

    def test_no_approval_without_explicit_no_fallback_assurance(self):
        output=io.StringIO()
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'non-secret'}):
            with redirect_stderr(output):
                rc=worker.main(['--repo',str(self.repo),
                    '--packet','runner-blocker','--approve-model-use',
                    '--model','some/verified-route','--out',str(self.out)])
        self.assertEqual(rc,2)
        self.assertFalse(self.out.exists())
        self.assertNotIn('non-secret',output.getvalue())

    def test_complete_private_receipt_once_no_replay(self):
        called=[]
        def completion(model,prompt,key):
            called.append((model,prompt,key))
            return ('Unverified assumptions; collect Mac runner status',{'total_tokens':56})
        first=worker.run_packet(self.repo,self.out,'runner-blocker',
                                'groq/openai/gpt-oss-120b','private-key',
                                completion=completion)
        second=worker.run_packet(self.repo,self.out,'runner-blocker',
                                 'groq/openai/gpt-oss-120b','private-key',
                                 completion=lambda *a:self.fail('replayed'))
        self.assertEqual(first['status'],'draft_completed_needs_review')
        self.assertEqual(second['status'],'previous_attempt_not_replayed')
        self.assertEqual(len(called),1)
        report=json.loads(Path(first['receipt']).read_text())
        self.assertEqual(report['answer'],
                         'Unverified assumptions; collect Mac runner status')
        self.assertTrue(report['user_review_required'])
        self.assertFalse(report['source_edits'])
        self.assertFalse(report['mac_control_verified'])
        self.assertNotIn('private-key',Path(first['receipt']).read_text())

    def test_completion_failure_is_not_retried_or_exposed(self):
        def failure(*a):
            raise RuntimeError('Secret provider token 234')
        result=worker.run_packet(self.repo,self.out,'provider-efficiency',
                                 'explicit-route','key',completion=failure)
        saved=Path(result['receipt']).read_text()
        self.assertEqual(result['status'],'needs_review_no_auto_retry')
        self.assertNotIn('Secret provider token',saved)
        self.assertEqual(worker.run_packet(self.repo,self.out,
            'provider-efficiency','explicit-route','key',
            completion=lambda *_:self.fail('retry'))['status'],
            'previous_attempt_not_replayed')

    def test_incomplete_reserved_receipt_prevents_rerun(self):
        self.out.mkdir()
        (self.out/'runner-blocker.receipt.json').write_text('{"status":"reserved_no_retry"}')
        result=worker.run_packet(self.repo,self.out,'runner-blocker',
                                 'explicit-route','key',
                                 completion=lambda *_:self.fail('replayed'))
        self.assertEqual(result['status'],'previous_attempt_not_replayed')

    def test_refuse_symlinked_private_receipts_root(self):
        self.out.symlink_to(self.repo,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'redirected'):
            worker.run_packet(self.repo,self.out,'runner-blocker',
                              'model','key',completion=lambda *_:('ok',None))

    def test_refuse_public_source_escape_or_symlink(self):
        for p in ('../private', '/etc/passwd', '.env', 'folder//secret',
                  'secret/../../passwd',r'X:\Users\file'):
            with self.subTest(path=p):
                with self.assertRaises(ValueError):
                    worker.read_public_file(self.repo,p,300)
        public=self.repo/'WORK.md'
        public.unlink()
        public.symlink_to(self.base/'something-private')
        with self.assertRaises(ValueError):
            worker.read_public_file(self.repo,'WORK.md',300)

    def test_manifest_injection_cannot_change_permissions(self):
        f=self.repo/'coordination'/'omniroute-workpacks'/'runner-blocker.json'
        packet=json.loads(f.read_text())
        packet['external_effects_allowed']=True
        f.write_text(json.dumps(packet))
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            worker.load_packet(self.repo,'runner-blocker')

    def test_combined_input_limit_refuses_silent_truncation(self):
        f=self.repo/'coordination'/'hosted-runner-diagnosis.md'
        f.write_text('A'*19000)
        other=self.repo/'.github'/'workflows'/'rovor-mac-exec-proof.yml'
        other.write_text('B'*19000)
        with self.assertRaisesRegex(ValueError,'Combined source too large'):
            worker.load_packet(self.repo,'runner-blocker')

    def test_http_payload_uses_local_loopback_only_and_one_route(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*exc): return None
            def read(self,n):
                return json.dumps({'choices':[{'message':{'content':'Review only'}}],
                                   'usage':{'total_tokens':10}}).encode()
        calls=[]
        def opener(req,timeout):
            calls.append((req,timeout))
            return Response()
        answer,usage=worker.http_completion('groq/openai/gpt-oss-120b',
                                            'public task','key-from-keychain',
                                            opener=opener)
        self.assertEqual(answer,'Review only')
        self.assertEqual(usage,{'total_tokens':10})
        self.assertEqual(len(calls),1)
        req,timeout=calls[0]
        self.assertEqual(req.full_url,worker.GATEWAY)
        self.assertIn('127.0.0.1',req.full_url)
        body=json.loads(req.data)
        self.assertEqual(body['model'],'groq/openai/gpt-oss-120b')
        self.assertFalse(body['stream'])
        self.assertEqual(len(body['messages']),2)
        self.assertNotIn('key-from-keychain',req.data.decode())

    def test_keychain_stays_local_and_not_logged(self):
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':''}):
            with mock.patch.object(worker.sys,'platform','darwin'):
                def lookup(cmd,**kwargs):
                    self.assertEqual(cmd[0],'/usr/bin/security')
                    self.assertIn('rovordigital.omniroute.endpoint',cmd)
                    return subprocess.CompletedProcess(cmd,0,
                            stdout='stored-endpoint-key\n',stderr='')
                self.assertEqual(worker.access_key(lookup=lookup),
                                 'stored-endpoint-key')

    def test_local_key_invalid_or_missing_fails(self):
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':''}):
            with mock.patch.object(worker.sys,'platform','linux'):
                with self.assertRaisesRegex(ValueError,'unavailable'):
                    worker.access_key()
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'line1\nline2'}):
            with self.assertRaisesRegex(ValueError,'Invalid'):
                worker.access_key()

    def test_all_three_model_draft_jobs_via_mock_no_gui_or_github_write(self):
        with mock.patch.object(worker,'http_completion',
                               side_effect=lambda m,p,k:('Audit only',None)) as llm:
            with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'mock-key'}):
                with redirect_stdout(io.StringIO()) as out:
                    result=worker.main(['--repo',str(self.repo),'--all',
                                        '--out',str(self.out),
                                        '--model','explicit/verified-route',
                                        '--approve-model-use',
                                        '--confirm-no-paid-fallback'])
        self.assertEqual(result,0)
        self.assertEqual(llm.call_count,3)
        answer=json.loads(out.getvalue())
        self.assertEqual(len(answer['results']),3)
        self.assertTrue(all(x['status']=='draft_completed_needs_review'
                            for x in answer['results']))
        self.assertFalse(answer['host_app_control_verified'])
        self.assertFalse(answer['paid_fallback_attempted'])


if __name__=='__main__':
    unittest.main()
