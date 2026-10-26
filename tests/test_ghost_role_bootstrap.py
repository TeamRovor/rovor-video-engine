import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import ghost_role_bootstrap as b

DOC = json.loads((ROOT / "coordination/ghost-role-bootstrap.json").read_text())


class RoleBootstrapTest(unittest.TestCase):
    def test_manifest_and_first_role(self):
        self.assertTrue(b.validate(DOC))
        first = b.next_step(DOC, {}, "mike")
        self.assertEqual(first["dedupe_key"], "rovor-role-mike-orient-v1")
        self.assertFalse(first["external_effects"])

    def test_no_retry_after_failure_or_restart(self):
        stable = b.key("mike", "orient")
        for state in ("queued", "running", "needs_review", "failed", "rejected"):
            ledger = json.loads(json.dumps({stable: state}))
            result = b.next_step(DOC, ledger, "mike")
            self.assertTrue(result["no_retry"])
            self.assertEqual(result["status"], "waiting_" + state)

    def test_only_approved_advances(self):
        ledger = {b.key("mike", "orient"): "approved"}
        self.assertEqual(b.next_step(DOC, ledger, "mike")["stage"], "map")

    def test_stops_after_all_reviewed(self):
        ledger = {b.key("mike", s["id"]): "approved" for s in DOC["steps"]}
        self.assertEqual(b.next_step(DOC, ledger, "mike")["status"], "complete_await_reviewed_release")

    def test_other_roles_not_blocked(self):
        self.assertEqual(b.ready(DOC, {b.key("mike", "orient"): "needs_review"})[0]["role_id"], "jane")

    def test_stop_and_cap(self):
        self.assertEqual(b.ready(DOC, {}, stop=True), [])
        self.assertEqual(b.next_step(DOC, {}, "mike", stop=True)["status"], "stopped")
        with self.assertRaises(ValueError):
            b.ready(DOC, {}, limit=100)

    def test_policy_or_catalog_escalation_refused(self):
        x = copy.deepcopy(DOC)
        x["policy"]["native_app_control"] = True
        with self.assertRaises(ValueError):
            b.validate(x)
        x = copy.deepcopy(DOC)
        x["roles"].append(x["roles"][0])
        with self.assertRaises(ValueError):
            b.validate(x)
        with self.assertRaises(ValueError):
            b.next_step(DOC, {"strange": "approved"}, "mike")

    def test_stable_ids_across_text_changes(self):
        x = copy.deepcopy(DOC)
        before = b.next_step(x, {}, "mike")["dedupe_key"]
        x["roles"][0]["mission"] += " More detail."
        self.assertEqual(b.next_step(x, {}, "mike")["dedupe_key"], before)


if __name__ == "__main__":
    unittest.main()
