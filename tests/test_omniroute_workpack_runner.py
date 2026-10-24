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
        self.base=Path(tmp.name).resolve()
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

    def test_direct_api_refuses_receipts_in_ancestor_checkout(self):
        outer=self.base/'outer-checkout'
        outer.mkdir()
        (outer/'.git').mkdir()
        nested=outer/'tools'/'nested-rovor'
        nested.parent.mkdir()
        shutil.copytree(self.repo,nested)
        out=outer/'private-receipts'
        called=[]
        with self.assertRaisesRegex(ValueError,'inside Git checkout'):
            worker.run_packet(nested,out,'runner-blocker',
                'groq/openai/gpt-oss-120b','private-key',
                completion=lambda *args:called.append(args))
        self.assertEqual(called,[])
        self.assertFalse(out.exists())

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
        self.assertEqual(report['completion_token_limit'],worker.MAX_COMPLETION_TOKENS)
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

    def test_future_failed_receipt_records_only_safe_admission_code(self):
        def failed(*args):
            raise worker.GatewayInvalidCompletion("invalid_usage_shape")
        result=worker.run_packet(self.repo,self.out,'runner-blocker',
                                 'rovor-fast-free-v1','test-key',completion=failed)
        saved=json.loads(Path(result['receipt']).read_text())
        self.assertEqual(saved['status'],'needs_review_no_auto_retry')
        self.assertEqual(saved['completion_token_limit'],worker.MAX_COMPLETION_TOKENS)
        self.assertEqual(saved['error_class'],'GatewayInvalidCompletion')
        self.assertEqual(saved['admission_code'],'invalid_usage_shape')
        self.assertIsNone(worker.safe_admission_code(
            worker.GatewayInvalidCompletion("SECRET_NOT_ALLOWED")))
        self.assertIsNone(worker.safe_admission_code(
            ValueError("PRIVATE_PROVIDER_TEXT")))
        self.assertEqual(worker.run_packet(
            self.repo,self.out,'runner-blocker','rovor-fast-free-v1',
            'test-key',completion=lambda *_:self.fail("replayed"))['status'],
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

    def test_approved_packet_growth_has_explicit_bounded_public_excerpt(self):
        slug = 'unattended-readiness'
        manifest = json.loads((self.repo/'coordination'/'omniroute-workpacks'/
                               (slug+'.json')).read_text())
        for rel in manifest['inputs']:
            (self.repo/rel).write_text(('Public source ' + rel + ' ') * 850)
        packet, prompt, provenance = worker.load_packet(self.repo, slug)
        self.assertEqual(packet['slug'], slug)
        self.assertIn('PUBLIC SOURCE EXCERPT', prompt)
        self.assertIn('characters intentionally omitted', prompt)
        self.assertIn('explicit_source_excerpts', provenance)
        self.assertLess(len(prompt), 38000)
        self.assertTrue(all(v['included_chars'] <= v['total_chars']
                            for v in provenance['explicit_source_excerpts'].values()))
        self.assertTrue(any(v['omitted_chars'] > 0
                            for v in provenance['explicit_source_excerpts'].values()))

    def test_new_shortform_context_is_explicit_and_smaller_than_full_packet(self):
        slug = 'unattended-readiness'
        manifest=json.loads((self.repo/'coordination'/'omniroute-workpacks'/
                            (slug+'.json')).read_text())
        for rel in manifest['inputs']:
            (self.repo/rel).write_text(('Public background; source ' + rel + '.\\n')*650)
        _packet, long_prompt, _legacy = worker.load_packet(self.repo,slug)
        packet, short_prompt, proof = worker.load_packet(
            self.repo,slug,source_budget_chars=9000)
        self.assertEqual(packet['slug'], slug)
        self.assertLess(len(short_prompt),len(long_prompt))
        self.assertLess(len(short_prompt),14000)
        self.assertIn('PUBLIC SOURCE EXCERPT',short_prompt)
        self.assertIn('characters intentionally omitted',short_prompt)
        self.assertEqual(proof['source_budget_chars'],9000)
        self.assertTrue(any(v['omitted_chars']>0 for v
                            in proof['explicit_source_excerpts'].values()))
        original_sources=worker.load_packet(self.repo,slug)[2]['sources']
        self.assertEqual(proof['sources'],original_sources)

    def test_new_budget_is_bound_to_private_provenance_and_never_replayed(self):
        import omniroute_draft_review as reviewer
        slug='unattended-readiness'
        manifest=json.loads((self.repo/'coordination'/'omniroute-workpacks'/
                            (slug+'.json')).read_text())
        for rel in manifest['inputs']:
            (self.repo/rel).write_text(('Verified public fixture '+rel+'\\n')*500)
        calls=[]
        def completion(_model,prompt,_key):
            calls.append(prompt)
            return ('This is a proposal. Review its public-source limitations.',
                    {'prompt_tokens':500,'completion_tokens':80,'total_tokens':580})
        reply=worker.run_packet(self.repo,self.out,slug,'rovor-fast-free-v1',
                                'fake-key',completion=completion,
                                source_budget_chars=11000)
        self.assertEqual(reply['status'],'draft_completed_needs_review')
        saved=json.loads(Path(reply['receipt']).read_text())
        self.assertEqual(saved['source_budget_chars'],11000)
        self.assertEqual(saved['provenance']['source_budget_chars'],11000)
        self.assertEqual(reviewer.inspect(self.repo,self.out,slug)['status'],
                         'draft_ready_for_human_review')
        saved['source_budget_chars']=14500
        Path(reply['receipt']).write_text(json.dumps(saved))
        verdict=reviewer.inspect(self.repo,self.out,slug)
        self.assertEqual(verdict['status'],'stale_source')
        self.assertNotIn('fake-key',json.dumps(verdict))
        again=worker.run_packet(self.repo,self.out,slug,'rovor-fast-free-v1',
                                'fake-key',completion=lambda *_:self.fail('replayed'),
                                source_budget_chars=11000)
        self.assertEqual(again['status'],'previous_attempt_not_replayed')
        self.assertEqual(len(calls),1)

    def test_source_budgets_reject_unapproved_packet_and_bool(self):
        with self.assertRaisesRegex(ValueError,'Unapproved source context budget'):
            worker.load_packet(self.repo,'runner-blocker',source_budget_chars=9000)
        for budget in (True,5000,28000,'9000'):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(ValueError,'Unapproved source context budget'):
                    worker.load_packet(self.repo,'unattended-readiness',
                                       source_budget_chars=budget)

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
                return json.dumps({'choices':[{'message':{'content':'Review only'}, 'finish_reason':'stop'}],
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
        self.assertEqual(timeout,120)
        self.assertEqual(req.full_url,worker.GATEWAY)
        self.assertIn('127.0.0.1',req.full_url)
        body=json.loads(req.data)
        self.assertEqual(body['model'],'groq/openai/gpt-oss-120b')
        self.assertFalse(body['stream'])
        # Jane's v2 free-route response previously hit a 2400-token
        # finish_reason=length. The next revision permits at most 4096
        # output tokens; still one POST only, no retries or paid fallback.
        self.assertEqual(worker.MAX_COMPLETION_TOKENS,4096)
        self.assertEqual(body['max_tokens'],4096)
        self.assertLessEqual(body['max_tokens'],4096)
        self.assertEqual(len(body['messages']),2)
        self.assertNotIn('key-from-keychain',req.data.decode())

    def test_rejects_reasoning_only_and_truncated_gateway_answer(self):
        class Response:
            status = 200
            def __init__(self, data): self.data = data
            def __enter__(self): return self
            def __exit__(self, *exc): return False
            def read(self, n): return json.dumps(self.data).encode()
        cases = [
            ({'choices':[{'message':{'content':''},'finish_reason':'length'}],
              'usage':{'completion_tokens':2400,
                       'completion_tokens_details':{'reasoning_tokens':2400}}},
             'reasoning_budget_exhausted'),
            ({'choices':[{'message':{'content':'Partial'},'finish_reason':'length'}]},
             'incomplete_length_stop'),
            ({'choices':[{'message':{'content':'Looks complete'},'finish_reason':'tool_calls'}]},
             'unapproved_finish_reason'),
            ({'choices':[{'message':{'content':'No finish reason'}}]},
             'unapproved_finish_reason'),
            ({'choices':[]}, 'invalid_response_shape'),
        ]
        for data, reason in cases:
            called = []
            def opener(req, timeout):
                called.append(req.full_url)
                return Response(data)
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, '^' + reason + chr(36)):
                    worker.http_completion('rovor-code-free-v1',
                                           'bounded public context', 'test-key',
                                           opener=opener)
                self.assertEqual(called, [worker.GATEWAY])

    def test_gateway_failures_have_fixed_safe_classes_for_future_receipts(self):
        class HTTPResult:
            def __init__(self, code): self.code = code
        for code, expected in (
                (429, worker.GatewayRateLimited),
                (502, worker.GatewayUpstreamFailure),
                (503, worker.GatewayUpstreamFailure),
                (401, worker.GatewayAuthorizationFailure)):
            def opener(req, timeout):
                raise worker.error.HTTPError(worker.GATEWAY, code,
                                             "SECRET_PROVIDER_RESPONSE", None, None)
            with self.subTest(code=code):
                with self.assertRaises(expected) as raised:
                    worker.http_completion("rovor-code-free-v1",
                                           "bounded public context", "test-key",
                                           opener=opener)
                self.assertNotIn("SECRET_PROVIDER_RESPONSE",
                                 str(raised.exception))
        class Response:
            status=200
            def __init__(self, payload): self.payload=payload
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, n): return json.dumps(self.payload).encode()
        for payload, expected in (
                ({"choices":[{"message":{"content":""},
                              "finish_reason":"length"}],
                  "usage":{"completion_tokens":2400,
                           "completion_tokens_details":{"reasoning_tokens":2400}}},
                 worker.GatewayReasoningExhausted),
                ({"choices":[{"message":{"content":"Partial"},
                              "finish_reason":"length"}]},
                 worker.GatewayTruncatedAnswer),
                ({"choices":[{"message":{"content":""},
                              "finish_reason":"stop"}]},
                 worker.GatewayEmptyAnswer)):
            with self.subTest(error=expected.__name__):
                with self.assertRaises(expected):
                    worker.http_completion("rovor-code-free-v1", "public",
                                           "key", opener=lambda req,timeout:
                                           Response(payload))

    def test_timeout_is_terminal_without_second_http_request(self):
        calls=[]
        def opener(req,timeout):
            calls.append(timeout)
            raise TimeoutError('fixture')
        with self.assertRaises(ValueError):
            worker.http_completion('rovor-code-free-v1','public fixture','fixture-key',opener=opener)
        self.assertEqual(calls,[120])

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
                         '--route','provider-efficiency=gemini/verified-reason',
                         '--route','overnight-acceptance=gemini/verified-reason',
                         '--route','unattended-readiness=gemini/verified-reason'])
        self.assertEqual(rc,0)
        self.assertEqual(set(records),{'groq/verified-fast',
                                      'mistral/verified-code',
                                      'gemini/verified-reason'})
        self.assertEqual(sum(records.values()),len(worker.PACKETS))
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

    def test_all_model_draft_jobs_via_mock_no_gui_or_github_write(self):
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
        self.assertEqual(llm.call_count,len(worker.PACKETS))
        answer=json.loads(out.getvalue())
        self.assertEqual(len(answer['results']),len(worker.PACKETS))
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
