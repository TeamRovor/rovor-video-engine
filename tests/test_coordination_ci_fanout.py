"""Guard the single coordination-data CI owner against specialist workflow fan-out.

Workflow files are deliberately inspected as text to keep this offline,
dependency-free regression runnable on both supported Python versions.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
DATA_PATHS = ("coordination/tasks.json", "coordination/work-routing.json")
SPECIALIST_TESTS = {
    "walter-public-task-grounding.yml": "tests/test_walter_public_task_grounding.py",
    "omniroute-dispatch-permit.yml": "tests/test_omniroute_dispatch_permit.py",
    "omniroute-reasoning-admission.yml": "tests/test_omniroute_reasoning_admission.py",
    "walter-specialist-coverage.yml": "tests/test_walter_specialist_coverage.py",
    "walter-reviewed-finding-handoff.yml": "tests/test_walter_reviewed_finding_handoff.py",
    "walter-snapshot-continuity.yml": "tests/test_walter_snapshot_continuity.py",
    "walter-grounded-coverage-pipeline.yml": "tests/test_walter_grounded_coverage_pipeline.py",
    "walter-public-queue-admission.yml": "tests/test_walter_public_queue_admission.py",
    "walter-task-identity-guard.yml": "tests/test_walter_real_receipt_bridge.py",
}


def has_path_trigger(source, path):
    """Only match a YAML list item, never a command/comment/documentation."""
    return bool(re.search(r"(?m)^[ \t]*-[ \t]*['\"]?" + re.escape(path) +
                          r"['\"]?[ \t]*$", source))


class CoordinationCiFanoutTests(unittest.TestCase):
    def test_one_authoritative_queue_and_route_check_on_data_edits(self):
        source = (WORKFLOWS / "work-brief-routing-check.yml").read_text()
        for path in DATA_PATHS:
            with self.subTest(path=path):
                self.assertTrue(has_path_trigger(source, path))
        self.assertIn("pull_request:", source)
        self.assertIn("push:", source)
        self.assertIn("python tools/project_loop.py check", source)
        self.assertIn("python tools/task_routing_pair.py --check", source)
        self.assertIn("test_work_brief.py", source)
        self.assertIn("test_coordination_ci_fanout.py", source)
        self.assertNotIn("  schedule:", source)

    def test_specialist_regressions_do_not_duplicate_data_only_ci(self):
        for name, test_file in SPECIALIST_TESTS.items():
            with self.subTest(workflow=name):
                source = (WORKFLOWS / name).read_text()
                self.assertIn("pull_request:", source)
                self.assertIn("jobs:", source)
                self.assertTrue(has_path_trigger(source, test_file),
                                "specialist test edits must still trigger CI")
                self.assertNotIn("  schedule:", source)
                for path in DATA_PATHS:
                    self.assertFalse(has_path_trigger(source, path),
                                     "queue data should be checked centrally")

    def test_specialist_workflows_still_run_tests(self):
        for name in SPECIALIST_TESTS:
            with self.subTest(workflow=name):
                source = (WORKFLOWS / name).read_text()
                self.assertIn("python -m unittest discover", source)
                self.assertIn("tools/project_loop.py check", source)
                self.assertIn("tools/task_routing_pair.py --check", source)


if __name__ == "__main__":
    unittest.main()
