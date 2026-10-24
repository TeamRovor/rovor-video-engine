import sys,json,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hud_employee_snapshot as h

class EmployeeStatusTests(unittest.TestCase):
    def row(self,**kwargs):
        return dict(payload=json.dumps({'assignment':'mike-test-plan'}),result=None,status='running',lease_until=1100,updated_at=999,**kwargs)
    def test_roles_lease_and_freshness(self):
        d=h.project([self.row()],{'recent':True},{},1000)
        self.assertEqual(len(d['employees']),8)
        mike=next(x for x in d['employees'] if x['id']=='mike')
        self.assertEqual(mike['status'],'running');self.assertFalse(mike['online_verified'])
        self.assertEqual(mike['latest_job']['actual_model'],None)
        self.assertEqual(h.project([self.row()],{'recent':False},{},1000)['employees'][1]['status'],'running_unverified')
    def test_privacy_and_unknown_owner(self):
        r=self.row();r['payload']=json.dumps({'public_task':{'id':'overnight-jane-check','title':'PRIVATE TITLE'},'secret':'KEY'})
        r['result']=json.dumps({'role':'Jane','route':'rovor-fast-free-v1','selected_model_config_id':'provider/model','receipt':'PRIVATE_PATH','draft':'PRIVATE_DRAFT'})
        d=h.project([r],{'recent':True},{'overnight-jane-check':'Public task title'},1000)
        text=json.dumps(d)
        for bad in ('PRIVATE TITLE','KEY','PRIVATE_PATH','PRIVATE_DRAFT'):self.assertNotIn(bad,text)
        jane=d['employees'][2];self.assertEqual(jane['latest_job']['task'],'Public task title');self.assertEqual(jane['latest_job']['configured_model'],'provider/model');self.assertIsNone(jane['latest_job']['actual_model'])
        r['payload']='{}';r['result']='{}';self.assertEqual(h.project([r],{}, {},1000)['unassigned_jobs'],1)
    def test_completed_is_not_current_and_missing_state_fails_closed(self):
        r=self.row();r['status']='needs_review';r['result']='{"role":"mike"}'
        j=h.project([r],{'recent':True},{},1000)['employees'][1]['latest_job'];self.assertFalse(j['current']);self.assertEqual(j['state'],'pending_or_failed_review')
        d=h.snapshot('/not/a/real/worker/state',{},now=1000);self.assertEqual(d['source'],'worker_state_unavailable');self.assertTrue(all(x['latest_job'] is None for x in d['employees']))
if __name__=='__main__':unittest.main()
