"""One-command Jane SQLite/GUI approval adapter tests, all operations mocked."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ghost_worker as worker
import fcp_jane_library_onepass as jane
import jane_library_worker as launcher


class JaneDurableLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.root=self.home/'Documents'/'Rovor'
        self.root.mkdir(parents=True)
        self.state=self.root/'jane-native-worker-state'
        self.slug='jane-fcp-unique-0001'

    def test_dry_run_is_inert(self):
        with mock.patch.object(jane,'onepass',return_value={
            'status':'dry_run_only','native_gui_attempted':False}) as native:
            result=launcher.execute(self.home,self.slug)
        self.assertEqual(result['status'],'dry_run_only')
        native.assert_called_once_with(self.home,self.slug,create=False)
        self.assertFalse(self.state.exists())

    def test_status_is_readonly_and_does_not_create_db(self):
        result=launcher.read_status(self.home)
        self.assertEqual(result['status'],'not_initialized')
        self.assertFalse(self.state.exists())
        self.assertTrue(result['read_only'])

    def test_authorized_one_call_targets_exact_job_not_earlier_ping(self):
        with worker.connect(self.state) as conn:
            unrelated=worker.enqueue(conn,'system.ping',{},'older',now=10)
        answer={
            'status':'library_created_app_selection_unverified',
            'target_library_exists':True,
            'native_library_app_selected_verified':False,
            'xml_import_attempted':False}
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value=answer) as native:
                res=launcher.execute(self.home,self.slug,create=True)
                second=launcher.execute(self.home,self.slug,create=True)
        self.assertEqual(res['status'],'creation_attempt_recorded')
        self.assertEqual(res['job_status'],'needs_review')
        self.assertFalse(res['native_library_app_selected_verified'])
        self.assertFalse(res['xml_import_attempted'])
        self.assertEqual(second['status'],
                         'existing_queued_work_finished_or_started_no_replay')
        native.assert_called_once()
        with worker.connect(self.state) as conn:
            other=conn.execute('SELECT status,attempts FROM jobs WHERE id=?',
                               (unrelated,)).fetchone()
            self.assertEqual(other['status'],'queued')
            self.assertEqual(other['attempts'],0)
            job=conn.execute('SELECT status,attempts,kind FROM jobs WHERE kind=?',
                             (worker.LIBRARY_KIND,)).fetchone()
            self.assertEqual(job['attempts'],1)
            self.assertEqual(job['status'],'needs_review')
        observed=launcher.read_status(self.home)
        self.assertEqual(observed['status'],'recorded')
        self.assertEqual(len(observed['jobs']),1)
        self.assertEqual(observed['jobs'][0]['native_result_status'],
                         'library_created_app_selection_unverified')

    def test_stop_prevents_new_job_enqueuing(self):
        with worker.connect(self.state):
            (self.state/'STOP').write_text('STOP')
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass') as native:
                result=launcher.execute(self.home,self.slug,create=True)
        self.assertEqual(result['status'],'stop_requested_no_queue_or_native_action')
        native.assert_not_called()
        with worker.connect(self.state) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM jobs').fetchone()[0],0)

    def test_inflight_old_job_does_not_replay_when_cli_invoked_again(self):
        with worker.connect(self.state) as conn:
            job=worker.enqueue(conn,worker.LIBRARY_KIND,
                               {'job_id':self.slug},
                               'jane-library-create:'+self.slug,now=10)
            worker.claim(conn,'lost-previous-worker',now=11,
                         jane_library_only=True,allow_jane_library_create=True,
                         jane_queue_job_id=job)
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass') as native:
                result=launcher.execute(self.home,self.slug,create=True)
        self.assertEqual(result['status'],
                         'existing_queued_work_finished_or_started_no_replay')
        self.assertEqual(result['job_status'],'running')
        native.assert_not_called()

    def test_linux_refuses_gui_before_sqlite_init(self):
        with mock.patch.object(launcher.sys,'platform','linux'):
            with self.assertRaisesRegex(ValueError,'foreground macOS'):
                launcher.execute(self.home,self.slug,create=True)
        self.assertFalse(self.state.exists())

    def test_only_approved_job_is_selected_among_multiple_jane_jobs(self):
        with worker.connect(self.state) as conn:
            older=worker.enqueue(conn,worker.LIBRARY_KIND,
                                 {'job_id':'jane-prior-job-0002'},
                                 'jane-library-create:jane-prior-job-0002',now=10)
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value={
                 'status':'library_bootstrap_not_verified',
                 'xml_import_attempted':False}) as native:
                result=launcher.execute(self.home,self.slug,create=True)
        self.assertEqual(result['job_status'],'needs_review')
        self.assertEqual(native.call_args.args[1],self.slug)
        with worker.connect(self.state) as conn:
            older_state=conn.execute('SELECT status,attempts FROM jobs WHERE id=?',
                                     (older,)).fetchone()
            self.assertEqual(tuple(older_state),('queued',0))

    def test_no_reuse_of_invalid_existing_state_or_paths(self):
        self.state.symlink_to(self.home,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Unsafe redirected'):
            launcher.read_status(self.home)
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with self.assertRaisesRegex(ValueError,'state directory may not'):
                launcher.execute(self.home,self.slug,create=True)


    def test_native_attempt_is_not_cli_success_even_when_package_observed(self):
        # A native folder is insufficient to prove the library is active in FCP.
        import io
        from contextlib import redirect_stdout
        outcomes = [
            ({'status':'creation_attempt_recorded',
              'job_status':'needs_review',
              'native_library_folder_observed':False,
              'native_library_app_selected_verified':False,
              'review_required':True},3),
            ({'status':'creation_attempt_recorded',
              'job_status':'needs_review',
              'native_library_folder_observed':True,
              'native_library_app_selected_verified':False,
              'review_required':True},3),
            ({'status':'stop_requested_no_queue_or_native_action'},2),
        ]
        for result,expected_rc in outcomes:
            with self.subTest(result=result):
                with mock.patch.object(launcher,'execute',return_value=result):
                    output=io.StringIO()
                    with redirect_stdout(output):
                        rc=launcher.main(['--job-id',self.slug,'--create'])
                self.assertEqual(rc,expected_rc)
                self.assertEqual(json.loads(output.getvalue())['status'],
                                 result['status'])

    def test_readonly_commands_retains_success_exit(self):
        import io
        from contextlib import redirect_stdout
        with mock.patch.object(launcher,'execute',return_value={
                'status':'dry_run_only','native_gui_attempted':False}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.main(['--job-id',self.slug]),0)
        with mock.patch.object(launcher,'read_status',return_value={
                'status':'not_initialized','read_only':True}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(launcher.main(['--status']),0)

    def test_launcher_native_receipt_always_review_required(self):
        receipt={'status':'library_bootstrap_not_verified',
                 'target_library_exists':False,
                 'native_library_app_selected_verified':False,
                 'xml_import_attempted':False}
        with mock.patch.object(launcher.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value=receipt):
                result=launcher.execute(self.home,self.slug,create=True)
        self.assertEqual(result['status'],'creation_attempt_recorded')
        self.assertEqual(result['job_status'],'needs_review')
        self.assertTrue(result['review_required'])
        self.assertFalse(result['native_library_folder_observed'])
        self.assertFalse(result['native_library_app_selected_verified'])


if __name__=='__main__':
    unittest.main()
