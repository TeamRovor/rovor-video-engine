import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import work_brief


def task(ident='a', **kw):
    row = dict(id=ident, title=ident, priority=1, status='ready', owner=None,
               branch='feature/test', scopes=['src/' + ident], depends_on=[],
               next_action='Do one bounded thing', acceptance='Verify result')
    row.update(kw)
    if row['status'] in {'active', 'blocked'}:
        row.update(updated_at=datetime.now(timezone.utc).isoformat(), next_update='After check')
    return row


class RoutingTests(unittest.TestCase):
    def brief(self, tasks, caps=None, rules=None, who='evan', lane='efficiency'):
        if rules is None:
            rules = {t['id']: {'lane': 'efficiency', 'requires': []} for t in tasks}
        return work_brief.route({'version': 1, 'tasks': tasks}, {'version': 1, 'tasks': rules},
                               who, set(caps if caps is not None else ['github-read', 'github-write']), lane)

    def test_priority_and_tie_are_deterministic(self):
        b = self.brief([task('z'), task('b'), task('a', priority=2)])
        self.assertEqual(b['recommended']['id'], 'b')
        self.assertEqual([t['id'] for t in b['alternatives']], ['z', 'a'])

    def test_resume_own_before_new(self):
        b = self.brief([task('a'), task('b', priority=9, status='active', owner='evan')])
        self.assertEqual(b['recommended']['id'], 'b')
        self.assertEqual(b['recommended']['action'], 'resume')

    def test_no_takeover_or_blocked_resume(self):
        b = self.brief([task('a', status='active', owner='keona'),
                        task('b', status='blocked', owner='evan', blocker='missing audio')])
        self.assertIsNone(b['recommended'])

    def test_dependencies_and_overlapping_scopes(self):
        b = self.brief([task('a', status='active', owner='other', scopes=['src']),
                        task('b', depends_on=['a']), task('c')])
        self.assertIsNone(b['recommended'])

    def test_missing_capability_and_lane(self):
        rules = {'a': {'lane': 'efficiency', 'requires': ['local-exec']},
                 'b': {'lane': 'animation', 'requires': []}}
        self.assertIsNone(self.brief([task('a'), task('b')], rules=rules)['recommended'])
        b = self.brief([task('a')], caps=['github-read', 'github-write', 'local-exec'], rules=rules)
        self.assertEqual(b['recommended']['id'], 'a')

    def test_read_only_does_not_recommend_claim(self):
        self.assertIsNone(self.brief([task()], caps=['github-read'])['recommended'])

    def test_unclassified_is_not_guessed(self):
        self.assertIsNone(self.brief([task()], rules={})['recommended'])

    def test_invalid_queue_fails_closed(self):
        with self.assertRaises(ValueError):
            self.brief([task(), task()])

    def test_stale_routing_warns(self):
        b = self.brief([], rules={'missing': {'lane': 'efficiency', 'requires': []}})
        self.assertIn('missing', b['warnings'][0])

    def test_inputs_unchanged(self):
        rows = [task()]
        before = copy.deepcopy(rows)
        self.brief(rows)
        self.assertEqual(rows, before)

    def test_invalid_rule_rejected(self):
        with self.assertRaises(ValueError):
            self.brief([task()], rules={'a': {'lane': 'efficiency', 'requires': ['magic']}})

    def test_ref_uses_committed_pair_not_dirty_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'coordination').mkdir()
            for name, data in [('tasks.json', {'version': 1, 'tasks': [task()]}),
                               ('work-routing.json', {'version': 1, 'tasks': {'a': {'lane': 'efficiency', 'requires': []}}})]:
                (root / 'coordination' / name).write_text(json.dumps(data), encoding='utf-8')
            def git(*args):
                subprocess.run(['git', '-C', td, *args], check=True, capture_output=True)
            git('init')
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '-m', 'fixture')
            (root / 'coordination/tasks.json').write_text('invalid', encoding='utf-8')
            (root / 'coordination/work-routing.json').write_text('invalid', encoding='utf-8')
            cmd = [sys.executable, work_brief.__file__, '--repo', td, '--ref', 'HEAD',
                   '--participant', 'evan', '--capability', 'github-read', '--capability', 'github-write', '--json']
            out = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(json.loads(out.stdout)['recommended']['id'], 'a')
            self.assertEqual((root / 'coordination/tasks.json').read_text(), 'invalid')


if __name__ == '__main__':
    unittest.main()
