"""Regression guard: one runtime CI run per PR update, main push still covered.

Standard-library only. The workflow uses literal single-line YAML path arrays,
so this deliberately validates its supported shape rather than guessing YAML.
"""
import ast
import pathlib
import re
import unittest


WORKFLOW = (pathlib.Path(__file__).resolve().parents[1] /
            ".github/workflows/ghost-cloud.yml")


class NineProviderRuntimeCIContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")
        found = re.search(r"(?ms)^on:\n(?P<body>.*?)^permissions:", cls.source)
        if not found:
            raise AssertionError("missing literal GitHub Actions trigger block")
        cls.events = found.group("body")

    def event_body(self, name):
        found = re.search(
            rf"(?ms)^  {re.escape(name)}:\n(.*?)(?=^  [a-z_]+:|\\Z)",
            self.events,
        )
        self.assertIsNotNone(found, f"missing {name} event")
        return found.group(1)

    def event_paths(self, name):
        found = re.search(r"(?m)^    paths: (\[[^\n]+\])$", self.event_body(name))
        self.assertIsNotNone(found, f"{name} lacks an explicit file allowlist")
        paths = ast.literal_eval(found.group(1))
        self.assertIsInstance(paths, list)
        return paths

    def test_only_pr_and_main_push_trigger_validation(self):
        self.assertEqual(re.findall(r"(?m)^  ([a-z_]+):", self.events),
                         ["push", "pull_request"])
        push = self.event_body("push")
        self.assertRegex(push, r"(?m)^    branches: \[main\]$")
        self.assertNotRegex(self.event_body("pull_request"), r"(?m)^    branches:")
        self.assertNotIn("schedule:", self.events)

    def test_both_triggers_cover_original_runtime_tests_and_policy(self):
        expected = [
            "integrations/ghost-cloud/**",
            "tests/test_ghost_cloud*.mjs",
            "tests/test_ghost_cloud_workflow_policy.py",
            ".github/workflows/ghost-cloud.yml",
        ]
        self.assertEqual(self.event_paths("push"), expected)
        self.assertEqual(self.event_paths("pull_request"), expected)
        self.assertIn(
            "node --test tests/test_ghost_cloud.mjs tests/test_ghost_cloud_canary_preflight.mjs",
            self.source,
        )
        self.assertIn("python3 tools/project_loop.py check", self.source)
        self.assertIn("python3 tools/task_routing_pair.py --check", self.source)

    def test_superseded_checks_cancel_without_privileged_access(self):
        self.assertIn(
            "group: nine-provider-cloud-runtime-${{ github.event.pull_request.number || github.ref }}",
            self.source,
        )
        self.assertRegex(self.source, r"(?m)^  cancel-in-progress: true$")
        self.assertRegex(self.source, r"(?m)^    timeout-minutes: 10$")
        self.assertRegex(self.source, r"(?m)^permissions:\n  contents: read$")
        self.assertIn("persist-credentials: false", self.source)
        self.assertNotIn("secrets.", self.source)
        self.assertNotIn("environment:", self.source)


if __name__ == "__main__":
    unittest.main()
