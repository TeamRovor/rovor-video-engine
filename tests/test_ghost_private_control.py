"""Offline no-Mac/no-network regression suite for private Rovor bridge."""
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import ghost_private_control as bridge


class TestPrivateControl(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home=Path(temporary.name)
        (self.home/'Documents'/'Rovor').mkdir(parents=True)
        self.repo='TeamRovor/mac-control-private'
        self.job='smoke-private-001'
        self.packet={'schema':1,'id':self.job,'kind':'system.ping','payload':{}}
        self.calls=[]
        self.private=True
        self.staged=None
        self.fail_posts=False
        self.post_response={'id':1}

    def http(self,method,path,token,body=None):
        self.calls.append((method,path,body))
        self.assertEqual(token,'test-token')
        if method=='GET' and path=='/repos/'+self.repo:
            return {'full_name':self.repo,'private':self.private,'archived':False}
        if method=='GET' and path=='/repos/'+self.repo+'/contents/control/jobs/'+self.job+'.json?ref=main':
            raw=json.dumps(self.packet).encode()
            return {'encoding':'base64','type':'file','size':len(raw),'content':base64.b64encode(raw).decode()}
        if method=='POST' and path=='/repos/'+self.repo+'/issues/7/comments':
            if self.fail_posts:raise bridge.Refused('simulated network error')
            return self.post_response
        self.fail('Unexpected method or path: '+method+' '+path)

    def work(self,**kwargs):
        return bridge.bridge(self.repo,self.job,home=self.home,token='test-token',
                             issue_number=7,http=self.http,**kwargs)

    def test_repository_identity_and_public_refusal(self):
        for name in ('TeamRovor/rovor-video-engine','Someone/other','TeamRovor/X',
                     'TeamRovor/../outside','TeamRovor/private/name'):
            with self.subTest(name=name):
                with self.assertRaises(bridge.Refused):
                    bridge.repo_name(name)
        self.private=False
        with self.assertRaisesRegex(bridge.Refused,'not confirmed private'):
            self.work()
        self.assertFalse((self.home/'Documents'/'Rovor'/bridge.STATE).exists())

    def test_expires_if_task_id_payload_or_capability_invalid(self):
        for value in ('bad id','..', 'Bad-ABC','slash/path','a'*70):
            with self.subTest(value=value):
                with self.assertRaises(bridge.Refused):bridge.job_name(value)
        variants=[
            {'schema':True,'id':self.job,'kind':'system.ping','payload':{}},
            {'schema':1,'id':'another-safe-task','kind':'system.ping','payload':{}},
            {'schema':1,'id':self.job,'kind':'system.ping','payload':{'shell':'ls'}},
            {'schema':1,'id':self.job,'kind':'files.delete','payload':{}},
            {'schema':1,'id':self.job,'kind':'moho.animate','payload':{}},
            {'schema':1,'id':self.job,'kind':'files.inventory','payload':{'subpath':'..'}},
            {'schema':1,'id':self.job,'kind':'system.ping','payload':{},'cmd':'whoami'},
        ]
        for packet in variants:
            with self.subTest(packet=packet):
                with self.assertRaises(bridge.Refused):
                    bridge.validate_packet(packet,self.job,allow_inventory=True)

    def test_encoded_packet_content_must_be_text(self):
        base_http = self.http
        for malformed in (None, 42, [], {'encoded':'abc'}):
            with self.subTest(malformed=malformed):
                def fake_http(method, path, token, body=None):
                    if method == 'GET' and '/contents/control/jobs/' in path:
                        return {'type':'file','encoding':'base64','size':24,
                                'content':malformed}
                    return base_http(method,path,token,body)
                with self.assertRaises(bridge.Refused):
                    bridge.fetch_private_job(
                        self.repo,self.job,'test-token',http=fake_http)

    def test_inventory_requires_exact_local_approval(self):
        self.packet={'schema':1,'id':self.job,'kind':'files.inventory','payload':{'subpath':'.'}}
        with self.assertRaises(bridge.Refused):self.work()
        dry=self.work(allow_inventory=True)
        self.assertEqual(dry['kind'],'files.inventory')
        self.assertFalse(dry['executed'])
        self.assertFalse((self.home/'Documents'/'Rovor'/bridge.SANDBOX).exists())

    def test_dry_run_checks_remote_private_without_local_mutation(self):
        out=self.work()
        self.assertEqual(out['status'],'valid_private_job_dry_run')
        self.assertFalse(out['executed'])
        self.assertFalse((self.home/'Documents'/'Rovor'/bridge.STATE).exists())
        self.assertEqual(len(self.calls),2)

    def test_execute_and_exact_once_receipt_persisted(self):
        out=self.work(execute=True)
        self.assertEqual(out['status'],'succeeded')
        self.assertTrue(out['receipt_posted'])
        state=self.home/'Documents'/'Rovor'/bridge.STATE/self.job
        self.assertTrue((state/'jobs.sqlite3').is_file())
        self.assertTrue((state/bridge.MARKER).is_file())
        post=self.calls[-1]
        self.assertEqual(post[0],'POST')
        self.assertEqual(post[1],'/repos/'+self.repo+'/issues/7/comments')
        self.assertNotIn(str(self.home),json.dumps(post[2]))
        self.assertNotIn('test-token',json.dumps(post[2]))
        second=self.work(execute=True)
        self.assertEqual(second['status'],'succeeded')
        self.assertFalse(second['receipt_posted'])
        self.assertFalse(second['executed'])
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),1)
        import sqlite3
        with sqlite3.connect(str(state/'jobs.sqlite3')) as con:
            self.assertEqual(con.execute('SELECT attempts FROM jobs').fetchone()[0],1)

    def test_network_post_failure_does_not_replay_job(self):
        self.fail_posts=True
        with self.assertRaises(bridge.Refused):self.work(execute=True)
        self.fail_posts=False
        out=self.work(execute=True)
        self.assertEqual(out['status'],'succeeded')
        self.assertTrue(out['receipt_posted'])
        import sqlite3
        with sqlite3.connect(str(self.home/'Documents'/'Rovor'/bridge.STATE/self.job/'jobs.sqlite3')) as con:
            self.assertEqual(con.execute('SELECT attempts FROM jobs').fetchone()[0],1)

    def test_missing_ack_preserves_unposted_receipt_and_does_not_replay(self):
        import sqlite3
        for malformed in ({}, {'id':0}, {'id':True}, {'id':'42'}, None, []):
            with self.subTest(ack=malformed):
                self.post_response = malformed
                with self.assertRaisesRegex(bridge.Refused,'not acknowledged'):
                    self.work(execute=True)
                state=self.home/'Documents'/'Rovor'/bridge.STATE/self.job
                self.assertFalse((state/bridge.MARKER).exists())
                with sqlite3.connect(str(state/'jobs.sqlite3')) as con:
                    self.assertEqual(
                        con.execute('SELECT attempts FROM jobs').fetchone()[0],1)
        self.post_response={'id':1829}
        out=self.work(execute=True)
        self.assertEqual(out['status'],'succeeded')
        self.assertTrue(out['receipt_posted'])
        self.assertFalse(out['executed'])  # Receipt retried; job not rerun
        self.assertTrue((state/bridge.MARKER).exists())
        self.assertEqual(len([x for x in self.calls if x[0]=='POST']),7)

    def test_stop_marker_prevents_any_queue_creation_or_post(self):
        state=self.home/'Documents'/'Rovor'/bridge.STATE
        state.mkdir()
        (state/'STOP').write_text('stop')
        out=self.work(execute=True)
        self.assertEqual(out['status'],'stopped')
        self.assertFalse((state/self.job/'jobs.sqlite3').exists())
        self.assertFalse(any(x[0]=='POST' for x in self.calls))

    def test_symlinked_state_or_workspace_denied(self):
        home=self.home/'Documents'/'Rovor'
        target=self.home/'outside';target.mkdir()
        (home/bridge.STATE).symlink_to(target,target_is_directory=True)
        with self.assertRaises(bridge.Refused):self.work(execute=True)
        (home/bridge.STATE).unlink()
        (home/bridge.SANDBOX).symlink_to(target,target_is_directory=True)
        with self.assertRaises(bridge.Refused):self.work(execute=True)

    def test_db_sidecars_rejected_without_reading_outside(self):
        base=self.home/'Documents'/'Rovor'/bridge.STATE/self.job
        base.mkdir(parents=True)
        outside=self.home/'secret'
        outside.write_text('private')
        for suffix in ('','-wal','-shm'):
            p=base/('jobs.sqlite3'+suffix)
            p.symlink_to(outside)
            with self.subTest(suffix=suffix):
                with self.assertRaises(ValueError): self.work(execute=True)
                self.assertEqual(outside.read_text(),'private')
            p.unlink()

    def test_marker_cannot_redirect_receipt(self):
        self.work(execute=True)
        base=self.home/'Documents'/'Rovor'/bridge.STATE/self.job
        marker=base/bridge.MARKER
        marker.unlink()
        marker.symlink_to(self.home/'missing')
        with self.assertRaises(bridge.Refused): self.work(execute=True)

    def test_receipt_issue_is_locally_fixed_not_remote(self):
        self.packet['receipt_issue']=8
        with self.assertRaises(bridge.Refused): self.work(execute=True)
        self.packet.pop('receipt_issue')
        with self.assertRaises(bridge.Refused):bridge.bridge(self.repo,self.job,
            home=self.home,token='test-token',issue_number=None,
            execute=True,http=self.http)

    def test_no_local_workspace_exists_before_successful_auth(self):
        self.private=False
        with self.assertRaises(bridge.Refused): self.work(execute=True)
        self.assertFalse((self.home/'Documents'/'Rovor'/bridge.STATE).exists())

    def test_active_running_job_not_reexecuted(self):
        self.work(execute=True)
        state=self.home/'Documents'/'Rovor'/bridge.STATE/self.job
        import sqlite3
        with sqlite3.connect(str(state/'jobs.sqlite3')) as con:
            con.execute("UPDATE jobs SET status='running',attempts=1")
            con.commit()
        (state/bridge.MARKER).unlink()
        result=self.work(execute=True)
        self.assertEqual(result['status'],'needs_review')
        self.assertFalse(result['executed'])  # Past attempt, not this invocation
        with sqlite3.connect(str(state/'jobs.sqlite3')) as con:
            self.assertEqual(con.execute('SELECT attempts FROM jobs').fetchone()[0],1)

if __name__=='__main__':
    unittest.main()