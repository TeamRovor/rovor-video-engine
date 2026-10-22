"""Read-only, bounded Jane status checks. No FCP or Apple events."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_status as inspector


class JaneStatusTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.old = self.root / 'fcp-jane-auto-20261022-111111'
        self.new = self.root / 'fcp-jane-auto-20261022-223333'
        self.old.mkdir()
        self.new.mkdir()

    def test_picks_latest_job_without_suggesting_rerun(self):
        (self.old / inspector.RECEIPT).write_text(json.dumps({
            'status': 'apple_events_sent_timeline_unverified',
            'target_library': str(self.old / 'ROVOR-Jane-Test.fcpbundle'),
        }))
        (self.new / inspector.RECEIPT).write_text(json.dumps({
            'status': 'sending_landscape_apple_event',
            'target_library': str(self.new / 'ROVOR-Jane-Test.fcpbundle'),
            'apple_event_dispatch_attempted': True,
            'apple_event_sent': False,
        }))
        response = inspector.status(self.root)
        self.assertEqual(response['status'], 'sending_landscape_apple_event')
        self.assertFalse(response['native_timeline_verified'])
        self.assertTrue(response['read_only'])
        self.assertFalse(response['native_library_exists'])
        self.assertTrue(response['apple_event_dispatch_attempted'])
        self.assertIn('Do not rerun', response['next_action'])

    def test_no_receipt_is_not_falsely_a_failure(self):
        response = inspector.status(self.root)
        self.assertEqual(response['status'], 'no_receipt_yet_preparing_or_interrupted')
        self.assertIsNone(response['apple_event_sent'])

    def test_bare_library_folder_cannot_prove_timeline(self):
        target = self.new / 'ROVOR-Jane-Test.fcpbundle'
        target.mkdir()
        (self.new / inspector.RECEIPT).write_text(json.dumps({
            'status': 'apple_events_sent_timeline_unverified',
            'target_library': str(target),
            'library_creation_observed': True,
            'apple_event_sent': True,
        }))
        response = inspector.status(self.root)
        self.assertTrue(response['native_library_exists'])
        self.assertFalse(response['native_timeline_verified'])

    def test_rejects_unexpected_library_path_and_symlinks(self):
        r = self.new / inspector.RECEIPT
        r.write_text(json.dumps({
            'status': 'ok',
            'target_library': '/Users/someone/production.fcpbundle'
        }))
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            inspector.status(self.root)
        r.unlink()
        r.symlink_to(self.root / 'unknown')
        response = inspector.status(self.root)
        self.assertEqual(response['status'], 'no_receipt_yet_preparing_or_interrupted')

    def test_no_jobs_explicitly_unverified(self):
        self.new.rmdir()
        self.old.rmdir()
        self.assertEqual(
            inspector.status(self.root)['status'], 'no_jane_auto_import_job_found')


if __name__ == '__main__':
    unittest.main()
