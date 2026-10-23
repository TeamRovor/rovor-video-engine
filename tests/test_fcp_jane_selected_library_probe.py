"""No-model no-app tests for strict native Jane library selection evidence."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_library_bootstrap as bootstrap
import fcp_jane_selected_library_probe as probe


class SelectedJaneNativeLibraryEvidenceTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        self.root=self.home/'Documents'/'Rovor'
        self.root.mkdir(parents=True)
        self.slug='jane-fcp-safe-20261022-a'
        self.job=self.root/(bootstrap.BOOTSTRAP_PREFIX+self.slug)
        self.job.mkdir()
        self.bundle=bootstrap.expected_library(self.job)
        self.bundle.mkdir()
        self.receipt=self.job/bootstrap.REPORT
        self.receipt.write_text(json.dumps({
            'schema_version':2,
            'status':'native_library_folder_created_app_selection_unverified',
            'target_library':str(self.bundle),
            'native_library_directory_observed':True,
            'xml_import_attempted':False,
        }))

    def test_requires_exact_jane_receipt_and_private_new_target(self):
        job,target=probe.inspect_target(self.home,self.slug)
        self.assertEqual(job,self.job)
        self.assertEqual(target,self.bundle)
        for key,value in [('status','native_library_not_observed'),
                          ('xml_import_attempted',True),
                          ('target_library','/tmp/Untitled.fcpbundle'),
                          ('native_library_directory_observed',False)]:
            original=json.loads(self.receipt.read_text())
            altered=dict(original)
            altered[key]=value
            self.receipt.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'not eligible'):
                probe.inspect_target(self.home,self.slug)
            self.receipt.write_text(json.dumps(original))

    def test_symlinks_and_missing_job_are_denied(self):
        alias=self.root/(bootstrap.BOOTSTRAP_PREFIX+'jane-fcp-symlink')
        alias.symlink_to(self.job,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'not present or redirected'):
            probe.inspect_target(self.home,'jane-fcp-symlink')
        self.bundle.rmdir()
        external=self.home/'outside'
        external.mkdir()
        self.bundle.symlink_to(external,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'missing or redirected'):
            probe.inspect_target(self.home,self.slug)

    def test_ui_parser_rejects_tainted_output_and_wrong_pid(self):
        self.assertEqual(probe.parse_ui('STATE|READY\nPID|187\nSELECTED|true'),
                         {'ui_status':'read_only_selected_row_query',
                          'pid':187,'selected_exact_row':True})
        self.assertFalse(probe.parse_ui(
            'STATE|READY\nPID|187\nSELECTED|false')['selected_exact_row'])
        for raw in ('STATE|READY\nPID|0\nSELECTED|true',
                    'STATE|READY\nPID|187\nSELECTED|true\nPRIVATE|project',
                    'STATE|READY\nPID|187\nSELECTED|TRUE',
                    'STATE|READY\nPID|abc\nSELECTED|true',
                    'Window name: Secret Client'):
            with self.subTest(raw=raw):
                self.assertEqual(probe.parse_ui(raw)['ui_status'],
                                 'invalid_response')
                self.assertFalse(probe.parse_ui(raw)['selected_exact_row'])

    def test_osx_ui_error_states_are_fail_closed(self):
        for status in ('AX_FAILED','APP_MISSING','NOT_FRONTMOST',
                       'SHEET_PRESENT','UI_BUDGET_EXCEEDED','NO_WINDOW'):
            response=probe.parse_ui('STATE|'+status)
            self.assertFalse(response['selected_exact_row'])
            self.assertEqual(response['ui_status'],status.lower())

    def test_lsof_needs_matching_process_and_exact_native_db_name(self):
        db=self.bundle/'CurrentVersion.flexolibrary'
        positive='p187\nn'+str(db)+'\n'
        self.assertTrue(probe.has_native_handle(positive,self.bundle,187))
        for raw in ('p123\nn'+str(db),
                    'p187\nn/tmp/Untitled.fcpbundle/CurrentVersion.flexolibrary',
                    'p187\nn'+str(self.bundle/'secret.mov'),
                    'p187\nn'+str(self.bundle/'Original Media'/'CurrentVersion.fcpevent'),
                    'p187\nn'+str(self.bundle/'CurrentVersion.flexolibrary.bak'),
                    'p187\nn'+str(self.bundle/'../Untitled.fcpbundle/CurrentVersion.fcpevent'),
                    'p187\np187\nn'+str(db)):
            with self.subTest(raw=raw):
                self.assertFalse(probe.has_native_handle(raw,self.bundle,187))

    def test_positive_requires_exact_selected_row_plus_native_db_handle(self):
        def yes_ui(name):
            self.assertEqual(name,self.bundle.stem)
            return {'ui_status':'read_only_selected_row_query',
                    'selected_exact_row':True,'pid':187}
        def yes_handle(pid,path):
            self.assertEqual(pid,187)
            self.assertEqual(path,self.bundle)
            return {'handle_status':'checked_read_only','native_db_handle':True}
        out=probe.verify(self.home,self.slug,ui=yes_ui,handles=yes_handle)
        self.assertTrue(out['native_library_app_selected_verified'])
        self.assertEqual(out['status'],'selected_library_evidence_observed')
        self.assertFalse(out['timeline_or_import_verified'])
        self.assertTrue(out['no_xml_import_or_app_changes'])
        self.assertNotIn('Untitled.fcpbundle',json.dumps(out))

    def test_never_queries_file_handles_for_unselected_ui(self):
        def no_ui(name):
            return {'ui_status':'not_frontmost','selected_exact_row':False}
        def no_handle(*args):
            self.fail('lsof must never run when no selected row')
        out=probe.verify(self.home,self.slug,ui=no_ui,handles=no_handle)
        self.assertEqual(out['status'],'selection_unverified')
        self.assertFalse(out['native_library_app_selected_verified'])
        self.assertEqual(out['handle_status'],'not_queried')

    def test_native_db_handle_absent_is_not_active_selection_proof(self):
        out=probe.verify(
            self.home,self.slug,
            ui=lambda _: {'ui_status':'read_only_selected_row_query',
                          'selected_exact_row':True,'pid':91},
            handles=lambda *_: {'handle_status':'checked_read_only',
                                 'native_db_handle':False},
        )
        self.assertFalse(out['native_library_app_selected_verified'])
        self.assertTrue(out['selected_exact_row'])
        self.assertFalse(out['native_db_handle'])

    def test_ui_and_lsof_executors_do_not_launch_or_modify_final_cut(self):
        calls=[]
        def fake(cmd,**kwargs):
            calls.append((cmd,kwargs))
            if cmd[0]=='/usr/bin/osascript':
                source=cmd[2].lower()
                for banned in ('click ', 'keystroke', 'activate', 'open posix file',
                               'delete ', 'set selection'):
                    self.assertNotIn(banned,source)
                return subprocess.CompletedProcess(
                    cmd,0,stdout='STATE|READY\nPID|187\nSELECTED|true',stderr='')
            if cmd[0]=='/usr/sbin/lsof':
                return subprocess.CompletedProcess(
                    cmd,0,stdout='p187\nn'+str(
                        self.bundle/'CurrentVersion.flexolibrary')+'\n',stderr='')
            self.fail('Unexpected executable')
        ui=probe.ui_query(self.bundle.stem,run=fake)
        handles=probe.native_handle_query(ui['pid'],self.bundle,run=fake)
        self.assertTrue(ui['selected_exact_row'])
        self.assertTrue(handles['native_db_handle'])
        self.assertEqual(len(calls),2)
        self.assertNotIn('/bin/sh',str(calls))

    def test_private_osascript_stderr_and_other_open_paths_not_reported(self):
        secret='Confidential Client Wedding Name'
        def bad_ui(cmd,**kw):
            return subprocess.CompletedProcess(
                cmd,1,stdout='',stderr='Error '+secret)
        self.assertEqual(probe.ui_query('ROVOR-Jane-Isolated-test',run=bad_ui),
                         {'ui_status':'denied_or_failed','selected_exact_row':False})
        def lsof_other(cmd,**kw):
            return subprocess.CompletedProcess(
                cmd,0,stdout='p187\nn/Users/Someone/Secret/'+secret+'.fcpevent\n',
                stderr='')
        self.assertFalse(probe.native_handle_query(
            187,self.bundle,run=lsof_other)['native_db_handle'])
        self.assertNotIn(secret,json.dumps(probe.verify(
            self.home,self.slug,
            ui=lambda _: {'ui_status':'read_only_selected_row_query',
                          'selected_exact_row':True,'pid':187},
            handles=lambda *_: probe.native_handle_query(
                187,self.bundle,run=lsof_other))))

    def test_timeout_or_missing_osascript_never_claims_selected(self):
        def timeout(cmd,**kw):
            raise subprocess.TimeoutExpired(cmd,2)
        self.assertFalse(probe.ui_query('ROVOR-Jane',run=timeout)['selected_exact_row'])
        self.assertFalse(probe.native_handle_query(
            187,self.bundle,run=timeout)['native_db_handle'])

    def test_no_untrusted_job_name_path_or_root_escape(self):
        for slug in ('../outside','Jane Upper','x','../../Untitled'):
            with self.subTest(slug=slug):
                with self.assertRaisesRegex(ValueError,'Invalid bounded'):
                    probe.inspect_target(self.home,slug)


if __name__=='__main__':
    unittest.main()
