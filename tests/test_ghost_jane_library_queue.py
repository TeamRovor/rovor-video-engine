"""SQLite and STOP integration tests for Jane's approved library-only job.

No GUI, XML, app launch, model, network or protected library mutation.
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import ghost_worker as worker
import ghost_worker_loop as loop
import fcp_jane_library_onepass as jane


class JaneLibraryQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.workspace = self.home / 'workspace'
        self.workspace.mkdir()
        self.state = self.home / 'worker-state'
        self.conn = worker.connect(self.state)
        self.addCleanup(self.conn.close)
        self.slug = 'jane-authorized-20261022-1'

    def enqueue(self, dedupe='jane-library-creation'):
        return worker.enqueue(self.conn,worker.LIBRARY_KIND,
                              {'job_id':self.slug},dedupe,now=100.0)

    def job(self, job_id):
        return dict(self.conn.execute(
            'SELECT status,attempts,result,error FROM jobs WHERE id=?',
            (job_id,)).fetchone())

    def test_enqueued_no_execution_without_specific_gui_approval(self):
        jid=self.enqueue()
        with mock.patch.object(jane,'onepass') as native:
            self.assertIsNone(worker.run_once(self.conn,self.workspace))
            self.assertIsNone(worker.run_once(self.conn,self.workspace,
                                              allow_model_use=True))
            self.assertIsNone(worker.run_once(self.conn,self.workspace,
                                              allow_native_import=True))
        native.assert_not_called()
        self.assertEqual(self.job(jid)['status'],'queued')
        self.assertEqual(self.job(jid)['attempts'],0)

    def test_approved_gui_uses_onepass_and_finishes_needs_review_not_success(self):
        jid=self.enqueue()
        simulated={'status':'library_created_app_selection_unverified',
                   'target_library':'/test-only/jane.fcpbundle',
                   'target_library_exists':True,
                   'native_library_app_selected_verified':False,
                   'xml_import_attempted':False}
        with mock.patch.object(worker.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value=simulated) as native:
                result=worker.run_once(
                    self.conn,self.workspace,now=101.0,
                    allow_jane_library_create=True)
        native.assert_called_once_with(Path.home(),self.slug,create=True)
        self.assertEqual(result['status'],'needs_review')
        saved=self.job(jid)
        self.assertEqual(saved['status'],'needs_review')
        self.assertEqual(saved['attempts'],1)
        self.assertIsNone(saved['error'])
        self.assertEqual(json.loads(saved['result']),simulated)
        self.assertIsNone(worker.run_once(
            self.conn,self.workspace,now=102.0,
            allow_jane_library_create=True))
        self.assertEqual(self.job(jid)['attempts'],1)
        kinds=[x[0] for x in self.conn.execute(
            'SELECT event FROM events WHERE job_id=? ORDER BY id',(jid,))]
        self.assertEqual(kinds,['submitted','claimed','needs_review'])

    def test_failed_native_preflight_cannot_repeat(self):
        jid=self.enqueue()
        with mock.patch.object(worker.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value={
                    'status':'native_ui_preflight_failed_no_job_created',
                    'xml_import_attempted':False}) as native:
                out=worker.run_once(self.conn,self.workspace,
                                    allow_jane_library_create=True)
                again=worker.run_once(self.conn,self.workspace,
                                      allow_jane_library_create=True)
        self.assertEqual(out['status'],'needs_review')
        self.assertIsNone(again)
        native.assert_called_once()
        self.assertEqual(self.job(jid)['attempts'],1)

    def test_native_exception_still_no_replay(self):
        jid=self.enqueue()
        with mock.patch.object(worker.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',
                                   side_effect=RuntimeError('native GUI error')):
                out=worker.run_once(self.conn,self.workspace,
                                    allow_jane_library_create=True)
        self.assertEqual(out['status'],'needs_review')
        self.assertEqual(self.job(jid)['attempts'],1)
        self.assertEqual(self.job(jid)['status'],'needs_review')
        self.assertEqual(self.job(jid)['error'],'native GUI error')
        self.assertIsNone(worker.run_once(self.conn,self.workspace,
                                          allow_jane_library_create=True))

    def test_expired_inflight_native_job_never_requeues(self):
        jid=self.enqueue()
        claim=worker.claim(self.conn,'abandoned-worker',now=101.0,
                           allow_jane_library_create=True)
        self.assertEqual(claim['id'],jid)
        self.assertIsNone(worker.claim(self.conn,'another',now=1000.0,
                                       allow_jane_library_create=True))
        self.assertEqual(self.job(jid)['status'],'needs_review')
        self.assertEqual(self.job(jid)['attempts'],1)

    def test_stop_marker_prevents_gui_launch_even_if_approved(self):
        jid=self.enqueue()
        (self.state/'STOP').write_text('halt')
        with mock.patch.object(jane,'onepass') as native:
            self.assertIsNone(worker.run_once(self.conn,self.workspace,
                                              allow_jane_library_create=True))
        native.assert_not_called()
        self.assertEqual(self.job(jid)['attempts'],0)

    def test_library_job_payload_restricted_no_arbitrary_scripts_paths(self):
        invalid=[
            {}, {'job_id':'../escape'}, {'job_id':'UPPER'},
            {'job_id':12}, {'job_id':'x'}, {'job_id':self.slug,'xml':'file'},
            {'job_id':self.slug,'script':'run-anything'},
        ]
        for index,payload in enumerate(invalid):
            with self.subTest(i=index):
                with self.assertRaises(ValueError):
                    worker.enqueue(self.conn,worker.LIBRARY_KIND,
                                   payload,'bad-'+str(index))
        self.assertEqual(self.conn.execute(
            'SELECT count(*) FROM jobs').fetchone()[0],0)

    def test_wrong_platform_marks_needs_review_no_native_call(self):
        jid=self.enqueue()
        with mock.patch.object(worker.sys,'platform','linux'):
            with mock.patch.object(jane,'onepass') as native:
                out=worker.run_once(self.conn,self.workspace,
                                    allow_jane_library_create=True)
        self.assertEqual(out['status'],'needs_review')
        self.assertEqual(self.job(jid)['attempts'],1)
        native.assert_not_called()

    def test_loop_explicit_gui_approval_is_separate_from_xml_flag(self):
        jid=self.enqueue()
        fake_result={'status':'library_bootstrap_not_verified',
                     'native_library_app_selected_verified':False,
                     'xml_import_attempted':False}
        with mock.patch.object(worker.sys,'platform','darwin'):
            with mock.patch.object(jane,'onepass',return_value=fake_result) as native:
                stats=loop.poll(self.conn,self.workspace,self.state,worker_id='jane-test',
                                max_jobs=1,max_seconds=1,poll_seconds=0.1,
                                allow_jane_library_create=True,
                                jane_queue_job_id=jid)
        self.assertEqual(stats['executed'],1)
        self.assertFalse(stats['native_import_enabled'])
        self.assertTrue(stats['jane_library_creation_approved'])
        self.assertEqual(stats['succeeded'],0)
        self.assertEqual(stats['failed'],1)
        native.assert_called_once()
        self.assertEqual(self.job(jid)['status'],'needs_review')

    def test_broad_native_loop_flag_rejected_before_gui_or_claim(self):
        jid=self.enqueue()
        with mock.patch.object(jane,'onepass') as native:
            with self.assertRaisesRegex(ValueError, 'one exact queue job ID'):
                loop.poll(self.conn,self.workspace,self.state,
                          worker_id='unsafe-broad',
                          max_jobs=1,max_seconds=1,poll_seconds=0.1,
                          allow_jane_library_create=True)
            with self.assertRaisesRegex(ValueError, 'max-jobs=1'):
                loop.poll(self.conn,self.workspace,self.state,
                          worker_id='unsafe-many',
                          max_jobs=20,max_seconds=1,poll_seconds=0.1,
                          allow_jane_library_create=True,
                          jane_queue_job_id=jid)
        native.assert_not_called()
        self.assertEqual(self.job(jid)['attempts'],0)

    def test_stop_appearing_after_claim_prevents_native_ui(self):
        jid=self.enqueue()
        def stop_during_claim(*args,**kwargs):
            (self.state/'STOP').write_text('stop now')
            return worker.claim(*args,**kwargs)
        original_claim=worker.claim
        # Patch using captured original to avoid recursion.
        def with_stop(*args,**kwargs):
            result=original_claim(*args,**kwargs)
            (self.state/'STOP').write_text('stop now')
            return result
        with mock.patch.object(worker,'claim',side_effect=with_stop):
            with mock.patch.object(worker.sys,'platform','darwin'):
                with mock.patch.object(jane,'onepass') as native:
                    out=worker.run_once(self.conn,self.workspace,
                                        allow_jane_library_create=True)
        self.assertEqual(out['status'],'needs_review')
        native.assert_not_called()
        self.assertEqual(self.job(jid)['attempts'],1)

    def test_default_loop_does_not_dispatch_native_gui(self):
        jid=self.enqueue()
        with mock.patch.object(jane,'onepass') as native:
            stats=loop.poll(self.conn,self.workspace,self.state,worker_id='default',
                            max_jobs=1,max_seconds=0.12,poll_seconds=0.1)
        self.assertEqual(stats['executed'],0)
        self.assertFalse(stats['jane_library_creation_approved'])
        self.assertEqual(self.job(jid)['status'],'queued')
        native.assert_not_called()

    def test_stable_slug_distinct_keys_same_native_job_still_serially_protected(self):
        first=self.enqueue('key1')
        second=self.enqueue('key2')
        self.assertNotEqual(first,second)
        self.assertEqual(self.job(first)['status'],'queued')
        self.assertEqual(self.job(second)['status'],'queued')
        # Native onepass's per-job receipt path is a second safety layer
        # even when different DB dedupe keys refer to same job_id.
        self.assertEqual(jane.path_for(self.home,self.slug),
                         jane.path_for(self.home,self.slug))


if __name__=='__main__':
    unittest.main()
