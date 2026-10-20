"""GitHub-only handoff must never imply local laptop verification."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from remote_handoff import make_brief


def item(ident, state, priority=1, **kwargs):
    t = {
        "id": ident, "title": ident + " title", "priority": priority,
        "status": state, "owner": None, "branch": "main",
        "scopes": ["subsystem:" + ident], "depends_on": [],
        "next_action": ident + " next", "acceptance": "Check evidence",
    }
    t.update(kwargs)
    return t


class RemoteHandoffTests(unittest.TestCase):
    def test_ready_and_blocked_work_are_distinct(self):
        data = {"version": 1, "tasks": [
            item("ready-work", "ready"),
            item("win-check", "blocked", owner="Evan session",
                 updated_at="2026-10-19T00:00:00Z",
                 next_update="After audio", blocker="Missing original audio"),
        ]}
        brief = make_brief(data, revision="abc123")
        self.assertIn("Missing original audio", brief)
        self.assertIn("ready-work`: ready-work title", brief)
        self.assertNotIn("win-check`: win-check title", brief)
        self.assertIn("NO access to Evan's Windows laptop", brief)
        self.assertIn("abc123", brief)

    def test_dependencies_not_advertised_as_available(self):
        data = {"version": 1, "tasks": [
            item("first", "ready"),
            item("later", "ready", depends_on=["first"]),
        ]}
        brief = make_brief(data)
        section = brief.split("## Available unclaimed work", 1)[1]
        self.assertIn("first`: first title", section)
        self.assertNotIn("later`: later title", section)

    def test_invalid_queue_fails_before_report(self):
        with self.assertRaisesRegex(ValueError, "Invalid shared task queue"):
            make_brief({"version": 1, "tasks": [item("broken", "unknown")]})

    def test_table_text_escapes_pipes_and_newlines(self):
        data = {"version": 1, "tasks": [item("a", "ready", title="Two | teams\nnext")]}
        brief = make_brief(data)
        self.assertIn("Two \\| teams next", brief)


if __name__ == "__main__":
    unittest.main()
