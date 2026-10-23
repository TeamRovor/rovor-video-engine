"""Jane GUI library isolation gate: no XML import under any circumstance."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_library_bootstrap as gate
import fcp_jane_native_probe as native


class NativeLibraryBootstrapTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.home = Path(td.name)
        self.root = self.home / 'Documents' / 'Rovor'
        self.root.mkdir(parents=True)
        self.job = self.root / 'fcp-jane-auto-20261022-183007'
        self.job.mkdir()
        self.prior = self.job / 'ROVOR-Jane-Test.fcpbundle'
        (self.job / native.RECEIPT_NAME).write_text(json.dumps({
            'status': 'native_library_not_observed',
            'target_library': str(self.prior),
            'last_dispatched': 'landscape',
        }))
        self.output = self.root / 'fcp-jane-library-20261022-200000'

    def prepared(self):
        return gate.prepare(self.job, self.output, home=self.home)

    def test_prepare_is_non_native_and_cannot_touch_existing_library(self):
        old = self.home / 'Movies' / 'Untitled.fcpbundle'
        old.mkdir(parents=True)
        protected = old / 'CurrentVersion.flexolibrary'
        protected.write_bytes(b'original')
        folder, receipt = self.prepared()
        self.assertEqual(receipt['status'], 'prepared_no_native_app_action')
        self.assertFalse(receipt['xml_import_attempted'])
        self.assertFalse(receipt['native_library_created'])
        self.assertFalse(receipt['existing_library_mutation_assessed'])
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        self.assertEqual(protected.read_bytes(), b'original')
        self.assertFalse(Path(receipt['target_library']).exists())

    def test_create_only_calls_new_library_ui_apple_script(self):
        output, report = self.prepared()
        cmds = []
        expected = Path(report['target_library'])
        def fake(command, **kwargs):
            cmds.append(command)
            self.assertEqual(command[:2], ['/usr/bin/osascript','-e'])
            script = command[2]
            self.assertIn('menu item "Library"', script)
            self.assertNotIn('open POSIX file', script)
            self.assertNotIn('File > Import', script)
            self.assertNotIn('import XML', script)
            self.assertEqual(command[3], str(self.output))
            self.assertEqual(command[4], gate.LIBRARY_BASENAME)
            self.assertEqual(command[5], self.output.name)
            self.assertIn('locationVerified is false', script)
            # Fake successful native app creation.
            expected.mkdir()
            return subprocess.CompletedProcess(command,0,stdout='',stderr='')
        with mock.patch.object(gate, 'APP', self.root):
            result = gate.create_library(output, report, run=fake)
        self.assertEqual(result['status'],
                         'native_library_folder_created_app_selection_unverified')
        self.assertEqual(len(cmds),1)
        self.assertTrue(result['native_library_directory_observed'])
        self.assertFalse(result['native_library_app_selected_verified'])
        self.assertFalse(result['xml_import_attempted'])

    def test_gui_refusal_never_tries_to_import_or_retry(self):
        output, report = self.prepared()
        calls = []
        def fake(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv,1,stdout='',
                                               stderr='Not authorized')
        with mock.patch.object(gate, 'APP', self.root):
            result = gate.create_library(output, report, run=fake)
        self.assertEqual(result['status'], 'ui_create_failed_unverified')
        self.assertEqual(len(calls),1)
        self.assertFalse(result['native_library_created'])
        self.assertFalse(result['xml_import_attempted'])
        persisted = json.loads((output / gate.REPORT).read_text())
        self.assertEqual(persisted['status'],'ui_create_failed_unverified')

    def test_native_automation_permission_error_is_sanitized(self):
        output, report = self.prepared()
        private = 'Confidential Project 74828'
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv,1,stdout='',
                stderr='execution error: Not authorized to control ' +
                       private + ' (-1743)')
        with mock.patch.object(gate, 'APP', self.root):
            result = gate.create_library(output, report, run=fake)
        self.assertEqual(result['error_class'], 'accessibility_permission')
        self.assertEqual(result['apple_error_number'], -1743)
        self.assertNotIn(private, json.dumps(result))
        self.assertNotIn(private, (output/gate.REPORT).read_text())
        self.assertFalse(result['xml_import_attempted'])

    def test_step_errors_do_not_leak_personal_window_names(self):
        output, report = self.prepared()
        private = 'Client 123 private film'
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv,1,stdout='',
                stderr='execution error: No File/New/Library command; ' +
                       private + ' (-2700)')
        with mock.patch.object(gate, 'APP', self.root):
            result = gate.create_library(output, report, run=fake)
        self.assertEqual(result['error_class'], 'menu_preflight')
        self.assertEqual(result['apple_error_number'], -2700)
        self.assertNotIn(private, json.dumps(result))

    def test_osascript_success_without_library_is_not_success(self):
        output, report = self.prepared()
        def fake(argv, **kw):
            return subprocess.CompletedProcess(argv,0,stdout='',stderr='')
        with mock.patch.object(gate, 'APP', self.root):
            result = gate.create_library(output, report, run=fake,
                                         clock=lambda:0, timeout=0)
        self.assertEqual(result['status'], 'native_library_not_observed')
        self.assertFalse(result['xml_import_attempted'])
        self.assertFalse(result['native_library_created'])

    def test_reused_destination_refused(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError,'never-used'):
            self.prepared()

    def test_same_previously_failed_job_cannot_be_replayed(self):
        p=self.job/native.RECEIPT_NAME
        state=json.loads(p.read_text())
        state['status']='apple_events_sent_timeline_unverified'
        p.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'confirmed original'):
            self.prepared()
        self.assertFalse(self.output.exists())

    def test_output_cannot_overlap_existing_job(self):
        with self.assertRaisesRegex(ValueError,'never-used'):
            gate.prepare(self.job,self.job/'fcp-jane-library-hijack',
                         home=self.home)


if __name__ == '__main__':
    unittest.main()
