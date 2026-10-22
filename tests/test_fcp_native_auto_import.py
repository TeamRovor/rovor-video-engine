"""Jane Apple event native Final Cut automatic import safety tests (NO app, no AI)."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_native_auto_import as jane
from fcp_native_import_candidate import create_candidate


class AutoImportTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.home = Path(td.name) / 'home'
        self.base = self.home / 'Documents' / 'Rovor'
        self.base.mkdir(parents=True)
        self.candidates = self.base / 'validated-candidates'
        self.candidates.mkdir()
        self.output = self.base / 'new-automated-import'
        self.dtd = self.base / 'actual-installed-dtd'
        self.dtd.write_text('fake DTD; mocked xmllint in unit only')
        hashes = {}
        for label, width, height in jane.LABELS:
            source = self.candidates / (
                'ROVOR-NATIVE-IMPORT-' + label + '-30s-60fps.fcpxml')
            create_candidate(source, int(width), int(height), label)
            hashes[source.name] = jane.sha(source)
        (self.candidates / 'native-candidate-receipt.json').write_text(
            json.dumps({
                'status': 'candidate_prepared_native_not_imported',
                'duration_seconds': 30, 'frame_rate': 60,
                'referenced_media_files': 0,
                'native_final_cut_operated': False,
                'fcpxml_sha256': hashes,
            }))
        patch = mock.patch.object(jane.Path, 'home', return_value=self.home)
        patch.start()
        self.addCleanup(patch.stop)
        self.validator_calls = []

    def validator(self, command, **kw):
        self.validator_calls.append(command)
        self.assertEqual(command[1:4], ['--nonet', '--noout', '--dtdvalid'])
        self.assertEqual(Path(command[4]).read_bytes(), self.dtd.read_bytes())
        self.assertEqual(kw['timeout'], 30)
        xml = ET.parse(command[5]).getroot()
        self.assertEqual(xml[0].tag, 'import-options')
        return subprocess.CompletedProcess(command, 0, stdout='', stderr='')

    def prepare(self):
        with mock.patch.object(jane.shutil, 'which', return_value='/usr/bin/xmllint'):
            return jane.prepare(self.candidates, self.output, self.dtd, run=self.validator)

    def test_prepare_targets_new_library_without_native_app(self):
        before = {label: jane.sha(
            self.candidates / ('ROVOR-NATIVE-IMPORT-'+label+'-30s-60fps.fcpxml'))
            for label, _, _ in jane.LABELS}
        state = self.prepare()
        self.assertEqual(state['status'], 'ready_to_dispatch_not_launched')
        self.assertEqual(len(self.validator_calls), 2)
        self.assertFalse(state['apple_event_sent'])
        self.assertFalse(state['native_timeline_verified'])
        self.assertFalse(state['original_media_modified'])
        self.assertFalse(Path(state['target_library']).exists())
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for label, _, _ in jane.LABELS:
            source = self.candidates / (
                'ROVOR-NATIVE-IMPORT-'+label+'-30s-60fps.fcpxml')
            self.assertEqual(before[label], jane.sha(source))
            target_xml = ET.parse(self.output / (label+'-auto.fcpxml')).getroot()
            opt = target_xml.findall('./import-options/option')
            self.assertEqual(opt[0].attrib, {
                'key':'library location',
                'value': Path(state['target_library']).as_uri()})
            self.assertTrue(opt[0].get('value').endswith('.fcpbundle'))
            self.assertEqual(target_xml.find('./library/event/project/sequence').get('duration'), '30s')
            self.assertEqual(target_xml.find('./resources/format').get('frameDuration'), '1/60s')

    def test_dispatch_sends_two_native_events_without_manual_menu(self):
        state = self.prepare()
        sent = []
        target = Path(state['target_library'])
        def native_fake(command, **kw):
            sent.append(command)
            self.assertEqual(command[:2], ['osascript', '-e'])
            self.assertIn('open POSIX file', command[2])
            self.assertTrue(command[3].endswith('-auto.fcpxml'))
            if len(sent) == 1:
                target.mkdir()
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        with mock.patch.object(jane, 'APP', self.base):
            result = jane.dispatch(self.output, state, run=native_fake,
                                   clock=lambda: 1, sleep=lambda n: None)
        self.assertEqual(result['status'], 'apple_events_sent_timeline_unverified')
        self.assertTrue(result['library_creation_observed'])
        self.assertTrue(result['apple_event_sent'])
        self.assertFalse(result['native_timeline_verified'])
        self.assertEqual(len(sent), 2)
        self.assertEqual([Path(cmd[3]).stem for cmd in sent],
                         ['landscape-auto','portrait-auto'])

    def test_failed_first_event_does_not_send_portrait(self):
        state = self.prepare()
        sent = []
        def native_fake(command, **kw):
            sent.append(command)
            return subprocess.CompletedProcess(command, 1,
                                               stdout='', stderr='Not authorized')
        with mock.patch.object(jane, 'APP', self.base):
            result = jane.dispatch(self.output, state, run=native_fake)
        self.assertEqual(result['status'], 'apple_event_failed')
        self.assertIn('Not authorized', result['error'])
        self.assertEqual(len(sent), 1)
        self.assertFalse(result['library_creation_observed'])

    def test_no_library_stops_without_second_event(self):
        state = self.prepare()
        sent = []
        def fake(command, **kw):
            sent.append(command)
            return subprocess.CompletedProcess(command, 0, stdout='', stderr='')
        with mock.patch.object(jane, 'APP', self.base):
            result = jane.dispatch(self.output, state, run=fake,
                                   clock=lambda: 10, wait_seconds=0)
        self.assertEqual(result['status'], 'native_library_not_observed')
        self.assertEqual(len(sent), 1)
        self.assertFalse(result['native_timeline_verified'])

    def test_dispatch_checkpoint_exists_before_blocking_apple_event(self):
        state = self.prepare()
        seen = []
        def check_live_receipt(command, **kw):
            current = json.loads(
                (self.output / 'native-auto-import-receipt.json').read_text())
            seen.append(current)
            self.assertEqual(current['status'],
                             'sending_landscape_apple_event')
            self.assertTrue(current['apple_event_dispatch_attempted'])
            self.assertFalse(current['apple_event_sent'])
            # Simulate a blocked/denied Automation event, without running FCP.
            return subprocess.CompletedProcess(command, 1,
                                               stdout='', stderr='Denied by macOS')
        with mock.patch.object(jane, 'APP', self.base):
            result = jane.dispatch(self.output, state, run=check_live_receipt)
        self.assertEqual(len(seen), 1)
        self.assertEqual(result['status'], 'apple_event_failed')
        final = json.loads(
            (self.output / 'native-auto-import-receipt.json').read_text())
        self.assertEqual(final['status'], 'apple_event_failed')
        self.assertFalse(final['native_timeline_verified'])

    def test_crash_leftover_old_receipt_tmp_cannot_block_final_state(self):
        state = self.prepare()
        stale = self.output / 'receipt.tmp'
        stale.write_text('simulated prior interrupted write')
        with mock.patch.object(jane, 'APP', self.base):
            result = jane.dispatch(self.output, state,
                                   run=lambda *a, **kw: subprocess.CompletedProcess(
                                       a[0], 1, stdout='', stderr='Denied'))
        self.assertEqual(result['status'], 'apple_event_failed')
        self.assertTrue(stale.exists())
        self.assertEqual(
            json.loads((self.output / 'native-auto-import-receipt.json').read_text())['status'],
            'apple_event_failed')

    def test_already_existing_output_rejected(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'must be a new path'):
            self.prepare()

    def test_tampered_source_rejected_without_output(self):
        f = self.candidates / 'ROVOR-NATIVE-IMPORT-landscape-30s-60fps.fcpxml'
        f.write_text(f.read_text() + 'tampered')
        with self.assertRaisesRegex(ValueError, 'Candidate changed'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_invalid_dtd_prevents_app_dispatch(self):
        def fail(argv, **kw):
            return subprocess.CompletedProcess(argv, 1, stdout='', stderr='bad schema')
        with mock.patch.object(jane.shutil, 'which', return_value='/usr/bin/xmllint'):
            with self.assertRaisesRegex(ValueError, 'DTD rejected'):
                jane.prepare(self.candidates, self.output, self.dtd, run=fail)
        self.assertFalse(self.output.exists())

    def test_dispatch_can_not_replay(self):
        state = self.prepare()
        state['status'] = 'apple_events_sent_timeline_unverified'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            jane.dispatch(self.output, state)


if __name__ == '__main__':
    unittest.main()
