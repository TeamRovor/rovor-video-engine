import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from continuity_ledger import validate, LedgerError, source_hash

LEDGER = Path(__file__).with_name('painting-film-ledger.json')

class ContinuityLedgerTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(LEDGER.read_text())

    def test_real_coverage_is_not_approval(self):
        s=validate(self.data)
        self.assertEqual(s['next_start_frame'], 8688)
        self.assertEqual(s['remaining_source_frames'], 7074)
        self.assertAlmostEqual(s['remaining_source_seconds'], 117.887313)
        self.assertFalse(s['artistic_approval'])
        self.assertFalse(s['technical_video_verified_from_media'])

    def test_changes_must_cover_entire_newly_claimed_section(self):
        self.data['revisions'][-1]['edited_intervals']=[[7920,8620]]
        with self.assertRaisesRegex(LedgerError,'unsupported new-coverage'):
            validate(self.data)

    def test_no_coverage_regression(self):
        self.data['revisions'][-1]['review_coverage']=[0,7900]
        with self.assertRaisesRegex(LedgerError, 'cannot regress'):
            validate(self.data)

    def test_no_fake_release_approval(self):
        self.data['publication_approved']=True
        with self.assertRaisesRegex(LedgerError,'release approval'):
            validate(self.data)
        self.data['publication_approved']=False
        self.data['revisions'][-1]['artist_approved']=True
        with self.assertRaisesRegex(LedgerError,'approval must remain'):
            validate(self.data)

    def test_no_float_or_boolean_frame_indices(self):
        self.data['revisions'][-1]['review_coverage']=[0,8688.0]
        with self.assertRaisesRegex(LedgerError,'integer'):
            validate(self.data)
        self.data['revisions'][-1]['review_coverage']=[False,8688]
        with self.assertRaisesRegex(LedgerError,'integer'):
            validate(self.data)

    def test_reject_mismatched_total_frame_count(self):
        self.data['total_source_frames']=15761
        with self.assertRaisesRegex(LedgerError,'Total source frames'):
            validate(self.data)

    def test_reject_wrong_audio_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.mp3';p.write_bytes(b'wrong')
            with self.assertRaisesRegex(LedgerError,'original narration'):
                validate(self.data,source=p)

    def test_reject_modified_archive(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/self.data['revisions'][-1]['editable_archive']
            p.write_bytes(b'not the source')
            with self.assertRaisesRegex(LedgerError,'archive hash failed'):
                validate(self.data,archives={p.name:p})

    def test_reject_overlapping_edit_intervals(self):
        self.data['revisions'][-1]['edited_intervals']=[[7920,8500],[8400,8688]]
        with self.assertRaisesRegex(LedgerError,'overlap'):
            validate(self.data)

    def test_fresh_episode_different_duration(self):
        a=copy.deepcopy(self.data)
        a['project_id']='new-original-video'
        a['original_audio']['duration_seconds']=50
        a['total_source_frames']=3000
        a['revisions']=[{'revision':'v1','review_coverage':[0,1800],
                         'edited_intervals':[[0,1800]],'editable_archive':'new.zip',
                         'editable_archive_sha256':'a'*64,
                         'artist_approved':False,'publication_approved':False}]
        a['current_revision']='v1'
        s=validate(a)
        self.assertEqual(s['next_start_frame'],1800)
        self.assertEqual(s['remaining_source_seconds'],20)

    def test_detect_duplicate_revision(self):
        self.data['revisions'][-1]['revision']='v6'
        with self.assertRaisesRegex(LedgerError,'duplicate'):
            validate(self.data)

if __name__=='__main__': unittest.main()