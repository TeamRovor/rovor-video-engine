import base64
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import github_atomic_task_intake as atomic


def proposal(ident='new', status='ready', scopes=None, owner=None):
    row = {'id':ident,'title':'A test task','priority':1,'status':status,
           'branch':'feature/' + ident,'scopes':scopes or ['tools/' + ident + '.py'],
           'owner':owner,'depends_on':[],'next_action':'Work only in bounded source',
           'acceptance':'Review and verify exact results'}
    if status in {'active','blocked'}:
        row['updated_at'] = datetime.now(timezone.utc).isoformat()
        row['next_update'] = 'After hosted tests'
    return row


def contents(doc):
    raw = json.dumps(doc).encode()
    return {'type':'file','encoding':'base64','size':len(raw),
            'content':base64.b64encode(raw).decode('ascii')}


class FakeAPI:
    def __init__(self):
        self.head = 'a' * 40
        self.tree = 'b' * 40
        self.commit = 'd' * 40
        self.queue = {'version':1,'tasks':[]}
        self.routing = {'version':1,'tasks':{}}
        self.calls = []
        self.change_head_before_patch = False
        self.fail_patch = False
        self.published = False

    def request(self, method, path, payload=None):
        self.calls.append((method,path,copy.deepcopy(payload)))
        if method == 'GET' and path == '/git/ref/heads/main':
            if self.change_head_before_patch and any(x[0]=='POST' and x[1]=='/git/commits'
                                                     for x in self.calls):
                return {'object':{'sha':'e'*40}}
            return {'object':{'sha':self.head}}
        if method=='GET' and path == '/git/commits/' + self.head:
            return {'sha':self.head,'tree':{'sha':self.tree}}
        if method=='GET' and path.startswith('/contents/coordination/tasks.json?ref='):
            assert path.endswith(self.head)
            return contents(self.queue)
        if method=='GET' and path.startswith('/contents/coordination/work-routing.json?ref='):
            assert path.endswith(self.head)
            return contents(self.routing)
        if method=='POST' and path == '/git/trees':
            return {'sha':'c'*40}
        if method=='POST' and path == '/git/commits':
            return {'sha':self.commit}
        if method=='PATCH' and path == '/git/refs/heads/main':
            if self.fail_patch:
                raise atomic.Conflict('concurrent branch update')
            self.published = True
            return {'object':{'sha':self.commit}}
        raise AssertionError('Unexpected fake request %s %s' % (method,path))


class AtomicGithubIntakeTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()

    def ready(self, data=None, requirements=None):
        return atomic.prepare(self.api, data or proposal(), 'coordination',
                              requirements or ['hosted-ci'])

    def test_pinned_read_has_no_write(self):
        plan = self.ready()
        self.assertEqual(plan['counts'], (1,1))
        self.assertEqual(plan['head'],'a'*40)
        self.assertEqual(plan['base_tree'],'b'*40)
        self.assertEqual([call[0] for call in self.api.calls],['GET']*4)
        self.assertTrue(all(call[1].endswith('?ref='+'a'*40)
                            for call in self.api.calls[-2:]))
        self.assertFalse(self.api.published)

    def test_one_commit_contains_both_files_and_expected_parent(self):
        plan=self.ready()
        result=atomic.publish(self.api,plan)
        self.assertEqual(result,'d'*40)
        self.assertTrue(self.api.published)
        tree_calls=[x for x in self.api.calls if x[1]=='/git/trees']
        self.assertEqual(len(tree_calls),1)
        body=tree_calls[0][2]
        self.assertEqual(body['base_tree'],'b'*40)
        self.assertEqual({x['path'] for x in body['tree']},
                         {'coordination/tasks.json','coordination/work-routing.json'})
        files={entry['path']:json.loads(entry['content']) for entry in body['tree']}
        self.assertEqual(files['coordination/tasks.json']['tasks'][0]['id'],'new')
        self.assertEqual(files['coordination/work-routing.json']['tasks']['new']['lane'],
                         'coordination')
        commit=next(x[2] for x in self.api.calls if x[1]=='/git/commits')
        self.assertEqual(commit['parents'],['a'*40])
        patch=next(x[2] for x in self.api.calls if x[0]=='PATCH')
        self.assertEqual(patch,{'sha':'d'*40,'force':False})

    def test_concurrent_advance_skips_ref_update(self):
        plan=self.ready()
        self.api.change_head_before_patch=True
        with self.assertRaisesRegex(atomic.Conflict,'Main changed'):
            atomic.publish(self.api,plan)
        self.assertFalse(any(x[0]=='PATCH' for x in self.api.calls))
        self.assertFalse(self.api.published)

    def test_nonfastforward_ref_conflict_does_not_publish(self):
        plan=self.ready()
        self.api.fail_patch=True
        with self.assertRaises(atomic.Conflict):
            atomic.publish(self.api,plan)
        self.assertFalse(self.api.published)

    def test_reject_duplicate_from_pinned_queue_before_post(self):
        t=proposal()
        self.api.queue['tasks'].append(t)
        self.api.routing['tasks'][t['id']]={'lane':'coordination','requires':[]}
        with self.assertRaisesRegex(atomic.IntakeError,'already exists'):
            self.ready(t)
        self.assertFalse(any(x[0]=='POST' for x in self.api.calls))

    def test_reject_unclassified_existing_task_before_post(self):
        self.api.queue['tasks'].append(proposal('unrouted'))
        with self.assertRaisesRegex(atomic.IntakeError,'Routing mismatch'):
            self.ready()
        self.assertFalse(any(x[0]=='POST' for x in self.api.calls))

    def test_reject_reserved_scope_collision(self):
        active=proposal('active',status='active',owner='another',
                        scopes=['tools'])
        self.api.queue['tasks'].append(active)
        self.api.routing['tasks']['active']={'lane':'operations','requires':[]}
        with self.assertRaisesRegex(atomic.IntakeError,'overlapping claims'):
            self.ready(proposal(status='active',owner='me'))
        self.assertFalse(any(x[0]=='POST' for x in self.api.calls))

    def test_reject_nonstring_or_corrupt_base64(self):
        for value in (12,None,'$$$$'):
            with self.subTest(value=value):
                self.api=FakeAPI()
                base=self.api.request
                def corrupt(method,path,payload=None):
                    if method=='GET' and '/contents/coordination/tasks.json?' in path:
                        x=contents(self.api.queue);x['content']=value;return x
                    return base(method,path,payload)
                self.api.request=corrupt
                with self.assertRaises(atomic.IntakeError):
                    self.ready()

    def test_reject_invalid_file_size_and_type(self):
        for override in ({'size':5_000_001},{'type':'symlink'},
                         {'encoding':'utf-8'},{'size':-1}):
            with self.subTest(override=override):
                self.api=FakeAPI()
                original=self.api.request
                def bad(method,path,payload=None):
                    if method=='GET' and '/contents/coordination/tasks.json?' in path:
                        x=contents(self.api.queue);x.update(override);return x
                    return original(method,path,payload)
                self.api.request=bad
                with self.assertRaises(atomic.IntakeError):
                    self.ready()

    def test_secret_not_output_in_dry_run_or_apply(self):
        with tempfile.TemporaryDirectory() as td:
            file=Path(td)/'task.json';file.write_text(json.dumps(proposal()))
            with mock.patch.object(atomic,'GitHubAPI',return_value=self.api), \
                 mock.patch.dict(os.environ,{'ROVOR_GITHUB_TOKEN':'TOPSECRETFAKE'}), \
                 mock.patch('builtins.print') as printer:
                self.assertEqual(atomic.main(['--task-json',str(file),'--lane',
                                              'coordination']),0)
                self.assertNotIn('TOPSECRETFAKE',str(printer.call_args_list))
                self.assertFalse(self.api.published)
                self.assertEqual(atomic.main(['--task-json',str(file),'--lane',
                                              'coordination','--apply']),0)
                self.assertTrue(self.api.published)
                self.assertNotIn('TOPSECRETFAKE',str(printer.call_args_list))

    def test_local_symlink_task_refused_before_network(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'real.json';target.write_text(json.dumps(proposal()))
            link=Path(td)/'task.json';link.symlink_to(target)
            with self.assertRaisesRegex(atomic.IntakeError,'redirected'):
                atomic._read_proposed(link)

    def test_invalid_git_response_sha_fails_closed(self):
        first=self.api.request
        def bad(method,path,payload=None):
            if method=='GET' and path=='/git/commits/'+'a'*40:
                return {'sha':'a'*40,'tree':{'sha':'bad'}}
            return first(method,path,payload)
        self.api.request=bad
        with self.assertRaisesRegex(atomic.IntakeError,'SHA'):
            self.ready()


if __name__=='__main__':
    unittest.main()
