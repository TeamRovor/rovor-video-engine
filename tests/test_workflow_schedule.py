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


    def test_noncanonical_yaml_on_keys_fail_closed(self):
        # All these are accepted by YAML but invisible to the simple
        # inventory parser, so they cannot be allowed to hide new crons.
        for header in ("'on':", '"on":', "on :", " on:"):
            with self.subTest(header=header), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "shadow.yml").write_text(
                    header + "\\n  schedule:\\n    - cron: '*/5 * * * *'\\n",
                    encoding="utf-8",
                )
                self.assertTrue(any(
                    "noncanonical on: header" in error
                    for error in schedule.check_directory(root)[1]
                ))

    def test_duplicate_on_header_cannot_override_reviewed_clock(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "shadow.yaml").write_text(
                "on:\\n  pull_request:\\n'on':\\n  schedule:\\n    - cron: '*/5 * * * *'\\n",
                encoding="utf-8",
            )
            self.assertTrue(any(
                "duplicate on: trigger header" in error
                for error in schedule.check_directory(root)[1]
            ))

    def test_missing_trigger_header_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "shadow.yml").write_text("jobs:\\n  check:\\n    runs-on: ubuntu-latest\\n")
            self.assertTrue(any(
                "missing canonical on: trigger header" in error
                for error in schedule.check_directory(root)[1]
            ))


if __name__ == "__main__":
    unittest.main()
