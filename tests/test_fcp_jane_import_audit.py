"""Jane read-only wrong-library marker scan: no native app, no media."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_import_audit as audit
import fcp_jane_native_probe as probe


class WrongLibraryMarkerAuditTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.root = self.home / 'Documents' / 'Rovor'
        self.root.mkdir(parents=True)
        self.job = self.root / 'fcp-jane-auto-20261022-183007'
        self.job.mkdir()
        self.target = self.job / 'ROVOR-Jane-Test.fcpbundle'
        (self.job / probe.RECEIPT_NAME).write_text(json.dumps({
            'status': 'native_library_not_observed',
            'target_library': str(self.target),
            'last_dispatched': 'landscape',
        }))
        for label in ('landscape', 'portrait'):
            (self.job / (label + '-auto.fcpxml')).write_text('<fcpxml/>')
        self.lib = self.home / 'Movies' / 'Untitled.fcpbundle'
        self.lib.mkdir(parents=True)
        self.event = self.lib / 'An Unrelated Personal Event Name'
        self.event.mkdir()

    def test_exact_project_marker_found_read_only_in_native_database(self):
        marker = audit.MARKERS['landscape']
        p = self.event / 'CurrentVersion.fcpevent'
        p.write_bytes(b'SECRET CLIENT DATA\x00' + marker.encode('utf-16le') +
                      b'\x00No Other Project Should Be Reported')
        untouched = p.read_bytes()
        state = audit.audit(self.job, home=self.home)
        self.assertEqual(state['status'], 'read_only_targeted_marker_audit')
        self.assertTrue(state['marker_presence']['landscape']['found'])
        self.assertIn('native_database_byte_match',
                      state['marker_presence']['landscape']['evidence_types'])
        self.assertFalse(state['marker_presence']['portrait']['found'])
        self.assertFalse(state['native_timeline_verified'])
        self.assertTrue(state['no_import_or_replay'])
        self.assertTrue(state['no_media_files_read'])
        self.assertEqual(p.read_bytes(), untouched)
        self.assertNotIn('SECRET', json.dumps(state))
        self.assertNotIn('Personal Event', json.dumps(state))

    def test_media_never_scanned_even_if_it_contains_marker(self):
        media_dir = self.lib/'Original Media'
        media_dir.mkdir()
        (media_dir/'CurrentVersion.fcpevent').write_bytes(
            audit.MARKERS['landscape'].encode())
        out = audit.audit(self.job, home=self.home)
        self.assertFalse(out['marker_presence']['landscape']['found'])

    def test_native_project_directory_name_can_mark_presence(self):
        (self.event/audit.MARKERS['landscape']).mkdir()
        r = audit.audit(self.job, home=self.home)
        self.assertTrue(r['marker_presence']['landscape']['found'])
        self.assertIn('directory_name',
                      r['marker_presence']['landscape']['evidence_types'])

    def test_absence_in_native_database_does_not_claim_project_missing(self):
        (self.event/'CurrentVersion.fcpevent').write_bytes(b'compressed or opaque')
        out = audit.audit(self.job, home=self.home)
        self.assertFalse(out['marker_presence']['landscape']['found'])
        self.assertIn('INCONCLUSIVE', out['conclusion'])
        self.assertFalse(out['native_timeline_verified'])

    def test_unexpected_job_or_changed_target_refused(self):
        self.target.mkdir()
        with self.assertRaisesRegex(ValueError, 'state changed'):
            audit.audit(self.job, home=self.home)
        self.target.rmdir()
        r = self.job / probe.RECEIPT_NAME
        data = json.loads(r.read_text())
        data['status'] = 'apple_events_sent_timeline_unverified'
        r.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'only for'):
            audit.audit(self.job, home=self.home)

    def test_library_symlink_does_not_follow(self):
        old=self.lib
        old.rmdir()
        target=self.home/'private-library'
        target.mkdir()
        old.symlink_to(target, target_is_directory=True)
        response = audit.audit(self.job, home=self.home)
        self.assertEqual(response['status'],'known_untitled_library_not_present')
        self.assertFalse(response['native_timeline_verified'])

    def test_oversized_database_never_read(self):
        p=self.event/'CurrentVersion.fcpevent'
        with p.open('wb') as f:
            f.truncate(audit.FILE_LIMIT+1)
        state=audit.audit(self.job,home=self.home)
        self.assertTrue(state['database_search_limit_hit'])
        self.assertEqual(state['native_metadata_bytes_scanned'],0)


if __name__ == '__main__':
    unittest.main()
