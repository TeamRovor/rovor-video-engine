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
            status = 200
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

    def test_safe_local_open_disables_environment_proxies_and_redirects(self):
        captured=[]
        class FakeOpener:
            def open(self,req,timeout):
                self.last=(req,timeout)
                return 'fake'
        actual=FakeOpener()
        def build(*handlers):
            captured.extend(handlers)
            return actual
        with mock.patch.object(worker.request,'build_opener',side_effect=build):
            result=worker.safe_local_open('request',12)
        self.assertEqual(result,'fake')
        self.assertEqual(actual.last,('request',12))
        self.assertTrue(any(type(h) is worker.request.ProxyHandler
                            and h.proxies == {} for h in captured))
        self.assertTrue(any(isinstance(h,worker.RefuseRedirects)
                            for h in captured))
        handler=worker.RefuseRedirects()
        with self.assertRaisesRegex(ValueError,'localhost redirect refused'):
            handler.redirect_request(None,None,302,'Found',{},
                                     'https://external.invalid/steal')

    def test_http_refuses_redirect_or_non_200_status(self):
        class Response:
            def __init__(self,status): self.status=status
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,*args):
                raise AssertionError('should not read unexpected HTTP status')
        for status in (301,302,307,308,401,500):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError,'not HTTP 200'):
                    worker.http_completion('valid/route','prompt','dummy',
                        opener=lambda req,timeout:Response(status))
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            worker.http_completion('invalid with spaces','prompt','key',
                                   opener=lambda *_:self.fail('no request'))

    def test_only_bounded_integer_usage_counts_are_preserved(self):
        self.assertEqual(worker.sanitized_usage({
            'total_tokens':19,
            'prompt_tokens':True,
            'completion_tokens':-4,
            'api_key':'SHOULD_NOT_BE_SAVED',
            'cost_usd':98.74}),{'total_tokens':19})
        self.assertIsNone(worker.sanitized_usage({'metadata':'secret'}))
        self.assertIsNone(worker.sanitized_usage('secret'))

    def test_refuse_receipts_under_public_git_checkout(self):
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'fixture-key'}):
            with redirect_stderr(io.StringIO()) as err:
                code=worker.main(['--repo',str(self.repo),'--packet',
                    'runner-blocker','--model','test/route',
                    '--approve-model-use','--confirm-no-paid-fallback',
                    '--out',str(self.repo/'accidental-private')])
        self.assertEqual(code,2)
        self.assertFalse((self.repo/'accidental-private').exists())
        self.assertNotIn('fixture-key',err.getvalue())

    def test_refuse_symlinked_ancestor_to_private_receipts_folder(self):
        target=self.base/'destination'
        target.mkdir()
        ancestor=self.base/'alias'
        ancestor.symlink_to(target,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'redirected parent'):
            worker.safe_private_root(ancestor/'receipts')
        self.assertFalse((target/'receipts').exists())

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

    def test_per_packet_routes_are_selected_without_fallback(self):
        records={}
        def completion(model,prompt,key):
            for slug in worker.PACKETS:
                if slug.replace('-','') in prompt.replace('-',''):
                    pass
            records[model]=records.get(model,0)+1
            return ('No executed Mac action; draft only',None)
        with mock.patch.object(worker,'http_completion',side_effect=completion):
            with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'fake'}):
                with redirect_stdout(io.StringIO()) as out:
                    rc=worker.main(['--repo',str(self.repo),'--all',
                         '--out',str(self.out),'--approve-model-use',
                         '--confirm-no-paid-fallback',
                         '--route','runner-blocker=groq/verified-fast',
                         '--route','supervisor-resilience=mistral/verified-code',
                         '--route','provider-efficiency=gemini/verified-reason'])
        self.assertEqual(rc,0)
        self.assertEqual(set(records),{'groq/verified-fast',
                                      'mistral/verified-code',
                                      'gemini/verified-reason'})
        self.assertEqual(sum(records.values()),3)
        self.assertFalse(json.loads(out.getvalue())['paid_fallback_attempted'])

    def test_reject_missing_role_routing_or_untrusted_model(self):
        with mock.patch.dict(os.environ,{'OMNIROUTE_API_KEY':'fake'}):
            with redirect_stderr(io.StringIO()):
                rc=worker.main(['--repo',str(self.repo),'--all',
                                '--approve-model-use',
                                '--confirm-no-paid-fallback',
                                '--route','runner-blocker=fast/only'])
        self.assertEqual(rc,2)
        self.assertFalse(self.out.exists())

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



    def test_direct_api_refuses_receipts_inside_checkout_before_completion(self):
        alias = self.base / 'repo-alias'
        alias.symlink_to(self.repo, target_is_directory=True)
        destinations = (
            self.repo,
            self.repo / 'private-receipts',
            alias,
            alias / 'nested-private-receipts',
        )

        def must_not_call(*args, **kwargs):
            self.fail('completion must not run for a public-checkout destination')

        for destination in destinations:
            with self.subTest(destination=str(destination)):
                with self.assertRaisesRegex(
                        ValueError, 'inside Git checkout or redirected'):
                    worker.run_packet(
                        self.repo, destination, 'runner-blocker',
                        'explicit/route', 'fixture-key',
                        completion=must_not_call,
                    )
                if destination == alias:
                    self.assertTrue(alias.is_symlink(), 'existing alias must not be removed')
                elif destination != self.repo:
                    self.assertFalse(destination.exists())
        self.assertFalse((self.repo / 'private-receipts').exists())
        self.assertFalse((self.repo / 'nested-private-receipts').exists())


if __name__=='__main__':
    unittest.main()
