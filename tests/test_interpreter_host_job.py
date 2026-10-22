import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import interpreter_host_job as host


class HostJobTests(unittest.TestCase):
    def test_approval_precedes_exec(self):
        cmd = host.command('/fake/interpreter')
        self.assertLess(cmd.index('--ask-for-approval'), cmd.index('exec'))
        self.assertEqual(cmd[cmd.index('--sandbox') + 1], 'read-only')
        self.assertIn('--ignore-user-config', cmd)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', cmd)

    def test_dry_check_never_starts_model(self):
        with mock.patch.object(host.shutil, 'which', return_value='/fake'), mock.patch.object(host, 'check') as check, mock.patch.object(host.os, 'execv') as execute:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(host.main(['--check']), 0)
            check.assert_called_once()
            execute.assert_not_called()

    def test_legacy_fixed_argv_translates(self):
        with mock.patch.object(host.shutil, 'which', return_value='/fake'), mock.patch.object(host.os, 'execv', side_effect=RuntimeError('exec reached')) as execute:
            with self.assertRaisesRegex(RuntimeError, 'exec reached'):
                host.main(host.LEGACY)
            execute.assert_called_once_with('/fake', host.command('/fake'))

    def test_run_requires_model_optin_before_output(self):
        with mock.patch.object(host.shutil, 'which', return_value='/fake'), mock.patch.object(host, 'check'), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                host.main(['--run'])

    def test_existing_output_refuses_replay(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(host.shutil, 'which', return_value='/fake'), mock.patch.object(host, 'check'):
            with self.assertRaisesRegex(ValueError, 'refusing automatic replay'):
                host.main(['--run', '--approve-model-use', '--output', root])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_real_shim_process_and_adapter_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binary = root / 'interpreter'
            binary.write_text('#!' + sys.executable + '\nimport sys\nif "--help" in sys.argv:\n print("--ask-for-approval on-request --search --sandbox --ephemeral --ignore-user-config")\nelse:\n assert sys.argv[1:3] == ["--ask-for-approval", "on-request"]\n assert "--ignore-user-config" in sys.argv\n assert "read-only" in sys.argv\n assert "final-cut-pro" in sys.stdin.read()\n print("FAKE RESEARCH ONLY")\n')
            binary.chmod(0o700)
            with mock.patch.dict(os.environ, {'PATH': str(root) + os.pathsep + os.environ['PATH']}), contextlib.redirect_stdout(io.StringIO()):
                rc = host.main(['--run', '--approve-model-use', '--output', str(root / 'result')])
            import json
            receipt = json.loads((root / 'result/receipts/jane-finalcut-host-001.receipt.json').read_text())
            self.assertIn(receipt['status'], ['completed_unverified', 'needs_review'])
            self.assertTrue((root / 'result/receipts/jane-finalcut-host-001.reserved').exists())
            self.assertIn('FAKE RESEARCH ONLY', (root / 'result/receipts/jane-finalcut-host-001.answer.txt').read_text())
