"""Offline private OmniRoute receipt review tests (no model or Mac)."""
from contextlib import redirect_stdout,redirect_stderr
from datetime import datetime,timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import omniroute_workpack_runner as worker
import omniroute_draft_review as gate

REAL_ROOT=Path(__file__).resolve().parents[1]

class OmniRouteDraftReviewTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name).resolve()
        self.repo=self.home/'repository'
        self.repo.mkdir()
        self.receipts=self.home/'private-receipts'
        self.receipts.mkdir(mode=0o700)
        (self.repo/'WORK.md').write_text('# Public ROVOR read-only fixture')
        for slug in worker.PACKETS:
            original=json.loads((REAL_ROOT/'coordination'/'omniroute-workpacks'/
                                 (slug+'.json')).read_text())
            packet=self.repo/'coordination'/'omniroute-workpacks'/(slug+'.json')
            packet.parent.mkdir(parents=True,exist_ok=True)
            packet.write_text(json.dumps(original))
            for file in original['inputs']:
                path=self.repo/file
                path.parent.mkdir(parents=True,exist_ok=True)
                if not path.exists():
                    path.write_text('Public source fixture for '+file)

    def make(self,slug='runner-blocker',status='draft_completed_needs_review',
             answer='Potential runner issue: no runtime evidence observed'):
        packet,_,p=worker.load_packet(self.repo,slug)
        value={'schema_version':1,
               'id':packet['id'],
               'model':'explicit/verified-model',
               'status':status,
               'created_at':datetime.now(timezone.utc).isoformat(),
               'provenance':p,
               'external_effects_allowed':False,
               'source_edits':False,
               'mac_control_verified':False,
               'user_review_required':True}
        if status=='draft_completed_needs_review':
            value.update(answer=answer,usage_reported={'total_tokens':15},
                         elapsed_seconds=0.5)
        elif status=='needs_review_no_auto_retry':
            value.update(error_class='ValueError',elapsed_seconds=0.5)
        path=self.receipts/(slug+'.receipt.json')
        path.write_text(json.dumps(value))
        return path,value

    def test_valid_draft_still_requires_human_review(self):
        path,obj=self.make()
        result=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(result['status'],'draft_ready_for_human_review')
        self.assertTrue(result['source_fresh'])
        self.assertTrue(result['response_present'])
        self.assertFalse(result['approval_granted'])
        self.assertFalse(result['actual_mac_execution_verified'])
        self.assertNotIn(obj['answer'],json.dumps(result))

    def test_batch_cli_never_writes_model_output_or_performs_actions(self):
        for slug in worker.PACKETS:self.make(slug)
        before=sorted(str(p) for p in self.home.rglob('*'))
        out=io.StringIO()
        with redirect_stdout(out):
            result=gate.main(['--repo',str(self.repo),
                              '--receipts',str(self.receipts),'--all'])
        self.assertEqual(result,0)
        self.assertEqual(before,sorted(str(p) for p in self.home.rglob('*')))
        summary=json.loads(out.getvalue())
        self.assertEqual(len(summary['results']),len(worker.PACKETS))
        self.assertFalse(summary['external_effects_performed'])
        self.assertFalse(summary['automatic_task_approval'])
        self.assertTrue(all(x['status']=='draft_ready_for_human_review'
                            for x in summary['results']))

    def test_source_change_invalidates_existing_draft_without_content_leak(self):
        self.make()
        original=self.repo/'.github'/'workflows'/'rovor-mac-exec-proof.yml'
        original.write_text(original.read_text()+'\nNew current revision')
        result=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(result['status'],'stale_source')
        self.assertEqual(result['reasons'],['source_digest_mismatch'])
        self.assertFalse(result['source_fresh'])

    def test_packet_change_invalidates_existing_draft(self):
        self.make()
        p=self.repo/'coordination'/'omniroute-workpacks'/'runner-blocker.json'
        obj=json.loads(p.read_text())
        obj['title']='Changed title, needs regenerated draft'
        p.write_text(json.dumps(obj))
        self.assertEqual(gate.inspect(
            self.repo,self.receipts,'runner-blocker')['status'],'stale_source')

    def test_reject_receipt_attempting_self_approval_or_mac_proof(self):
        for key,attack in [('user_review_required',False),
                           ('mac_control_verified',True),
                           ('external_effects_allowed',True),
                           ('source_edits',True),
                           ('id','different-agent'),
                           ('model','malicious model')]:
            with self.subTest(key=key):
                path,obj=self.make()
                obj[key]=attack
                path.write_text(json.dumps(obj))
                self.assertEqual(gate.inspect(
                    self.repo,self.receipts,'runner-blocker')['status'],
                    'invalid_receipt')

    def test_refuses_metadata_and_unknown_fields(self):
        for key,value in [('unknown_user_control',True),('usage_reported',
                          {'total_tokens':True,'secret':'no'}),
                          ('elapsed_seconds',-1),
                          ('answer','')]:
            with self.subTest(key=key):
                path,obj=self.make()
                obj[key]=value
                path.write_text(json.dumps(obj))
                self.assertEqual(gate.inspect(
                    self.repo,self.receipts,'runner-blocker')['status'],
                    'invalid_receipt')

    def test_detects_high_confidence_secret_without_printing_it(self):
        secret='ghp_'+'a'*34
        self.make(answer='Never publish this secret: '+secret)
        result=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(result['status'],'sensitive_draft_blocked')
        self.assertNotIn(secret,json.dumps(result))
        self.assertFalse(result['approval_granted'])

    def test_flags_unsupported_native_mac_execution_claim(self):
        self.make(answer='I verified the Mac runner and connected Final Cut.')
        result=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(result['status'],'execution_claim_needs_review')
        self.assertEqual(result['reasons'],['unsupported_execution_claim'])
        self.assertFalse(result['actual_mac_execution_verified'])

    def test_observed_stale_header_and_token_usage_trigger_review(self):
        cases=(
            ('provider-efficiency','**Date:** 2025-01-15 (analysis date)',2400,
             {'report_header_year_mismatch','near_completion_token_cap_truncation_unknown'}),
            ('supervisor-resilience','**Date:** 2024‑XX‑XX',2398,
             {'report_date_placeholder','near_completion_token_cap_truncation_unknown'}),
            ('supervisor-resilience','**Date:** 2024–XX–XX',2398,
             {'report_date_placeholder','near_completion_token_cap_truncation_unknown'}),
        )
        for slug,header,used,expected in cases:
            with self.subTest(slug=slug):
                path,obj=self.make(slug,answer=header+'\n## Research notes\nUnverified draft.')
                obj['created_at']='2026-10-23T18:00:00-05:00'
                obj['usage_reported']={'completion_tokens':used,
                                      'prompt_tokens':50,'total_tokens':used+50}
                path.write_text(json.dumps(obj))
                result=gate.inspect(self.repo,self.receipts,slug)
                self.assertEqual(result['status'],'content_quality_needs_review')
                self.assertEqual(set(result['reasons']),expected)
                self.assertFalse(result['approval_granted'])
                self.assertNotIn(header,json.dumps(result))

    def test_current_header_and_historical_body_dates_are_reviewable(self):
        body=('**Date:** 2026-10-23\n'
              '# Evidence\nThe older 2024-XX-XX and 2025-01-15 refer '
              'to past work, not the current memo.')
        path,obj=self.make('provider-efficiency',answer=body)
        obj['created_at']='2026-10-23T18:00:00-05:00'
        obj['usage_reported']={'completion_tokens':2350}
        path.write_text(json.dumps(obj))
        outcome=gate.inspect(self.repo,self.receipts,'provider-efficiency')
        self.assertEqual(outcome['status'],'draft_ready_for_human_review')

    def test_new_4096_limit_receipt_not_wrongly_flagged_at_2400_tokens(self):
        path,obj=self.make(answer='**Date:** 2026-10-23\\n'
            'Public-source technical draft, with proposed checks only.')
        obj['created_at']='2026-10-23T18:00:00-05:00'
        obj['completion_token_limit']=worker.MAX_COMPLETION_TOKENS
        obj['usage_reported']={'completion_tokens':2500,
            'prompt_tokens':300,'total_tokens':2800}
        path.write_text(json.dumps(obj))
        verdict=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(verdict['status'],'draft_ready_for_human_review')
        self.assertFalse(verdict['approval_granted'])
        self.assertFalse(verdict['actual_mac_execution_verified'])

    def test_new_limit_near_real_request_ceiling_still_flags_truncation(self):
        path,obj=self.make()
        obj['completion_token_limit']=worker.MAX_COMPLETION_TOKENS
        obj['usage_reported']={'completion_tokens':worker.MAX_COMPLETION_TOKENS-20}
        path.write_text(json.dumps(obj))
        verdict=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(verdict['status'],'content_quality_needs_review')
        self.assertEqual(verdict['reasons'],
                         ['near_completion_token_cap_truncation_unknown'])

    def test_old_legacy_2400_token_receipts_stay_conservatively_flagged(self):
        path,obj=self.make()
        obj['usage_reported']={'completion_tokens':2400}
        path.write_text(json.dumps(obj))
        verdict=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(verdict['status'],'content_quality_needs_review')
        self.assertEqual(verdict['reasons'],
                         ['near_completion_token_cap_truncation_unknown'])

    def test_forged_or_invalid_new_token_caps_fail_closed(self):
        for invalid in (True,4097,2400,0,"4096",None):
            with self.subTest(invalid=invalid):
                path,obj=self.make()
                obj['completion_token_limit']=invalid
                path.write_text(json.dumps(obj))
                verdict=gate.inspect(self.repo,self.receipts,'runner-blocker')
                self.assertEqual(verdict['status'],'invalid_receipt')
                self.assertEqual(verdict['reasons'],
                                 ['invalid_completion_request_limit'])

    def test_new_failed_receipt_still_no_retry_and_never_review_ready(self):
        path,obj=self.make(status='needs_review_no_auto_retry')
        obj['completion_token_limit']=worker.MAX_COMPLETION_TOKENS
        obj['admission_code']='incomplete_length_stop'
        path.write_text(json.dumps(obj))
        verdict=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(verdict['status'],'failed_needs_review')
        self.assertFalse(verdict['response_present'])
        self.assertFalse(verdict['approval_granted'])

    def test_no_header_and_missing_completion_usage_are_reviewable(self):
        self.make('provider-efficiency',answer='No report date or usage known.')
        self.assertEqual(gate.inspect(self.repo,self.receipts,
            'provider-efficiency')['status'],'draft_ready_for_human_review')

    def test_pending_and_failed_receipts_never_count_as_draft(self):
        for state,status in [('reserved_no_retry','incomplete_needs_review'),
                             ('needs_review_no_auto_retry','failed_needs_review')]:
            with self.subTest(state=state):
                self.make(status=state)
                self.assertEqual(gate.inspect(
                    self.repo,self.receipts,'runner-blocker')['status'],status)

    def test_missing_or_symlinked_receipt_is_not_read(self):
        res=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(res['status'],'invalid_receipt')
        target=self.home/'outside'
        target.write_text('{"answer":"secret"}')
        (self.receipts/'runner-blocker.receipt.json').symlink_to(target)
        res=gate.inspect(self.repo,self.receipts,'runner-blocker')
        self.assertEqual(res['status'],'invalid_receipt')
        self.assertNotIn('secret',json.dumps(res))

    def test_refuses_redirected_private_folder_without_creation(self):
        outside=self.home/'elsewhere'
        outside.mkdir()
        alias=self.home/'redirect'
        alias.symlink_to(outside,target_is_directory=True)
        self.assertEqual(gate.inspect(
            self.repo,alias/'receipts','runner-blocker')['status'],
            'private_receipt_root_unavailable')
        self.assertFalse((outside/'receipts').exists())

    def test_non_secret_malformed_data_stays_private(self):
        p=self.receipts/'runner-blocker.receipt.json'
        p.write_bytes(b'{' + b'\x00'*1024)
        self.assertEqual(gate.inspect(self.repo,self.receipts,
                                     'runner-blocker')['status'],'invalid_receipt')
        p.write_bytes(b'X'*61000)
        self.assertEqual(gate.inspect(self.repo,self.receipts,
                                     'runner-blocker')['status'],'invalid_receipt')

    def test_fail_closed_when_public_source_missing(self):
        self.make()
        (self.repo/'.github'/'workflows'/'rovor-mac-exec-proof.yml').unlink()
        with self.assertRaisesRegex(ValueError,'Missing'):
            gate.inspect(self.repo,self.receipts,'runner-blocker')

    def test_blocks_private_receipts_under_public_checkout(self):
        bad=self.repo/'private'
        bad.mkdir()
        with redirect_stderr(io.StringIO()) as err:
            rc=gate.main(['--repo',str(self.repo),'--receipts',str(bad),
                          '--packet','runner-blocker'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(err.getvalue())['status'],'review_refused')


if __name__=='__main__':
    unittest.main()
