"""Offline checks for the read-only GitHub workflow topology guard."""
import tempfile
import unittest
from pathlib import Path

from tools.workflow_topology import events_in, job_count, scan


class WorkflowTopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.wf = self.root / ".github" / "workflows"
        self.wf.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, body):
        (self.wf / name).write_text(body, encoding="utf-8")

    def test_reads_nested_and_inline_event_syntax(self):
        self.assertEqual(events_in("name: Demo\non:\n  push:\n    branches: [main]\n  workflow_dispatch:\npermissions:\n  contents: read\n"),
                         ["push", "workflow_dispatch"])
        self.assertEqual(events_in("on: [pull_request, push]\njobs: {}\n"),
                         ["pull_request", "push"])
        self.assertEqual(events_in("'on': schedule\njobs: {}\n"), ["schedule"])
        self.assertEqual(events_in("name: Test\n# schedule:\non: workflow_dispatch\n"), ["workflow_dispatch"])

    def test_nested_job_keys_are_not_jobs(self):
        body = "on: push\njobs:\n  safety:\n    steps:\n      - run: echo OK\n  report:\n    needs: safety\n"
        self.assertEqual(job_count(body), 2)

    def test_manual_legacy_diagnostic_does_not_run_a_cron(self):
        self.write("ghost-cloud-github-scheduler.yml",
                   "on:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs:\n  manual:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python3 tools/ghost_cloud_hosted_shift.py\n")
        report = scan(self.root)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["totals"]["manual"], 1)
        self.assertEqual(report["totals"]["scheduled"], 0)

    def test_rejects_reintroduced_legacy_scheduler(self):
        self.write("ghost-cloud-github-scheduler.yml",
                   "on:\n  schedule:\n    - cron: '*/5 * * * *'\npermissions:\n  contents: read\njobs:\n  shift:\n    runs-on: ubuntu-latest\n")
        report = scan(self.root)
        self.assertTrue(any("manual-only" in issue for issue in report["issues"]))

    def test_rejects_retired_shift_script_from_any_cron(self):
        self.write("unrelated-scheduled-worker.yml",
                   "on: schedule\npermissions:\n  contents: read\njobs:\n  shift:\n    steps:\n      - run: python3 tools/ghost_cloud_hosted_shift.py\n")
        report = scan(self.root)
        self.assertTrue(any("retired Site shift" in issue for issue in report["issues"]))

    def test_non_shift_schedules_are_not_forbidden(self):
        self.write("rovor-ai-workflow-factory.yml",
                   "on:\n  schedule:\n    - cron: '11 */2 * * *'\n  pull_request:\npermissions:\n  contents: read\nconcurrency:\n  group: factory\njobs:\n  validate:\n    runs-on: ubuntu-latest\n")
        report = scan(self.root)
        self.assertEqual(report["issues"], [])
        self.assertEqual(report["totals"]["scheduled"], 1)

    def test_empty_inventory_is_error(self):
        self.assertTrue(scan(self.root)["issues"])


if __name__ == "__main__":
    unittest.main()
