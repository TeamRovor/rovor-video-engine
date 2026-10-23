"""Jane failed isolated-library probe; GUI menu inspection is read-only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_library_failure_probe as probe
import fcp_jane_library_bootstrap as gate


class FailedBootstrapProbeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.root = self.home / 'Documents' / 'Rovor'
        self.root.mkdir(parents=True)
        self.job = self.root / 'fcp-jane-library-20261022-200846'
        self.job.mkdir()
        self.target = self.job / 'ROVOR-Jane-Isolated.fcpbundle'
        (self.job / gate.REPORT).write_text(json.dumps({
            'status': 'ui_create_failed_unverified',
            'target_library': str(self.target),
            'xml_import_attempted': False,
            'native_library_app_selected_verified': False,
            'error_code': 1,
            'error_class': 'applescript_or_accessibility'
        }))

    def test_live_failure_and_read_only_ui_classification(self):
        def fake(command, **kw):
            self.assertEqual(command[:2], ['/usr/bin/osascript','-e'])
            self.assertNotIn('click ', command[2].lower())
            self.assertNotIn('activate', command[2].lower())
            self.assertNotIn('keystroke', command[2].lower())
            self.assertNotIn('open POSIX file', command[2])
            return subprocess.CompletedProcess(command, 0, stdout=(
                'APP|RUNNING\nFRONTMOST|false\nWINDOWS|2\nSHEETS|0\n'
                'FILE_MENU|true\nNEW_MENU|true\nLIBRARY_MENU|false\n'
            ), stderr='')
        d = probe.diagnose(self.job, home=self.home, run=fake)
        self.assertEqual(d['previous_status'], 'ui_create_failed_unverified')
        self.assertFalse(d['intended_library_exists_now'])
        self.assertEqual(d['ui']['library_menu'], 'false')
        self.assertEqual(d['ui']['frontmost'], 'false')
        self.assertFalse(d['native_library_app_selected_verified'])
        self.assertFalse(d['xml_import_attempted'])
        self.assertTrue(d['no_clicks_imports_retries_or_file_writes'])

    def test_mac_denial_reported_without_logging_full_private_error(self):
        private = 'private client file super secret'
        def fake(command, **kw):
            return subprocess.CompletedProcess(command,1,stdout='',
                       stderr='Automation not authorized for ' + private +
                              ' (-1743)')
        d = probe.diagnose(self.job, home=self.home, run=fake)
        self.assertEqual(d['ui']['error_category'],
                         'macos_automation_or_accessibility_denied')
        self.assertNotIn(private, json.dumps(d))

    def test_existing_target_still_unverified_not_import_proof(self):
        self.target.mkdir()
        def fake(command, **kw):
            return subprocess.CompletedProcess(command,0,stdout='APP|MISSING',
                                               stderr='')
        d = probe.diagnose(self.job, home=self.home, run=fake)
        self.assertTrue(d['intended_library_exists_now'])
        self.assertFalse(d['native_library_app_selected_verified'])
        self.assertFalse(d['xml_import_attempted'])

    def test_bad_receipt_refused(self):
        report = self.job/gate.REPORT
        receipt = json.loads(report.read_text())
        receipt['target_library'] = '/Users/someone/real-client.fcpbundle'
        report.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'not a recognized'):
            probe.diagnose(self.job, home=self.home,
                           run=lambda *a, **k: None)

    def test_refuse_symlinked_job(self):
        alias = self.root/'fcp-jane-library-symlink'
        alias.symlink_to(self.job, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'one existing'):
            probe.diagnose(alias, home=self.home)

    def test_bounded_reply_no_sensitive_titles_or_controls(self):
        self.assertEqual(probe.parse_ui('APP|RUNNING\nEXTRA|Personal Library')
                         ['ui_status'], 'invalid_reply')
        self.assertEqual(probe.parse_ui('APP|RUNNING\nWINDOWS|9999')
                         ['ui_status'], 'invalid_reply')
        self.assertEqual(probe.parse_ui('APP|RUNNING\nWINDOWS|2\nSHEETS|1')
                         ['sheets'], 1)
        self.assertEqual(probe.parse_ui('APP|MISSING')['ui_status'],
                         'read_only_menu_inspection')

    def test_timeout_does_not_claim_ui_inspected(self):
        def timeout(command, **kw):
            raise subprocess.TimeoutExpired(command, 15)
        self.assertEqual(probe.ui_read(run=timeout)['ui_status'],
                         'query_timed_out')


if __name__ == '__main__':
    unittest.main()
