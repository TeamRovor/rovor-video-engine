"""Offline regression tests for the read-only workflow inventory."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "tools" / "workflow_inventory.py"
spec = importlib.util.spec_from_file_location("workflow_inventory", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InventoryTests(unittest.TestCase):
    def test_schedule_and_scoped_permissions(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "rovor-autonomous-discovery.yml"
            p.write_text("""name: Test
on:
  schedule:
    - cron: '17 * * * *'
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: diagnostic
jobs:
  run:
    permissions:
      contents: write
""")
            result = module.inventory(Path(root))
            self.assertEqual(result["workflow_count"], 1)
            self.assertEqual(result["schedule_count"], 1)
            self.assertEqual(result["scheduled_workflows"], [p.name])
            self.assertEqual(result["requires_review"], [])
            self.assertEqual(result["workflows"][0]["top_level_permissions"], ["contents: read"])
            self.assertTrue(result["workflows"][0]["has_top_level_concurrency"])

    def test_dispatched_cron_requires_review(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "ghost-cloud-github-scheduler.yml"
            p.write_text("""on:
  schedule:
    - cron: "*/5 * * * *"
jobs:
  shift:
    runs-on: ubuntu-latest
""")
            self.assertEqual(module.inventory(Path(root))["requires_review"], [p.name])

    def test_manual_legacy_is_not_scheduled(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root) / "ghost-cloud-github-scheduler.yml"
            p.write_text("on:\n  workflow_dispatch:\npermissions:\n  contents: read\n")
            r = module.inventory(Path(root))
            self.assertEqual(r["schedule_count"], 0)
            self.assertEqual(r["requires_review"], [])

    def test_ignore_comments_and_non_workflow_files(self):
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "notes.txt").write_text("on:\n  schedule:\n")
            p = Path(root) / "example.yaml"
            p.write_text("# on:\n#   schedule:\non:\n  push:\njobs:\n  job:\n    runs-on: ubuntu-latest\n")
            self.assertEqual(module.inventory(Path(root))["workflows"][0]["events"], ["push"])
            self.assertEqual(module.inventory(Path(root))["workflow_count"], 1)

if __name__ == "__main__":
    unittest.main()
