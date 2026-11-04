import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import moho_cli_inspect as cli


class MohoCliInspector(unittest.TestCase):
    def test_runs_only_bundled_read_only_script_and_checks_requested_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project = root / 'project.moho'
            executable = root / 'Moho'
            project.write_bytes(b'not opened by the test')
            executable.write_text('#!/bin/sh\n')
            executable.chmod(0o700)
            report = {'ok': True, 'path': str(project.resolve()), 'name': 'project',
                      'width': 1920, 'height': 1080, 'fps': 60, 'startFrame': 1,
                      'endFrame': 60, 'topLayers': 1, 'totalLayers': 1, 'layers': []}

            def fake_run(argv, env, **kwargs):
                Path(env['ROVOR_MOHO_REPORT']).write_text(json.dumps(report))
                self.assertEqual(argv, [str(executable.resolve()), str(cli.INSPECTOR.resolve())])
                self.assertEqual(env['ROVOR_MOHO_PROJECT'], str(project.resolve()))
                self.assertEqual(kwargs['stdin'], cli.subprocess.DEVNULL)
                return type('Completed', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

            with patch.object(cli.subprocess, 'run', side_effect=fake_run):
                self.assertEqual(cli.inspect(project, executable), report)
            self.assertEqual(project.read_bytes(), b'not opened by the test')

    def test_refuses_wrong_project_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            project, wrong, executable = root / 'a.moho', root / 'b.moho', root / 'Moho'
            project.touch(); wrong.touch(); executable.write_text(''); executable.chmod(0o700)
            report = {'ok': True, 'path': str(wrong.resolve())}

            def fake_run(argv, env, **kwargs):
                Path(env['ROVOR_MOHO_REPORT']).write_text(json.dumps(report))
                return type('Completed', (), {'returncode': 0, 'stdout': b'', 'stderr': b''})()

            with patch.object(cli.subprocess, 'run', side_effect=fake_run):
                with self.assertRaisesRegex(ValueError, 'different project'):
                    cli.inspect(project, executable)

    def test_rejects_non_moho_or_missing_projects_before_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'project.txt'; path.touch()
            with patch.object(cli.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, 'existing .moho'):
                    cli.inspect(path)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
