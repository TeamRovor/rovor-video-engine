"""Offline safety checks for the existing queue's bounded Mac entrypoint."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ghost_worker as worker
import omniroute_mac_once as once


class OnceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name).resolve()
        self.state=self.base/'state'
        self.conn=worker.connect(self.state); self.addCleanup(self.conn.close)

    def launch(self, codes):
        return mock.Mock(side_effect=[subprocess.CompletedProcess([],c) for c in codes])

    def test_no_approval_never_reads_key_or_catalog(self):
        with mock.patch.object(once.runner,'access_key') as key, mock.patch.object(once.omni,'read_combo_catalog') as cat:
            self.assertEqual(once.main([]),0)
            key.assert_not_called(); cat.assert_not_called()

    def test_old_eligible_job_and_duplicate_attempt_are_refused(self):
        worker.enqueue(self.conn,'system.ping',{},'old')
        with self.assertRaises(ValueError): once.verify_queue(self.conn)
        self.conn.execute("UPDATE jobs SET status='succeeded'")
        worker.enqueue(self.conn,worker.OMNI_KIND,{'packet':once.PACKET},once.DEDUPE)
        self.conn.execute("UPDATE jobs SET status='needs_review'")
        with self.assertRaises(ValueError): once.verify_queue(self.conn)

    def test_unconfirmed_or_failed_unload_never_runs(self):
        for codes in ([1,1],[0,1],[0,0,0]):
            with self.subTest(codes=codes):
                execute=mock.Mock()
                with self.assertRaises(ValueError):
                    once.run_one(self.conn,self.state,self.base,run=self.launch(codes),execute=execute)
                execute.assert_not_called()
                self.assertTrue((self.state/'STOP').is_file())
        self.assertEqual(self.conn.execute('SELECT count(*) FROM jobs').fetchone()[0],0)

    def test_exact_one_attempt_and_stop_restored_after_exception(self):
        execute=mock.Mock(side_effect=RuntimeError('fixture'))
        with self.assertRaises(RuntimeError):
            once.run_one(self.conn,self.state,self.base,run=self.launch([0,0,1]),execute=execute)
        execute.assert_called_once()
        self.assertTrue((self.state/'STOP').is_file())
        with self.assertRaises(ValueError): once.verify_queue(self.conn)

    def test_existing_finalcut_jobs_remain_unclaimed(self):
        old=worker.enqueue(self.conn,worker.RESEARCH_KIND,{},'old-finalcut')
        def execute(conn,workspace,**kwargs):
            self.assertFalse((self.state/'STOP').exists())
            row=conn.execute('SELECT id FROM jobs WHERE dedupe_key=?',(once.DEDUPE,)).fetchone()
            return {'id':row[0],'status':'needs_review'}
        r=once.run_one(self.conn,self.state,self.base,run=self.launch([0,0,1]),execute=execute)
        self.assertEqual(r['status'],'needs_review')
        self.assertEqual(tuple(self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?',(old,)).fetchone()),('queued',0))
        self.assertTrue((self.state/'STOP').exists())

    def test_exact_selector_cannot_claim_older_readonly_or_another_omni_job(self):
        old=worker.enqueue(self.conn,'system.ping',{},'old-ping')
        first=worker.enqueue(self.conn,worker.OMNI_KIND,{'packet':once.PACKET},'old-omni')
        chosen=worker.enqueue(self.conn,worker.OMNI_KIND,{'packet':once.PACKET},'chosen-omni')
        job=worker.claim(self.conn,'test',allow_omniroute_model_use=True,omniroute_queue_job_id=chosen)
        self.assertEqual(job['id'],chosen)
        for jid in (old,first):
            self.assertEqual(tuple(self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?',(jid,)).fetchone()),('queued',0))
        with self.assertRaises(ValueError): worker.claim(self.conn,'test',omniroute_queue_job_id=chosen)

    def test_positive_domain_observation_allows_new_task_without_replaying_old(self):
        old=worker.enqueue(self.conn,worker.OMNI_KIND,{'packet':once.PACKET},once.DEDUPE)
        self.conn.execute("UPDATE jobs SET status='needs_review',attempts=1 WHERE id=?",(old,))
        launch=mock.Mock(side_effect=[subprocess.CompletedProcess([],113),
            subprocess.CompletedProcess([],0,stdout='gui/501 = {\n services = {\n 0 0 com.other.service\n }\n}')])
        def execute(conn,workspace,**kwargs):
            jid=kwargs['omniroute_queue_job_id']
            self.assertNotEqual(jid,old)
            self.assertEqual(conn.execute('SELECT dedupe_key FROM jobs WHERE id=?',(jid,)).fetchone()[0],once.JOBS['overnight-acceptance'])
            return {'id':jid,'status':'needs_review'}
        once.run_one(self.conn,self.state,self.base,run=launch,execute=execute,packet='overnight-acceptance')
        self.assertEqual(launch.call_count,2)
        self.assertTrue((self.state/'STOP').is_file())
        self.assertEqual(tuple(self.conn.execute('SELECT status,attempts FROM jobs WHERE id=?',(old,)).fetchone()),('needs_review',1))

    def test_domain_parser_rejects_missing_block_partial_output_and_existing_service(self):
        for text in ('', 'services = {\n', 'services = {\n 1 0 '+once.LABEL+'\n}\n'):
            self.assertFalse(once.service_absent_from_domain(subprocess.CompletedProcess([],0,stdout=text)))


if __name__=='__main__': unittest.main()
