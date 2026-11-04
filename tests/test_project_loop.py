from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/project_loop.py'
spec = importlib.util.spec_from_file_location('project_loop', SCRIPT)
loop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loop)
NOW = datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc)


def task(ident='one', **kwargs):
    value = dict(id=ident, title='Check something', branch='work', priority=1,
                 status='ready', owner=None, scopes=['evan-engine'], depends_on=[],
                 next_action='Use existing work', acceptance='Actual evidence')
    value.update(kwargs)
    return value


def active(ident='one', **kwargs):
    value = task(ident, status='active', owner='test/session',
                 updated_at='2026-10-20T02:40:00Z', next_update='After checks')
    value.update(kwargs)
    return value


class CoordinationTests(unittest.TestCase):
    def check(self, *tasks):
        return loop.validate({'version': 1, 'tasks': list(tasks)}, NOW)

    def test_valid_ready(self):
        self.assertEqual(self.check(task()), ([], []))

    def test_active_requires_owner_and_update(self):
        errors, _ = self.check(task(status='active'))
        self.assertTrue(any('owner' in e for e in errors))
        self.assertTrue(any('next_update' in e for e in errors))

    def test_parent_directory_overlap_even_with_same_owner(self):
        errors, _ = self.check(active(), active('two', scopes=['evan-engine/animate_evan.py']))
        self.assertTrue(any('overlapping claims' in e for e in errors))

    def test_sibling_paths_are_independent(self):
        self.assertEqual(self.check(active(scopes=['tools/a.py']), active('two', scopes=['tools/b.py'])), ([], []))

    def test_blocked_keeps_scope_reserved(self):
        errors, _ = self.check(active(status='blocked', blocker='Waiting on evidence'), active('two'))
        self.assertTrue(any('overlapping claims' in e for e in errors))

    def test_stale_claim_warns_and_stays_reserved(self):
        data = {'version': 1, 'tasks': [active(updated_at='2026-10-18T00:00:00Z'), task('two')]}
        errors, warnings = loop.validate(data, NOW)
        self.assertFalse(errors)
        self.assertTrue(warnings)
        self.assertEqual(loop.suggestions(data), [])

    def test_done_requires_structured_evidence(self):
        errors, _ = self.check(active(status='done', evidence=['passed']))
        self.assertTrue(any('evidence requires' in e for e in errors))
        complete = active(status='done', evidence=[dict(commit='abc123', platform='Linux',
            check='unittest', result='PASS', reference='CI run link or committed report')])
        self.assertEqual(self.check(complete), ([], []))

    def test_missing_and_cyclic_dependencies(self):
        self.assertTrue(any('unknown dependency' in e for e in self.check(task(depends_on=['absent']))[0]))
        self.assertTrue(any('dependency cycle' in e for e in self.check(task(depends_on=['two']), task('two', depends_on=['one']))[0]))

    def test_blocked_dependency_is_not_suggested_or_startable(self):
        data = {'version': 1, 'tasks': [task(), task('two', depends_on=['one'], scopes=['tools'])]}
        self.assertEqual([t['id'] for t in loop.suggestions(data)], ['one'])
        self.assertTrue(any('dependency is not done' in e for e in self.check(task(), active('two', depends_on=['one']))[0]))

    def test_bad_data_returns_errors_without_crashing(self):
        for value in [None, [], {}, {'version': 1, 'tasks': [None]},
                      {'version': 1, 'tasks': [task(id=[], depends_on=[{}], scopes=[{}])]},
                      {'version': 1, 'tasks': [task(status=[])]}]:
            errors, _ = loop.validate(value, NOW)
            self.assertTrue(errors)

    def test_paths_are_portable_and_normalized(self):
        for scope in ['/tmp/work', '../work', 'a//b', 'a/./b', 'C:\\work', 'C:/work', 'subsystem:', 'a/']:
            self.assertTrue(self.check(task(scopes=[scope]))[0], scope)
        self.assertFalse(loop.overlaps('evan-engine', 'evan-engine-other'))

    def test_duplicate_ids_and_invalid_priority(self):
        errors, _ = self.check(task(), task(priority=True))
        self.assertTrue(any('duplicate id' in e for e in errors))
        self.assertTrue(any('priority' in e for e in errors))

    def test_timestamp_needs_timezone_and_cannot_be_future(self):
        for date in ['2026-10-20T02:40:00', '2027-01-01T00:00:00Z']:
            self.assertTrue(self.check(active(updated_at=date))[0])

    def test_reading_git_ref_ignores_local_task_edits(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            def git(*args):
                return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)
            git('init')
            (repo / 'coordination').mkdir()
            state = repo / loop.STATE
            state.write_text(json.dumps({'version': 1, 'tasks': [task()]}), encoding='utf-8')
            git('add', '.')
            git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-m', 'fixture')
            state.write_text('{}', encoding='utf-8')
            self.assertEqual(loop.load_state(repo, 'HEAD')['tasks'][0]['id'], 'one')
            self.assertEqual(loop.load_state(repo), {})


    def test_health_summary_counts_and_recommendations(self):
        data = {'version': 1, 'tasks': [
            task('ready-a', priority=1),
            task('ready-b', priority=2, scopes=['other']),
            active('active-a', scopes=['active-zone']),
            active('blocked-a', status='blocked', blocker='Needs external input', scopes=['blocked-zone']),
            active('done-a', status='done', scopes=['done-zone'], evidence=[dict(
                commit='abc123', platform='Linux', check='unittest',
                result='PASS', reference='https://example.invalid/evidence')]),
        ]}
        summary = loop.health_summary(data)
        self.assertEqual(summary['total'], 5)
        self.assertEqual(summary['counts'], {
            'active': 1, 'blocked': 1, 'done': 1, 'ready': 2})
        self.assertEqual([item['id'] for item in summary['ready']],
                         ['ready-a', 'ready-b'])
        self.assertEqual([item['id'] for item in summary['blocked']], ['blocked-a'])


if __name__ == '__main__':
    unittest.main()
