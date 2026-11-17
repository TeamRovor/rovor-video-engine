import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pr_overlap_audit import overlapping_prs, escape_warning


class OverlapTests(unittest.TestCase):
    def test_exact_file_collision_same_base(self):
        current = {"number": 455, "base": "main", "files": ["hud/live.js", "tests/a.py"]}
        others = [
            {"number": 314, "base": "main", "files": ["hud/live.js", "worker.js"]},
            {"number": 316, "base": "feature/hud", "files": ["hud/live.js"]},
            {"number": 455, "base": "main", "files": ["hud/live.js"]},
            {"number": 456, "base": "main", "files": ["worker.js"]},
        ]
        self.assertEqual(overlapping_prs(current, others), [
            {"number": 314, "paths": ["hud/live.js"]}
        ])

    def test_missing_paths_cannot_fabricate_conflicts(self):
        self.assertEqual(overlapping_prs(
            {"number": 1, "base": "main", "files": []},
            [{"number": 2, "base": "main", "files": ["x"]}]), [])
        self.assertEqual(overlapping_prs(
            {"number": 1, "base": "main", "files": ["x"]},
            [{"number": 2, "base": "main"}]), [])

    def test_sort_and_deduplicate_paths(self):
        current = {"number": 10, "base": "main", "files": ["b", "a", "a"]}
        others = [{"number": 20, "base": "main", "files": ["b", "a", "b"]},
                  {"number": 11, "base": "main", "files": ["a"]}]
        self.assertEqual(overlapping_prs(current, others), [
            {"number": 11, "paths": ["a"]},
            {"number": 20, "paths": ["a", "b"]}
        ])

    def test_warning_escaping(self):
        self.assertEqual(escape_warning("a%\nb\rc"), "a%25%0Ab%0Dc")


if __name__ == "__main__":
    unittest.main()
