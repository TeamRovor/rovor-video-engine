import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import task_routing_pair as intake


def task(ident, status='ready', scopes=None, owner=None, depends=None):
    t = dict(id=ident, title=ident, priority=1, status=status,
             owner=owner, branch='feature/paired-test',
             scopes=scopes or ['src/' + ident],
             depends_on=depends or [], next_action='Do bounded work',
             acceptance='Pass tests')
    if status in {'active', 'blocked'}:
        t.update(updated_at=datetime.now(timezone.utc).isoformat(),
                 next_update='After tests')
    if status == 'blocked':
        t['blocker'] = 'test-only missing host'
    return t


class TaskRoutingPairTests(unittest.TestCase):
    def setUp(self):
        self.queue = {'version':1, 'tasks':[]}
        self.routing = {'version':1, 'tasks':{}}

    def test_valid_ready_pair_is_exact_and_no_input_mutation(self):
        before = (copy.deepcopy(self.queue), copy.deepcopy(self.routing))
        q, r = intake.prepare_pair(self.queue, self.routing, task('new'),
                                   'coordination', ['hosted-ci'])
        self.assertEqual((self.queue, self.routing), before)
        self.assertEqual(q['tasks'][0]['id'], 'new')
        self.assertEqual(r['tasks']['new'], {
            'lane':'coordination','requires':['hosted-ci']})
        intake.validate_pair(q, r)

    def test_valid_active_claim_preserves_exact_owner(self):
        t = task('mine', status='active', owner='exact-session')
        q, r = intake.prepare_pair(self.queue,self.routing,t,'efficiency',[])
        self.assertEqual(q['tasks'][0]['owner'],'exact-session')
        self.assertEqual(r['tasks']['mine']['lane'],'efficiency')

    def test_duplicate_task_rejected(self):
        first, routing = intake.prepare_pair(self.queue,self.routing,
                                             task('duplicate'),'sales',[])
        with self.assertRaisesRegex(ValueError,'already exists'):
            intake.prepare_pair(first,routing,task('duplicate'),'sales',[])

    def test_missing_previous_mapping_rejected(self):
        self.queue['tasks'].append(task('old'))
        with self.assertRaisesRegex(ValueError,'Routing mismatch'):
            intake.prepare_pair(self.queue,self.routing,task('new'),
                                'operations',[])

    def test_unknown_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError,'unknown dependency'):
            intake.prepare_pair(self.queue,self.routing,
                                task('new',depends=['nonexistent']),
                                'integration',[])

    def test_overlapping_active_scope_rejected(self):
        self.queue['tasks'].append(task('busy',status='active',
                                         owner='other',scopes=['src/rig']))
        self.routing['tasks']['busy'] = {'lane':'animation','requires':[]}
        with self.assertRaisesRegex(ValueError,'overlapping claims'):
            intake.prepare_pair(self.queue,self.routing,
                                task('new',status='active',owner='another',
                                     scopes=['src/rig/face.py']),
                                'animation',[])

    def test_invalid_lane_and_capability_rejected(self):
        for lane, caps in [('invalid',[]),('integration',['unknown']),
                           ('operations',['hosted-ci','hosted-ci'])]:
            with self.subTest(lane=lane,caps=caps):
                with self.assertRaises(ValueError):
                    intake.prepare_pair(self.queue,self.routing,
                                        task('new'),lane,caps)

    def test_new_done_claim_rejected(self):
        with self.assertRaisesRegex(ValueError,'must be ready or actively claimed'):
            intake.prepare_pair(self.queue,self.routing,task('done',status='done'),
                                'delivery',[])

    def create_repo(self):
        t = tempfile.TemporaryDirectory()
        root = Path(t.name)
        (root / 'coordination').mkdir()
        (root / intake.TASKS).write_text(json.dumps(self.queue)+'\n',encoding='utf-8')
        (root / intake.ROUTING).write_text(json.dumps(self.routing)+'\n',encoding='utf-8')
        def git(*args):
            return subprocess.run(['git','-C',str(root),*args],
                                  check=True,capture_output=True,text=True)
        git('init')
        git('add','.')
        git('-c','user.name=Test','-c','user.email=test@example.com',
            'commit','-m','fixture')
        return t, root

    def test_clean_local_apply_prepares_both_tracked_files(self):
        with tempfile.TemporaryDirectory() as td:
            pass
        handle, root = self.create_repo()
        try:
            q,r = intake.prepare_pair(self.queue,self.routing,task('new'),
                                      'coordination',[])
            old = intake.read_pair(root)[2]
            intake.apply_pair(root,old,q,r)
            q2,r2,_ = intake.read_pair(root)
            intake.validate_pair(q2,r2)
            self.assertEqual(q2['tasks'][0]['id'],'new')
            self.assertEqual(r2['tasks']['new']['lane'],'coordination')
            changed = subprocess.run(['git','-C',str(root),'diff','--name-only'],
                                     capture_output=True,text=True,check=True)
            self.assertEqual(set(changed.stdout.splitlines()),
                             {intake.TASKS, intake.ROUTING})
        finally:
            handle.cleanup()

    def test_dirty_checkout_refuses_without_overwriting(self):
        handle,root = self.create_repo()
        try:
            q,r = intake.prepare_pair(self.queue,self.routing,task('new'),
                                      'coordination',[])
            old = intake.read_pair(root)[2]
            marker = (root / intake.TASKS)
            marker.write_text(marker.read_text()+'\n',encoding='utf-8')
            saved=marker.read_bytes()
            with self.assertRaisesRegex(ValueError,'clean tracked checkout'):
                intake.apply_pair(root,old,q,r)
            self.assertEqual(marker.read_bytes(),saved)
            self.assertEqual(json.loads((root/intake.ROUTING).read_text()),self.routing)
        finally:
            handle.cleanup()

    def test_symlinked_routing_refuses(self):
        handle,root = self.create_repo()
        try:
            external = root/'external.json'
            external.write_text('protected')
            target = root/intake.ROUTING
            target.unlink()
            target.symlink_to(external)
            with self.assertRaisesRegex(ValueError,'redirected'):
                intake.read_pair(root)
            self.assertEqual(external.read_text(),'protected')
        finally:
            handle.cleanup()

    def test_check_cli_and_dry_run_do_not_write(self):
        handle,root = self.create_repo()
        try:
            old=intake.read_pair(root)[2]
            self.assertEqual(intake.main(['--repo',str(root),'--check']),0)
            payload = root/'proposed-task.json'
            payload.write_text(json.dumps(task('new')))
            self.assertEqual(intake.main(['--repo',str(root),'--task-json',
                                          str(payload),'--lane','coordination']),0)
            self.assertEqual(intake.read_pair(root)[2],old)
        finally:
            handle.cleanup()


if __name__ == '__main__':
    unittest.main()
