"""Reject new GitHub clocks without changing the existing Worker runtime."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("check_workflow_schedule", TOOLS / "check_workflow_schedule.py")
schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(schedule)


def baseline():
    return {"workflows": [{"file": name, "events": ["schedule"], "cron": crons}
                          for name, crons in schedule.APPROVED.items()]}


class ScheduleGuardTests(unittest.TestCase):
    def test_existing_auxiliary_clocks_allowed(self):
        self.assertEqual(schedule.validate(baseline()), [])

    def test_new_file_cannot_hide_new_dispatch_cron(self):
        report = baseline()
        report["workflows"].append({"file": "fresh-cloud-runner.yml",
                                    "events": ["schedule"], "cron": ["*/5 * * * *"]})
        self.assertTrue(schedule.validate(report))

    def test_existing_clock_change_requires_review(self):
        report = baseline()
        report["workflows"][0]["cron"] = ["* * * * *"]
        self.assertTrue(schedule.validate(report))

    def test_missing_approved_workflow_requires_review(self):
        report = baseline()
        report["workflows"].pop()
        self.assertTrue(schedule.validate(report))

    def test_schedule_without_cron_is_error(self):
        report = baseline()
        report["workflows"].append({"file": "hidden.yml", "events": ["schedule"], "cron": []})
        self.assertTrue(any("without a parsed cron" in e for e in schedule.validate(report)))

    def test_inline_schedule_mapping_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "danger.yml").write_text("on: {schedule: [{cron: '*/5 * * * *'}]}\n", encoding="utf-8")
            self.assertTrue(any("unsupported inline" in e for e in schedule.check_directory(root)[1]))

    def test_quoted_on_keys_cannot_hide_schedule(self):
        for key in ("'on'", '"on"'):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "danger.yml").write_text(
                    f"{key}:\n  schedule:\n    - cron: '*/5 * * * *'\n",
                    encoding="utf-8")
                errors = schedule.check_directory(root)[1]
                self.assertTrue(any("unsupported quoted on: key" in e for e in errors))

    def test_yaml_alias_cannot_hide_schedule(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "danger.yml").write_text(
                "events: &clock [schedule]\non: *clock\n", encoding="utf-8")
            errors = schedule.check_directory(root)[1]
            self.assertTrue(any("unsupported inline on: syntax" in e for e in errors))

    def test_duplicate_top_level_event_blocks_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "danger.yml").write_text(
                "on: push\non: workflow_dispatch\n", encoding="utf-8")
            errors = schedule.check_directory(root)[1]
            self.assertTrue(any("duplicate top-level on:" in e for e in errors))

    def test_valid_inline_manual_trigger_is_not_rejected_by_surface_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "manual.yml").write_text(
                "on: [push, workflow_dispatch]\n", encoding="utf-8")
            errors = schedule.check_directory(root)[1]
            self.assertFalse(any("unsupported" in e or "duplicate top-level" in e
                                 for e in errors))



if __name__ == "__main__":
    unittest.main()
