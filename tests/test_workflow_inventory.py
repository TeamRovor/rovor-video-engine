import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "workflow_inventory.py"
spec = importlib.util.spec_from_file_location("workflow_inventory", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class WorkflowInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / ".github" / "workflows"
        self.directory.mkdir(parents=True)

    def put(self, name, text):
        (self.directory / name).write_text(text, encoding="utf-8")

    def test_reports_triggers_cron_jobs_dependencies_and_scoped_permissions(self):
        self.put("shift.yml", """
name: Cloud shift tests
on:
  schedule:
    - cron: '17 * * * *'
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: cloud-tests
  cancel-in-progress: false
jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
  publish:
    needs: [verify]
    permissions:
      contents: write
    concurrency:
      group: cloud-publisher
    runs-on: ubuntu-latest
    environment: protected
    steps:
      - run: echo safe
""")
        result = audit.inventory(self.root)
        self.assertEqual(result["summary"]["workflow_count"], 1)
        self.assertEqual(result["summary"]["cron_entries"], 1)
        item = result["workflows"][0]
        self.assertEqual(item["events"], ["schedule", "workflow_dispatch"])
        self.assertEqual(item["cron"], ["17 * * * *"])
        self.assertEqual(item["permissions"], {"contents": "read"})
        self.assertEqual(item["concurrency_group"], "cloud-tests")
        self.assertEqual(item["jobs"][1]["needs"], ["verify"])
        self.assertEqual(item["jobs"][1]["permissions_override"], {"contents": "write"})
        self.assertEqual(item["jobs"][1]["concurrency_group"], "cloud-publisher")
        self.assertIn("action_refs_not_sha_pinned", item["review_flags"])
        self.assertNotIn("scheduled_without_explicit_concurrency", item["review_flags"])

    def test_manual_legacy_diagnostic_is_not_a_second_cron(self):
        self.put("legacy.yml", """name: Legacy manual only
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  diagnostic:
    runs-on: ubuntu-latest
""")
        item = audit.inventory(self.root)["workflows"][0]
        self.assertEqual(item["cron"], [])
        self.assertEqual(item["events"], ["workflow_dispatch"])

    def test_same_cron_is_an_observation_not_proof_of_duplicate_dispatch(self):
        common = "on:\n  schedule:\n    - cron: '0 * * * *'\n"
        self.put("discovery.yml", common + "permissions:\n  contents: read\n")
        self.put("qa.yaml", common + "permissions:\n  contents: read\n")
        report = audit.inventory(self.root)
        self.assertEqual(len(report["summary"]["same_cron_expressions"]["0 * * * *"]), 2)
        self.assertEqual(report["summary"]["scheduled_without_concurrency"], 2)

    def test_inline_events_and_secret_values_are_never_emitted(self):
        self.put("test.yml", """on: [push, pull_request]
permissions: read-all
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo ${{ secrets.SUPER_PRIVATE_KEY }}
""")
        item = audit.inventory(self.root)["workflows"][0]
        self.assertEqual(item["events"], ["pull_request", "push"])
        self.assertNotIn("SUPER_PRIVATE_KEY", json.dumps(item))
        self.assertEqual(item["permissions"], {"_scalar": "read-all"})

    def test_empty_workflow_folder_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no GitHub Actions workflows"):
            audit.inventory(self.root)

    def test_cli_produces_machine_readable_artifact(self):
        self.put("manual.yml", "name: Manual\non:\n  workflow_dispatch:\n")
        output = self.root / "out" / "inventory.json"
        subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root),
                        "--output", str(output)], check=True, capture_output=True)
        self.assertEqual(json.loads(output.read_text())["summary"]["workflow_count"], 1)


if __name__ == "__main__":
    unittest.main()
