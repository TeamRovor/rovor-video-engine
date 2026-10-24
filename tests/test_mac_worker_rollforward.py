"""No-network dry-run and rollback checks for the one-service Mac upgrade."""
import json
from pathlib import Path
import plistlib
import sqlite3
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import mac_worker_rollforward as module

SHA = "1" * 40


class MockResult:
    def __init__(self, stdout="", rc=0):
        self.stdout = stdout
        self.returncode = rc


class UpgradeChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve() / "home"
        self.base = self.home / "Documents" / "Rovor"
        self.base.mkdir(parents=True)
        self.state = self.home / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"
        self.state.mkdir(parents=True, mode=0o700)
        self.state.chmod(0o700)
        conn = sqlite3.connect(str(self.state / "jobs.sqlite3"))
        conn.execute("CREATE TABLE jobs(id TEXT, status TEXT)")
        conn.commit()
        conn.close()
        self.runtime = self.base / ("worker-runtime-" + SHA[:12])
        (self.runtime / "tools").mkdir(parents=True)
        for name in ("ghost_worker_loop.py", "omniroute_workpack_runner.py",
                     "ghost_omniroute_feed.py"):
            (self.runtime / "tools" / name).write_text("# safe test")
        self.old = self.base / ("worker-runtime-" + "0" * 12)
        (self.old / "tools").mkdir(parents=True)
        (self.old / "tools/ghost_worker_loop.py").write_text("# old runtime")
        self.python = self.home / "python3"
        self.python.write_text("stub")
        self.python.chmod(0o700)
        self.plist = self.home / "Library" / "LaunchAgents" / module.PLIST
        self.plist.parent.mkdir(parents=True)
        self.orig = {
            "Label": module.LABEL,
            "ProgramArguments": [str(self.python), str(self.old / "tools/ghost_worker_loop.py"),
                                 "--state", str(self.state), "--workspace", str(self.base),
                                 "run", "--worker-id", "rovor-launchd-approved-drafts",
                                 "--max-jobs", "1", "--max-seconds", "2",
                                 "--poll-seconds", "2",
                                 "--approve-omniroute-model-use",
                                 "--approve-omniroute-work-plan"],
            "RunAtLoad": True,
            "KeepAlive": False,
            "StartInterval": 300,
        }
        self.plist.write_bytes(plistlib.dumps(self.orig))
        self.calls = []

    def fake_run(self, argv, **kwargs):
        self.calls.append(argv)
        if argv[:3] == ["git", "-C", str(self.runtime)]:
            if argv[-1] == "HEAD": return MockResult(SHA)
            return MockResult()
        return MockResult()

    def inspect(self):
        return module.inspect(self.home, self.runtime, SHA,
                              platform="darwin", uid=lambda: 501, run=self.fake_run)

    def test_existing_python_symlink_is_preserved(self):
        target = self.home / "python-binary"
        target.write_text("stub")
        target.chmod(0o700)
        self.python.unlink()
        self.python.symlink_to(target)
        info = self.inspect()
        self.assertEqual(info["replacement"]["ProgramArguments"][0], str(self.python))

    def test_read_only_finds_loaded_existing_schedule_without_modifying_it(self):
        baseline = self.plist.read_bytes()
        info = self.inspect()
        self.assertEqual(info["replacement"]["ProgramArguments"][1],
                         str(self.runtime / "tools/ghost_worker_loop.py"))
        self.assertEqual(info["original"], self.orig)
        self.assertEqual(self.plist.read_bytes(), baseline)
        self.assertFalse((self.state / "STOP").exists())

    def test_new_recovery_plan_is_separate_explicit_mac_upgrade_opt_in(self):
        untouched=self.inspect()
        self.assertNotIn("--approve-omniroute-recovery-plan",
                         untouched["replacement"]["ProgramArguments"])
        candidate=module.inspect(self.home,self.runtime,SHA,
                                 platform="darwin",uid=lambda:501,
                                 run=self.fake_run,approve_recovery=True)
        arguments=candidate["replacement"]["ProgramArguments"]
        self.assertEqual(arguments.count("--approve-omniroute-recovery-plan"),1)
        self.assertNotIn("--approve-omniroute-recovery-plan",
                         self.orig["ProgramArguments"])
        self.assertEqual(arguments[0],self.orig["ProgramArguments"][0])

    def test_parallel_rollforward_is_an_explicit_separate_approval(self):
        normal = self.inspect()
        self.assertNotIn("--parallel-omniroute-workers",
                         normal["replacement"]["ProgramArguments"])
        parallel = module.inspect(self.home, self.runtime, SHA,
                                  platform="darwin", uid=lambda: 501,
                                  run=self.fake_run, approve_parallel=True)
        args = parallel["replacement"]["ProgramArguments"]
        self.assertEqual(args[args.index("--max-jobs") + 1], "3")
        self.assertEqual(args[-2:], ["--parallel-omniroute-workers", "3"])
        self.assertEqual(self.orig["ProgramArguments"][
            self.orig["ProgramArguments"].index("--max-jobs") + 1], "1")

    def test_fourteen_daily_free_research_calls_need_separate_approval(self):
        with self.assertRaisesRegex(module.Blocked, "higher_daily_budget_requires_parallel_approval"):
            module.inspect(self.home,self.runtime,SHA,platform="darwin",
                           uid=lambda:501,run=self.fake_run,
                           approve_free_budget=True)
        info=module.inspect(self.home,self.runtime,SHA,platform="darwin",
                            uid=lambda:501,run=self.fake_run,
                            approve_parallel=True,approve_free_budget=True)
        args=info["replacement"]["ProgramArguments"]
        self.assertEqual(args[args.index("--max-omniroute-claims-per-day")+1],"14")
        self.assertEqual(args[args.index("--max-jobs")+1],"3")

    def test_bad_checkout_and_existing_stop_are_refused(self):
        with self.assertRaisesRegex(module.Blocked, "candidate_name_not_isolated"):
            module.inspect(self.home, self.runtime, "2" * 40, platform="darwin",
                           uid=lambda: 501, run=self.fake_run)
        (self.state / "STOP").write_text("owner")
        with self.assertRaisesRegex(module.Blocked, "owner_stop_present"):
            self.inspect()

    def test_failed_new_bootstrap_restores_old_service_with_stop_held(self):
        info = self.inspect()
        def fail_new(argv, **kwargs):
            if argv[:2] == ["/bin/launchctl", "bootstrap"]:
                if argv[-1] == str(self.plist) and plistlib.loads(
                        self.plist.read_bytes())["ProgramArguments"][1].startswith(str(self.runtime)):
                    return MockResult(rc=1)
            return MockResult()
        with self.assertRaisesRegex(module.Blocked, "candidate_launch_not_verified"):
            module.rollforward(info, run=fail_new)
        self.assertEqual(plistlib.loads(self.plist.read_bytes()), self.orig)
        self.assertTrue((self.state / "STOP").is_file())
        self.assertTrue(self.plist.with_name(
            self.plist.name+".pre-rollforward-to-"+self.runtime.name).exists())

    def test_existing_legacy_backup_does_not_block_revision_scoped_rollforward(self):
        legacy = self.plist.with_name(self.plist.name + ".pre-rollforward")
        legacy.write_bytes(b"PREVIOUS_VALID_OWNER_BACKUP")
        info = self.inspect()
        result = module.rollforward(info, run=lambda argv, **kwargs: MockResult())
        self.assertEqual(result["status"], "new_candidate_loaded_existing_label")
        self.assertEqual(legacy.read_bytes(), b"PREVIOUS_VALID_OWNER_BACKUP")
        newer = self.plist.with_name(
            self.plist.name + ".pre-rollforward-to-" + self.runtime.name)
        self.assertTrue(newer.is_file())
        self.assertEqual(plistlib.loads(newer.read_bytes()), self.orig)

    def test_active_wal_safe_snapshot_without_pausing_worker_database(self):
        database = self.state / "jobs.sqlite3"
        with sqlite3.connect(str(database)) as writer:
            self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0],
                             "wal")
            writer.execute("PRAGMA wal_autocheckpoint=0")
            writer.execute("INSERT INTO jobs(id,status) VALUES(?,?)",
                           ("idle-job", "needs_review"))
            writer.commit()
            self.assertTrue((self.state / "jobs.sqlite3-wal").exists())
            self.assertTrue((self.state / "jobs.sqlite3-shm").exists())
            self.assertTrue(module.state_snapshot(self.state))
            self.assertFalse((self.state / "STOP").exists())

    def test_running_job_still_blocks_upgrading_even_in_wal_mode(self):
        database = self.state / "jobs.sqlite3"
        with sqlite3.connect(str(database)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("INSERT INTO jobs(id,status) VALUES(?,?)",
                           ("active", "running"))
            writer.commit()
            with self.assertRaisesRegex(module.Blocked, "active_jobs_present"):
                module.state_snapshot(self.state)

    def test_success_swaps_one_path_preserving_other_flags(self):
        info = self.inspect()
        output = module.rollforward(info, run=lambda argv, **kwargs: MockResult())
        self.assertEqual(output["status"], "new_candidate_loaded_existing_label")
        self.assertFalse((self.state / "STOP").exists())
        new = plistlib.loads(self.plist.read_bytes())
        self.assertEqual(new["ProgramArguments"][0], self.orig["ProgramArguments"][0])
        self.assertEqual(new["ProgramArguments"][2:], self.orig["ProgramArguments"][2:])
        self.assertEqual(new["ProgramArguments"][1],
                         str(self.runtime / "tools/ghost_worker_loop.py"))
        self.assertFalse(output["unattended_model_execution_verified"])


if __name__ == "__main__":
    unittest.main()
