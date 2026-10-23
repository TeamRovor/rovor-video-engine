"""Reproducible source-verification regression tests; stdlib only."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from evaluate import evaluate, read_json, score_case, validate_cases

DIR=Path(__file__).resolve().parent


class CapabilityEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=read_json(DIR/'cases.json')
        cls.good=read_json(DIR/'good-answers.json')
        cls.bad=read_json(DIR/'bad-answers.json')
        cls.index=validate_cases(cls.cases)

    def test_fixture_has_three_distinct_real_workflow_families(self):
        self.assertEqual(set(c['capability'] for c in self.cases['cases']),
                         {'client_intake','sourced_sales','ci_triage'})

    def test_all_reference_outputs_pass(self):
        out=evaluate(self.cases,self.good)
        self.assertEqual(out['summary'],{'passed':3,'failed':0,'total':3})

    def test_all_known_bad_outputs_fail(self):
        out=evaluate(self.cases,self.bad)
        self.assertEqual(out['summary'],{'passed':0,'failed':3,'total':3})

    def test_unknown_price_must_never_be_invented(self):
        result=score_case(self.cases['cases'][0],self.bad['answers'][0])
        codes={x['code'] for x in result}
        self.assertIn('invented_field',codes)
        self.assertIn('missing_or_invented_unknown',codes)

    def test_email_is_a_real_effect_and_cannot_be_inferred(self):
        issues=score_case(self.cases['cases'][0],self.bad['answers'][0])
        self.assertIn('unauthorized_effect',{i['code'] for i in issues})

    def test_sales_claims_cannot_invent_conversion_loss(self):
        issues=score_case(self.cases['cases'][1],self.bad['answers'][1])
        self.assertIn('altered_claim',{i['code'] for i in issues})

    def test_fake_direct_outreach_rejected(self):
        issues=score_case(self.cases['cases'][1],self.bad['answers'][1])
        self.assertIn('unsafe_next_action',{i['code'] for i in issues})

    def test_github_failure_without_steps_is_not_failed_unit_test(self):
        issues=score_case(self.cases['cases'][2],self.bad['answers'][2])
        self.assertIn('misrepresented_ci',{i['code'] for i in issues})

    def test_github_failure_without_steps_is_not_proof_of_spending_limit(self):
        issues=score_case(self.cases['cases'][2],self.bad['answers'][2])
        self.assertIn('invented_root_cause',{i['code'] for i in issues})

    def test_draft_must_not_claim_delivered_and_paid(self):
        issues=score_case(self.cases['cases'][0],self.bad['answers'][0])
        self.assertIn('unearned_approval',{i['code'] for i in issues})

    def test_reject_unsourced_field_modification(self):
        ans=copy.deepcopy(self.good['answers'][0]);ans['fields']['business']['source_ids']=[]
        self.assertIn('unverified_field',{i['code'] for i in score_case(self.cases['cases'][0],ans)})

    def test_reject_unknown_observation(self):
        ans=copy.deepcopy(self.good['answers'][1]);ans['claims'].append({'id':'invented-prospect',
                       'classification':'observed','text':'A real client signed and paid.', 'source_ids':[]})
        self.assertIn('unsupported_claim',{i['code'] for i in score_case(self.cases['cases'][1],ans)})

    def test_reject_missing_reference_fact(self):
        ans=copy.deepcopy(self.good['answers'][0]);ans['fields'].pop('primary_action')
        self.assertIn('unverified_field',{i['code'] for i in score_case(self.cases['cases'][0],ans)})

    def test_reject_duplicate_and_missing_answers(self):
        batch=copy.deepcopy(self.good);batch['answers'].append(batch['answers'][0])
        with self.assertRaisesRegex(ValueError,'Duplicate answer'):
            evaluate(self.cases,batch)
        batch['answers']=[batch['answers'][0]]
        self.assertEqual(evaluate(self.cases,batch)['summary']['failed'],2)

    def test_reject_unknown_case(self):
        batch=copy.deepcopy(self.good);batch['answers'][1]['case_id']='unregistered-case'
        self.assertEqual(evaluate(self.cases,batch)['summary']['failed'],2)

    def test_reject_invalid_ground_truth_without_source_record(self):
        batch=copy.deepcopy(self.cases)
        batch['cases'][0]['known_fields']['business']['source_ids']=['made-up-citation']
        with self.assertRaisesRegex(ValueError,'approved source'):
            validate_cases(batch)

    def test_reject_duplicate_case_ids(self):
        batch=copy.deepcopy(self.cases)
        batch['cases'][1]['id']=batch['cases'][0]['id']
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            validate_cases(batch)

    def test_reject_no_unknowns_assumed_complete(self):
        batch=copy.deepcopy(self.cases);batch['cases'][0]['required_unknowns']=[]
        with self.assertRaisesRegex(ValueError,'Unknown-field'):
            validate_cases(batch)

    def test_cli_success_is_reproducible_and_report_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'report.json'
            run=subprocess.run([sys.executable,str(DIR/'evaluate.py'),'--answers',str(DIR/'good-answers.json'),
                                '--report',str(output)],capture_output=True,text=True,check=False)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(json.loads(output.read_text())['summary']['passed'],3)

    def test_cli_negative_expectation_passes_only_if_bad_examples_fail(self):
        passed=subprocess.run([sys.executable,str(DIR/'evaluate.py'),'--answers',str(DIR/'bad-answers.json'),
                               '--expect','fail'],capture_output=True,text=True)
        self.assertEqual(passed.returncode,0,passed.stderr)
        fail=subprocess.run([sys.executable,str(DIR/'evaluate.py'),'--answers',str(DIR/'bad-answers.json'),
                               '--expect','pass'],capture_output=True,text=True)
        self.assertEqual(fail.returncode,1)

    def test_input_file_size_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data.json';p.write_bytes(b' '*200_001)
            with self.assertRaisesRegex(ValueError,'oversized'):
                read_json(p)


if __name__=='__main__':
    unittest.main()
