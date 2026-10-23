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
    def brief(self, tasks, caps=None, rules=None, who='evan', lane='efficiency',
              fallback=False):
        if rules is None:
            rules = {t['id']: {'lane': 'efficiency', 'requires': []} for t in tasks}
        return work_brief.route({'version': 1, 'tasks': tasks}, {'version': 1, 'tasks': rules},
                               who, set(caps if caps is not None else ['github-read', 'github-write']),
                               lane, fallback_any_lane=fallback)

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

    def test_opt_in_cross_lane_fallback_when_primary_empty(self):
        rows = [task('animation'), task('operations', priority=2)]
        rules = {
            'animation': {'lane': 'animation', 'requires': []},
            'operations': {'lane': 'operations', 'requires': []}}
        default = self.brief(rows, rules=rules)
        self.assertIsNone(default['recommended'])
        selected = self.brief(rows, rules=rules, fallback=True)
        self.assertEqual(selected['recommended']['id'], 'animation')
        self.assertEqual(selected['recommended']['lane'], 'animation')
        self.assertEqual(selected['selection_mode'], 'fallback_other_lane')
        self.assertEqual([t['id'] for t in selected['alternatives']], ['operations'])

    def test_primary_lane_takes_precedence_over_fallback(self):
        rows = [task('other', priority=1), task('primary', priority=9)]
        rules = {'other': {'lane': 'animation', 'requires': []},
                 'primary': {'lane': 'efficiency', 'requires': []}}
        r = self.brief(rows, rules=rules, fallback=True)
        self.assertEqual(r['recommended']['id'], 'primary')
        self.assertEqual(r['selection_mode'], 'requested_lane')
        self.assertEqual(r['alternatives'], [])

    def test_fallback_preserves_owner_dependencies_and_capabilities(self):
        rows = [
            task('owned', status='active', owner='another'),
            task('stopped', status='blocked', owner='another', blocker='host offline'),
            task('dependent', depends_on=['owned']),
            task('private', priority=1),
            task('noaccess'),
        ]
        rules = {t['id']: {'lane': 'integration', 'requires': []} for t in rows}
        rules['private']['requires'] = ['local-exec']
        rules['noaccess']['requires'] = ['final-cut-runtime']
        r = self.brief(rows, rules=rules, fallback=True)
        self.assertIsNone(r['recommended'])
        reasons = {x['id']:x['reason'] for x in r['excluded']}
        self.assertIn('reserved by', reasons['owned'])
        self.assertIn('blocked', reasons['stopped'])
        self.assertIn('dependency', reasons['dependent'])
        self.assertIn('local-exec', reasons['private'])
        self.assertIn('final-cut-runtime', reasons['noaccess'])

    def test_fallback_resumes_only_exact_own_active_task(self):
        rows = [task('mine', status='active', owner='evan', priority=9),
                task('available', priority=1)]
        rules = {t['id']: {'lane':'operations', 'requires':[]} for t in rows}
        r = self.brief(rows, rules=rules, fallback=True)
        self.assertEqual(r['recommended']['id'], 'mine')
        self.assertEqual(r['recommended']['action'], 'resume')

    def test_routing_coverage_exposes_missing_tasks_without_guessing(self):
        rows = [task('classified'), task('missing')]
        rules = {'classified': {'lane':'efficiency', 'requires': []}}
        r = self.brief(rows, rules=rules)
        self.assertEqual(r['recommended']['id'], 'classified')
        self.assertEqual(r['routing_coverage']['routed_tasks'], 1)
        self.assertEqual(r['routing_coverage']['total_tasks'], 2)
        self.assertEqual(r['routing_coverage']['routed_unfinished'], 1)
        self.assertEqual(r['routing_coverage']['unclassified_unfinished'], ['missing'])
        self.assertTrue(any('Unclassified unfinished' in w for w in r['warnings']))

    def test_app_runtime_requires_positive_confirmation(self):
        rows = [task('blender')]
        rules = {'blender': {'lane':'integration',
                             'requires':['local-exec','blender-runtime']}}
        self.assertIsNone(self.brief(rows, rules=rules, lane='any',
                                     fallback=True)['recommended'])
        r=self.brief(rows,rules=rules,lane='any',
                     caps=['github-read','github-write','local-exec','blender-runtime'])
        self.assertEqual(r['recommended']['id'],'blender')

    def test_actual_queue_has_explicit_routes_for_every_unfinished_task(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / 'coordination/tasks.json').read_text(encoding='utf-8'))
        policy = json.loads((root / 'coordination/work-routing.json').read_text(encoding='utf-8'))
        b = work_brief.route(data, policy, 'CI coverage check',
                             {'github-read','github-write'}, 'any')
        self.assertEqual(b['routing_coverage']['unclassified_unfinished'], [])
        self.assertEqual(b['routing_coverage']['routed_tasks'],
                         b['routing_coverage']['total_tasks'])
        self.assertEqual(b['routing_coverage']['total_tasks'], len(data['tasks']))
        self.assertGreater(b['routing_coverage']['status_counts']['done'], 0)
        # The real queue may gain eligible work in the future. A new,
        # correctly routed, unclaimed task must NOT make this test fail.
        future = copy.deepcopy(data)
        future['tasks'].append(task('future-eligible-work', priority=1,
                                    scopes=['future-eligible-work']))
        future_policy = copy.deepcopy(policy)
        future_policy['tasks']['future-eligible-work'] = {
            'lane': 'coordination', 'requires': []}
        with_new = work_brief.route(future, future_policy, 'CI coverage check',
                                    {'github-read','github-write'}, 'any')
        eligible_ids = [t['id'] for t in
                        ([with_new['recommended']] if with_new['recommended'] else [])
                        + with_new['alternatives']]
        self.assertIn('future-eligible-work', eligible_ids)

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
