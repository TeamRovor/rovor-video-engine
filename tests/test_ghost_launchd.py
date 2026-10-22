"""Pure-stdlib, offline generator tests; do not launch or schedule services."""
from pathlib import Path
import importlib.util
import os
import plistlib
import stat
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ghost_launchd.py"
spec = importlib.util.spec_from_file_location("ghost_launchd", SCRIPT)
launchd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launchd)


class LaunchdTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.script = self.bin / "ghost_worker_loop.py"
        self.script.write_text("# safe fixture\n")
        (self.bin / "ghost_worker.py").write_text("# safe fixture\n")
        self.python = self.root / "python3"
        self.python.write_text("fixture\n")
        self.python.chmod(0o700)

    def build(self, **kw):
        return launchd.build_plist(self.state, self.workspace, self.script, self.python, **kw)

    def test_correct_launchagent_keys(self):
        p = self.build()
        self.assertEqual(p["Label"], launchd.LABEL)
        self.assertTrue(p["RunAtLoad"])
        self.assertFalse(p["KeepAlive"])
        self.assertEqual(p["StartInterval"], 600)
        self.assertNotIn("Program", p)
        self.assertNotIn("EnvironmentVariables", p)

    def test_no_shell_interpolation_or_commands(self):
        p = self.build()
        args = p["ProgramArguments"]
        self.assertEqual(args[0], str(self.python.resolve()))
        self.assertEqual(args[1], str(self.script.resolve()))
        self.assertEqual(args[-6:], ["--max-jobs", "25", "--max-seconds", "120", "--poll-seconds", "2"])
        self.assertNotIn("-c", args)
        self.assertNotIn("/bin/sh", args)
        self.assertNotIn("/bin/bash", args)
        self.assertEqual(args[args.index("--workspace") + 1], str(self.workspace.resolve()))

    def test_fixed_readonly_adapter_no_credentials(self):
        serialized = plistlib.dumps(self.build())
        for forbidden in (b"social.publish", b"email.send", b"shell.exec", b"token", b"password"):
            self.assertNotIn(forbidden, serialized)

    def test_rejects_interval_and_duration_abuse(self):
        for params in ({"interval":299}, {"interval":3601}, {"interval":True},
                       {"max_jobs":0}, {"max_jobs":101}, {"max_jobs":True},
                       {"max_seconds":0}, {"max_seconds":241},
                       {"interval":300,"max_seconds":241}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                self.build(**params)

    def test_rejects_nested_state_and_workspace(self):
        nested = self.state / "nested"
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, "separate"):
            launchd.build_plist(self.state, nested, self.script, self.python)
        with self.assertRaisesRegex(ValueError, "separate"):
            launchd.build_plist(self.root, self.workspace, self.script, self.python)

    def test_rejects_symlink_workspace_and_script(self):
        linked = self.root / "link"
        linked.symlink_to(self.workspace, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            launchd.build_plist(self.state, linked, self.script, self.python)
        other = self.root / "other.py"
        other.symlink_to(self.script)
        with self.assertRaisesRegex(ValueError, "symlink"):
            launchd.build_plist(self.state, self.workspace, other, self.python)

    def test_private_state_required(self):
        self.state.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "private"):
            self.build()

    def test_python_executable_required(self):
        self.python.chmod(0o600)
        with self.assertRaisesRegex(ValueError, "executable"):
            self.build()

    def test_missing_worker_script_rejected(self):
        (self.bin / "ghost_worker.py").unlink()
        with self.assertRaisesRegex(ValueError, "share"):
            self.build()

    def test_generation_idempotent_never_starts_service(self):
        with patch("os.system", side_effect=AssertionError("No command should run")), \
             patch("os.spawnv", side_effect=AssertionError("No subprocess")):
            first = launchd.generate(self.state, self.workspace, self.script, self.python)
            second = launchd.generate(self.state, self.workspace, self.script, self.python)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertFalse(first["started"])
        self.assertFalse(first["installed"])
        self.assertEqual(os.stat(first["plist"]).st_mode & 0o777, 0o600)
        saved = plistlib.loads(Path(first["plist"]).read_bytes())
        self.assertEqual(saved, self.build())

    def test_existing_different_config_rejected_without_overwrite(self):
        first = launchd.generate(self.state, self.workspace, self.script, self.python)
        before = Path(first["plist"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "differs"):
            launchd.generate(self.state, self.workspace, self.script, self.python, interval=900)
        self.assertEqual(Path(first["plist"]).read_bytes(), before)

    def test_existing_plist_symlink_rejected(self):
        dest = self.state / (launchd.LABEL + ".plist")
        outside = self.root / "outside"
        outside.write_text("KEEP")
        dest.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            launchd.generate(self.state, self.workspace, self.script, self.python)
        self.assertEqual(outside.read_text(), "KEEP")

    def test_uses_private_state_for_logs(self):
        p = self.build()
        self.assertEqual(p["StandardOutPath"], str(self.state / "launchd.out.log"))
        self.assertEqual(p["StandardErrorPath"], str(self.state / "launchd.err.log"))


if __name__ == "__main__":
    unittest.main()
