"""One-pass Jane library work: bounded once-only host operation and no XML."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_library_onepass as worker
import fcp_jane_library_bootstrap as native


class JaneOnepassTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.home = Path(td.name)
        self.base = self.home / 'Documents' / 'Rovor'
        self.base.mkdir(parents=True)
        self.ident = 'jane-lib-isolation-a1'
        self.dir = self.base / ('fcp-jane-library-' + self.ident)

    def ui_ready(self):
        return {'ui_status':'read_only_menu_inspection','app':'RUNNING',
                'windows':2,'sheets':0,'file_menu':'true','new_menu':'true',
                'library_menu':'false','frontmost':'false',
                'ui_controls_used':False}

    def test_dry_run_no_path_created(self):
        out=worker.onepass(self.home,self.ident,ui_read=self.ui_ready)
        self.assertEqual(out['status'],'dry_run_only')
        self.assertFalse(self.dir.exists())
        self.assertFalse(out['xml_import_attempted'])
        self.assertFalse(out['native_gui_attempted'])

    def test_true_one_shot_creates_and_never_replays(self):
        count = {'create':0}
        def fake_create(output, report):
            count['create'] += 1
            target=Path(report['target_library'])
            target.mkdir()
            native.checkpoint(output,report,
                'native_library_folder_created_app_selection_unverified',
                native_library_created=True,
                native_library_directory_observed=True,
                last_ui_stage='save_click_dispatched')
            return report
        one = worker.onepass(self.home,self.ident,create=True,
                             ui_read=self.ui_ready,create_native=fake_create)
        self.assertEqual(one['status'],'library_created_app_selection_unverified')
        self.assertTrue(one['target_library_exists'])
        self.assertTrue(one['target_library'].endswith(
            native.unique_library_name(self.dir)+'.fcpbundle'))
        self.assertFalse(one['native_library_app_selected_verified'])
        self.assertFalse(one['xml_import_attempted'])
        two = worker.onepass(self.home,self.ident,create=True,
                             ui_read=lambda: self.fail('No second UI call'),
                             create_native=lambda *a: self.fail('No replay'))
        self.assertEqual(two['status'],'previous_job_observed_no_retry')
        self.assertEqual(count['create'],1)

    def test_preflight_refuses_when_app_not_running(self):
        d=self.ui_ready()
        d['app']='MISSING'
        result=worker.onepass(self.home,self.ident,create=True,ui_read=lambda:d)
        self.assertEqual(result['status'],'native_ui_preflight_failed_no_job_created')
        self.assertFalse(self.dir.exists())

    def test_closed_submenu_false_does_not_block(self):
        def deny_create(output, report):
            return native.checkpoint(output,report,
               'ui_create_failed_unverified',
               error_class='menu_preflight',
               last_ui_stage='opening_new_submenu',
               apple_error_number=-2700) or report
        result=worker.onepass(self.home,self.ident,create=True,
                              ui_read=self.ui_ready,create_native=deny_create)
        self.assertEqual(result['status'],'library_bootstrap_not_verified')
        self.assertTrue(self.dir.exists())
        self.assertFalse(result['xml_import_attempted'])

    def test_failed_job_not_replayed(self):
        def fail_create(output,report):
            native.checkpoint(output,report,'ui_create_failed_unverified',
                              last_ui_stage='opening_file_menu')
            return report
        first=worker.onepass(self.home,self.ident,create=True,
                             ui_read=self.ui_ready,create_native=fail_create)
        self.assertEqual(first['status'],'library_bootstrap_not_verified')
        second=worker.onepass(self.home,self.ident,create=True,
                              ui_read=lambda:self.fail('never inspect twice'))
        self.assertEqual(second['status'],'previous_job_observed_no_retry')
        self.assertEqual(second['previous_status'],'ui_create_failed_unverified')

    def test_incomplete_job_refused_not_replayed(self):
        self.dir.mkdir()
        x=worker.onepass(self.home,self.ident,create=True,
                         ui_read=lambda:self.fail('no UI'))
        self.assertEqual(x['status'],'existing_job_without_valid_receipt_no_retry')
        self.assertFalse(x['native_gui_attempted_again'])

    def test_reject_traversal_and_symlink(self):
        for name in ('../../foo','UPPER','bad name','x','ab/xyz'):
            with self.assertRaisesRegex(ValueError,'Job ID'):
                worker.path_for(self.base,name)
        protected = self.home/'private'
        protected.mkdir()
        self.dir.symlink_to(protected,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'unsafe'):
            worker.path_for(self.base,self.ident)

    def test_existing_library_mtime_not_attributed_to_job(self):
        old=self.home/'Movies'/'Untitled.fcpbundle'
        old.mkdir(parents=True)
        def create(output, report):
            import os
            old.touch()
            native.checkpoint(output,report,'ui_create_failed_unverified')
            return report
        result=worker.onepass(self.home,self.ident,create=True,
                              ui_read=self.ui_ready,create_native=create)
        self.assertTrue(result['preexisting_untitled_library_present'])
        self.assertFalse(result['native_library_app_selected_verified'])
        self.assertFalse(result['xml_import_attempted'])

    def test_library_input_not_from_failed_oct22_job(self):
        def noop(output, report):
            native.checkpoint(output,report,'ui_create_failed_unverified')
            return report
        x=worker.onepass(self.home,self.ident,create=True,
                         ui_read=self.ui_ready,create_native=noop)
        receipt=json.loads((self.dir/native.REPORT).read_text())
        self.assertIsNone(receipt['prior_job'])
        self.assertEqual(receipt['schema_version'],2)


if __name__=='__main__':
    unittest.main()
