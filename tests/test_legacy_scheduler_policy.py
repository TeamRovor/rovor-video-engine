import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools/check_legacy_scheduler_policy.py"
spec = importlib.util.spec_from_file_location("scheduler_policy", SOURCE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

VALID = """on:
  workflow_dispatch:
    inputs:
      confirm_legacy_site_diagnostic:
  pull_request:
permissions:
  contents: read
concurrency:
  cancel-in-progress: false
jobs:
  shift:
    if: github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main' && inputs.confirm_legacy_site_diagnostic == true
    environment: rovor-hud-production
"""

class LegacySchedulerPolicyTests(unittest.TestCase):
    def test_known_safe_shape(self):
        self.assertEqual(policy.errors_for(VALID), [])

    def test_scheduled_legacy_shift_rejected(self):
        self.assertTrue(any("schedule trigger" in e for e in policy.errors_for(VALID.replace("  pull_request:", "  schedule:\n    - cron: '*/5 * * * *'\n  pull_request:"))))

    def test_unguarded_dispatch_rejected(self):
        self.assertTrue(policy.errors_for(VALID.replace("inputs.confirm_legacy_site_diagnostic == true", "true")))

    def test_external_trigger_rejected(self):
        self.assertTrue(any("external triggers" in e for e in policy.errors_for(VALID.replace("  pull_request:", "  repository_dispatch:\n  pull_request:"))))

    def test_missing_environment_rejected(self):
        self.assertTrue(policy.errors_for(VALID.replace("environment: rovor-hud-production", "")))

if __name__ == "__main__":
    unittest.main()
