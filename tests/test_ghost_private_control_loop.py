"""Offline private GitHub queue polling -- no network, Mac or real model."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import ghost_private_control as control
import ghost_private_control_loop as loop


class TestPrivatePolling(unittest.TestCase):
    def setUp(self):
        td=tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.home=Path(td.name)
        (self.home/'Documents'/'Rovor').mkdir(parents=True)
        self.repo='TeamRovor/mac-private-safe'
        self.jobs=['private-ping-001','private-ping-002']
        self.calls=[]
        self.private=True
        self.token='local-test-token'

    def http(self,method,path,token,body=None):
        self.calls.append((method,path,body))
        self.assertEqual(token,self.token)
        if method=='GET' and path=='/repos/'+self.repo:
            return {'full_name':self.repo,'private':self.private,'archived':False}
        if method=='GET' and path=='/repos/'+self.repo+'/contents/control/queue.json?ref=main':
            return self.encoded({'schema':1,'jobs':self.jobs})
        if method=='GET' and path.startswith('/repos/'+self.repo+'/contents/control/jobs/'):
            job=path.rsplit('/',1)[-1].removesuffix('.json?ref=main')
            self.assertIn(job,self.jobs)
            return self.encoded({'schema':1,'id':job,'kind':'system.ping','payload':{}})
        if method=='POST' and path=='/repos/'+self.repo+'/issues/4/comments':
            return {'id':345}
        self.fail('Unexpected '+method+' '+path)

    @staticmethod
    def encoded(data):
        raw=json.dumps(data).encode('utf-8')
        return {'type':'file','encoding':'base64','size':len(raw),
                'content':base64.b64encode(raw).decode('ascii')}

    def poll(self,**kw):
        return loop.poll(self.repo,self.token,self.home,4,http=self.http,**kw)

    def test_two_distinct_queue_jobs_run_once_and_report(self):
        result=self.poll(max_jobs=2)
        self.assertEqual(result['jobs_checked'],2)
        self.assertEqual(result['jobs_succeeded'],2)
        self.assertEqual(result['stop_reason'],'max_jobs')
        self.assertFalse(result['app_control_verified'])
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),2)
        state=self.home/'Documents'/'Rovor'/control.STATE
        self.assertEqual(len([p for p in state.iterdir() if p.is_dir()]),2)
        clock=[0]
        def tick():return clock[0]
        def sleep(s):clock[0]+=s
        again=self.poll(max_jobs=2,max_seconds=120,poll_seconds=60,monotonic=tick,sleeper=sleep)
        self.assertEqual(again['jobs_checked'],0)
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),2)
        import sqlite3
        for j in self.jobs:
            with sqlite3.connect(str(state/j/'jobs.sqlite3')) as conn:
                self.assertEqual(conn.execute('SELECT attempts FROM jobs').fetchone()[0],1)

    def test_old_queue_receipt_does_not_starve_new_job_budget_one(self):
        first=self.poll(max_jobs=1)
        self.assertEqual(first['jobs_checked'],1)
        second=self.poll(max_jobs=1)
        self.assertEqual(second['jobs_checked'],1)
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),2)

    def test_empty_queue_ends_on_time_limit_no_job(self):
        self.jobs=[]
        clock=[0]
        def tick():return clock[0]
        def sleep(seconds):clock[0]+=seconds
        result=self.poll(max_seconds=120,poll_seconds=60,monotonic=tick,sleeper=sleep)
        self.assertEqual(result['stop_reason'],'max_seconds')
        self.assertEqual(result['jobs_checked'],0)
        self.assertEqual(result['queue_polls'],2)
        self.assertEqual(clock[0],120)
        self.assertFalse((self.home/'Documents'/'Rovor'/control.STATE).exists())

    def test_private_queue_must_match_strict_schema(self):
        cases=[{'schema':True,'jobs':self.jobs},
               {'schema':1,'jobs':self.jobs,'script':'rm -rf'},
               {'schema':1,'jobs':[self.jobs[0],self.jobs[0]]},
               {'schema':1,'jobs':['../../outside']},
               {'schema':1,'jobs':['private-ping-001']*21},
               {'schema':1,'jobs':'private-ping-001'},
               {'schema':1,'jobs':[None]},
               {'schema':1,'jobs':['x'*80]}]
        for value in cases:
            with self.subTest(value=value):
                def http(method,path,token,body=None):
                    if path.endswith('/queue.json?ref=main'):
                        return self.encoded(value)
                    return {'full_name':self.repo,'private':True,'archived':False}
                with self.assertRaises(control.Refused):
                    loop.fetch_queue(self.repo,self.token,http=http)

    def test_public_repo_refused_even_if_api_says_private(self):
        with self.assertRaises(control.Refused):
            loop.fetch_queue('TeamRovor/rovor-video-engine',self.token,http=self.http)
        self.private=False
        with self.assertRaises(control.Refused):
            self.poll(max_jobs=1)
        self.assertFalse((self.home/'Documents'/'Rovor'/control.STATE).exists())

    def test_limits_do_not_allow_unbounded_jobs_or_tight_polls(self):
        cases=[{'max_jobs':4},{'max_jobs':0}, {'max_jobs':True},
               {'max_seconds':3601},{'max_seconds':0},
               {'poll_seconds':5},{'poll_seconds':601},
               {'poll_seconds':False}]
        for kw in cases:
            with self.subTest(kw=kw):
                with self.assertRaises(control.Refused): self.poll(**kw)
        self.assertEqual(len(self.calls),0)

    def test_stop_does_not_read_repo_or_create_queue(self):
        state=self.home/'Documents'/'Rovor'/control.STATE
        state.mkdir()
        (state/'STOP').write_text('stop')
        out=self.poll(max_jobs=2)
        self.assertEqual(out['stop_reason'],'stop_requested')
        self.assertEqual(out['queue_polls'],0)
        self.assertFalse(self.calls)
        self.assertEqual(list(state.iterdir()),[state/'STOP'])

    def test_symlinked_stop_file_fails_closed(self):
        state=self.home/'Documents'/'Rovor'/control.STATE
        state.mkdir()
        (state/'STOP').symlink_to(self.home/'nonexistent')
        with self.assertRaises(control.Refused): self.poll()
        self.assertFalse(self.calls)

    def test_receipt_post_contains_no_local_path_secret_or_inventory(self):
        self.poll(max_jobs=1)
        post=next(x for x in self.calls if x[0]=='POST')
        body=json.dumps(post[2])
        self.assertNotIn(self.token,body)
        self.assertNotIn(str(self.home),body)
        self.assertNotIn('files',body)
        self.assertIn('"status"',post[2]['body'])

    def test_empty_missing_repository_is_rejected_before_state(self):
        with self.assertRaises(control.Refused):
            loop.poll(self.repo,None,self.home,4,http=self.http)
        self.assertFalse((self.home/'Documents'/'Rovor'/control.STATE).exists())

    def test_job_budget_one_never_claims_next_job(self):
        self.poll(max_jobs=1)
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),1)
        self.assertFalse((self.home/'Documents'/'Rovor'/control.STATE/self.jobs[1]).exists())

if __name__=='__main__':unittest.main()