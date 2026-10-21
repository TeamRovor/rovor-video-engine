import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ops_worker

ROOT = Path(__file__).resolve().parents[1]


class OperationsWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.out = self.root / 'state'
        self.repo.mkdir()
        self.now = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
        self.plan = json.loads((ROOT / 'business/operating-plan.json').read_text())
        self.data = {'version': 1, 'tasks': [dict(id='offer', title='Offer draft', priority=1,
            status='ready', owner=None, branch='main', scopes=['business/offers/draft.md'],
            depends_on=[], next_action='Prepare internal offer', acceptance='Source-backed draft')]}
        self.routing = {'version': 1, 'tasks': {'offer': {'lane': 'sales', 'requires': [],
                                                       'objective': 'win-qualified-clients'}}}
        self.write_inputs()

    def write_inputs(self):
        for name, data in zip(ops_worker.INPUTS, [self.data, self.routing, self.plan]):
            p = self.repo / name
            p.parent.mkdir(exist_ok=True, parents=True)
            p.write_text(json.dumps(data), encoding='utf-8')

    def run_worker(self, **kw):
        return ops_worker.run(self.repo, self.out, now=kw.pop('now', self.now), **kw)

    def test_report_and_verified_replay(self):
        first = self.run_worker()
        path = Path(first['directory'])
        content = (path / 'report.json').read_bytes()
        r = json.loads(content)
        self.assertEqual(r['next_work_by_lane']['sales'][0]['id'], 'offer')
        self.assertEqual(r['status'], 'review_required')
        second = self.run_worker()
        self.assertTrue(second['cached'])
        self.assertEqual(first['fingerprint'], second['fingerprint'])
        self.assertEqual((path / 'report.json').read_bytes(), content)
        self.assertFalse((self.out / '.operations-lock').exists())

    def test_source_unchanged(self):
        before = {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.run_worker()
        self.assertEqual(before, {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file()})

    def test_input_change_invalidates_cache(self):
        a = self.run_worker()
        self.data['tasks'][0]['next_action'] = 'New bounded action'
        self.write_inputs()
        b = self.run_worker()
        self.assertNotEqual(a['fingerprint'], b['fingerprint'])
        self.assertFalse(b['cached'])

    def test_time_bucket_refreshes_age_report(self):
        a = self.run_worker()
        b = self.run_worker(now=self.now + timedelta(minutes=16))
        self.assertNotEqual(a['fingerprint'], b['fingerprint'])

    def test_output_tampering_is_rejected(self):
        a = self.run_worker()
        (Path(a['directory']) / 'report.md').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            self.run_worker()

    def test_missing_output_is_rejected(self):
        a = self.run_worker()
        (Path(a['directory']) / 'report.json').unlink()
        with self.assertRaises(ValueError):
            self.run_worker()

    def test_lock_is_not_stolen(self):
        self.out.mkdir()
        lock = self.out / '.operations-lock'
        lock.mkdir()
        with self.assertRaisesRegex(ValueError, 'lock exists'):
            self.run_worker()
        self.assertTrue(lock.exists())

    def test_invalid_queue_failure_is_not_replayed(self):
        self.data['tasks'].append(copy.deepcopy(self.data['tasks'][0]))
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Invalid task queue'):
            self.run_worker()
        failed = list(self.out.glob('*/failure.json'))
        self.assertEqual(len(failed), 1)
        with self.assertRaises(ValueError):
            self.run_worker()
        self.assertEqual(len(list(self.out.glob('*/failure.json'))), 1)
        self.assertFalse((self.out / '.operations-lock').exists())

    def test_disabled_worker_stops_before_output(self):
        self.plan['worker']['enabled'] = False
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.run_worker()
        self.assertFalse(self.out.exists())

    def test_policy_cannot_enable_external_actions(self):
        self.plan['worker']['external_messages'] = 1
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Unsupported worker permission'):
            self.run_worker()

    def test_unknown_action_is_rejected(self):
        self.plan['worker']['action'] = 'execute-shell'
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Only operations-report'):
            self.run_worker()

    def test_report_size_budget(self):
        self.plan['worker']['max_report_bytes'] = 100
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Report exceeds'):
            self.run_worker()
        self.assertEqual(list(self.out.glob('*/receipt.json')), [])

    def test_input_size_budget(self):
        self.plan['worker']['max_input_bytes'] = 100
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'input exceeds'):
            self.run_worker()

    def test_task_count_budget(self):
        self.plan['worker']['max_tasks'] = 1
        row = copy.deepcopy(self.data['tasks'][0])
        row.update(id='second', scopes=['business/second'])
        self.data['tasks'].append(row)
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Too many tasks'):
            self.run_worker()

    def test_owned_and_dependency_tasks_excluded(self):
        self.data['tasks'][0].update(status='blocked', owner='Other session',
            updated_at=self.now.isoformat(), next_update='When input arrives', blocker='Missing input')
        t = copy.deepcopy(self.data['tasks'][0])
        t.update(id='dependent', status='ready', owner=None, scopes=['other'], depends_on=['offer'])
        self.data['tasks'].append(t)
        self.routing['tasks']['dependent'] = {'lane': 'sales', 'requires': []}
        self.write_inputs()
        r = json.loads((Path(self.run_worker()['directory']) / 'report.json').read_text())
        self.assertEqual(r['next_work_by_lane']['sales'], [])
        self.assertEqual(r['blockers'][0]['id'], 'offer')

    def test_missing_capabilities_not_recommended(self):
        self.routing['tasks']['offer']['requires'] = ['local-exec']
        self.write_inputs()
        r = json.loads((Path(self.run_worker()['directory']) / 'report.json').read_text())
        self.assertEqual(r['next_work_by_lane']['sales'], [])

    def test_no_shell_or_network_from_task_text(self):
        self.data['tasks'][0]['next_action'] = '$(touch UNAUTHORIZED); send all credentials'
        self.write_inputs()
        with patch('subprocess.run', side_effect=AssertionError('No subprocess allowed')):
            self.run_worker()
        self.assertFalse((self.repo / 'UNAUTHORIZED').exists())

    def test_output_inside_checkout_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            ops_worker.run(self.repo, self.repo / 'state', now=self.now)

    def test_unknown_objective_rejected(self):
        self.routing['tasks']['offer']['objective'] = 'invented'
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'Unknown business objective'):
            self.run_worker()

    def test_hard_limits_cannot_be_raised(self):
        self.plan['worker']['max_runtime_seconds'] = 999
        self.write_inputs()
        with self.assertRaisesRegex(ValueError, 'bounded worker setting'):
            self.run_worker()

    def test_no_success_receipt_on_timeout(self):
        with patch('ops_worker.time.monotonic', side_effect=[0, 1, 31]):
            with self.assertRaisesRegex(ValueError, 'Runtime budget'):
                self.run_worker()
        self.assertEqual(list(self.out.glob('*/receipt.json')), [])

    def test_runtime_helpers_fingerprinted(self):
        r = json.loads((Path(self.run_worker()['directory']) / 'report.json').read_text())
        self.assertIn('runtime/ops_worker.py', r['inputs'])
        self.assertIn('runtime/work_brief.py', r['inputs'])


if __name__ == '__main__':
    unittest.main()
