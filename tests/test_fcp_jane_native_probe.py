"""Read-only Jane macOS native-import probe regressions."""
import json
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_native_probe as probe


class NativeProbeTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.home = Path(td.name)
        self.root = self.home / 'Documents' / 'Rovor'
        self.root.mkdir(parents=True)
        (self.home / 'Movies').mkdir()
        self.job = self.root / 'fcp-jane-auto-20261022-183007'
        self.job.mkdir()
        self.target = self.job / 'ROVOR-Jane-Test.fcpbundle'
        (self.job / probe.RECEIPT_NAME).write_text(json.dumps({
            'status': 'native_library_not_observed',
            'target_library': str(self.target),
            'apple_event_sent': True,
            'library_creation_observed': False,
            'last_dispatched': 'landscape',
            'error': 'Target library was not created; portrait NOT sent'
        }))
        for label,w,h in [('landscape',1920,1080),('portrait',1080,1920)]:
            top = ET.Element('fcpxml',version='1.13')
            opts = ET.SubElement(top,'import-options')
            ET.SubElement(opts,'option',key='library location',value=self.target.as_uri())
            res = ET.SubElement(top,'resources')
            ET.SubElement(res,'format',id='r1',
                          frameDuration='1/60s',width=str(w),height=str(h))
            lib = ET.SubElement(top,'library')
            ev = ET.SubElement(lib,'event')
            proj = ET.SubElement(ev,'project')
            seq = ET.SubElement(proj,'sequence', duration='30s', format='r1')
            spine = ET.SubElement(seq, 'spine')
            ET.SubElement(spine, 'gap', duration='30s', offset='0s', start='0s')
            ET.ElementTree(top).write(self.job/(label+'-auto.fcpxml'), encoding='utf-8')
        self.update_hashes()

    def update_hashes(self):
        path = self.job / probe.RECEIPT_NAME
        receipt = json.loads(path.read_text())
        receipt['xml_hashes'] = {label: hashlib.sha256(
            (self.job / (label + '-auto.fcpxml')).read_bytes()).hexdigest()
            for label in ('landscape', 'portrait')}
        path.write_text(json.dumps(receipt))

    @staticmethod
    def processes_good(cmd, **kw):
        assert cmd == ['/bin/ps', '-axo', 'comm=']
        return subprocess.CompletedProcess(cmd,0,
            stdout='/Applications/Final Cut Pro.app/Contents/MacOS/Final Cut Pro\n/usr/bin/osascript\n',
            stderr='')

    def test_exact_failure_matches_user_log_and_never_dispatches(self):
        out=probe.inspect(self.root,self.job,home=self.home,process_run=self.processes_good)
        self.assertEqual(out['original_job_status'],'native_library_not_observed')
        self.assertTrue(out['apple_event_returned_zero'])
        self.assertFalse(out['native_timeline_verified'])
        self.assertFalse(out['expected_library_created'])
        self.assertFalse(out['portrait_dispatched'])
        self.assertTrue(out['no_second_import_started'])
        self.assertTrue(out['process']['final_cut_process_present'])
        self.assertTrue(out['process']['osascript_process_present'])
        self.assertEqual(out['xml_files']['landscape'],
                         'import_target_and_empty_30s_sequence_present')

    def test_wrong_target_xml_reported(self):
        file=self.job/'landscape-auto.fcpxml'
        tree=ET.parse(file)
        tree.getroot().find('./import-options/option').set('value',
                   '/Users/someone/production.fcpbundle')
        tree.write(file)
        self.update_hashes()
        result=probe.inspect(self.root,self.job,home=self.home)
        self.assertEqual(result['xml_files']['landscape'],'unexpected_xml_or_target')

    def test_changed_xml_is_not_reported_as_original_dispatch(self):
        file = self.job / 'landscape-auto.fcpxml'
        file.write_bytes(file.read_bytes() + b'\n')
        result = probe.inspect(self.root, self.job, home=self.home)
        self.assertEqual(result['xml_files']['landscape'], 'changed_since_dispatch_receipt')
        self.assertEqual(result['xml_files']['portrait'],
                         'import_target_and_empty_30s_sequence_present')

    def test_absent_hash_does_not_certify_original_xml(self):
        path = self.job / probe.RECEIPT_NAME
        receipt = json.loads(path.read_text())
        del receipt['xml_hashes']
        path.write_text(json.dumps(receipt))
        result = probe.inspect(self.root, self.job, home=self.home)
        self.assertEqual(result['xml_files']['landscape'], 'receipt_hash_missing_or_invalid')

    def test_incorrect_timeline_structure_is_not_valid(self):
        file = self.job / 'landscape-auto.fcpxml'
        original = file.read_bytes()
        changes = [
            ('./resources/format', 'width', '1080'),
            ('./resources/format', 'height', '1920'),
            ('./resources/format', 'frameDuration', '1/30s'),
            ('./library/event/project/sequence', 'format', 'missing'),
            ('./library/event/project/sequence/spine/gap', 'duration', '1s'),
            ('./library/event/project/sequence/spine/gap', 'offset', '10s'),
            ('./library/event/project/sequence/spine/gap', 'src', 'file:///private.mov'),
        ]
        for selector, key, value in changes:
            with self.subTest(key=key, value=value):
                top = ET.fromstring(original)
                top.find(selector).set(key, value)
                ET.ElementTree(top).write(file)
                self.update_hashes()
                result = probe.inspect(self.root, self.job, home=self.home)
                self.assertEqual(result['xml_files']['landscape'], 'unexpected_xml_or_target')

    def test_extra_clips_or_sequences_are_not_empty_diagnostic(self):
        file = self.job / 'landscape-auto.fcpxml'
        original = file.read_bytes()
        for selector, tag in [('./library/event/project/sequence/spine', 'asset-clip'),
                              ('./library/event/project', 'sequence'),
                              ('./resources', 'format')]:
            with self.subTest(tag=tag):
                top = ET.fromstring(original)
                ET.SubElement(top.find(selector), tag)
                ET.ElementTree(top).write(file)
                self.update_hashes()
                result = probe.inspect(self.root, self.job, home=self.home)
                self.assertEqual(result['xml_files']['landscape'], 'unexpected_xml_or_target')

    def test_created_library_is_not_timeline_proof(self):
        self.target.mkdir()
        result=probe.inspect(self.root,self.job,home=self.home)
        self.assertTrue(result['expected_library_created'])
        self.assertFalse(result['native_timeline_verified'])

    def test_library_discovery_is_bounded_and_nonrecursive(self):
        (self.home/'Movies'/'ROVOR-Auto-Test.fcpbundle').mkdir()
        outside=self.home/'Private'
        outside.mkdir()
        (outside/'ROVOR-secret.fcpbundle').mkdir()
        result=probe.inspect(self.root,self.job,home=self.home)
        matches=result['discovery']['matches']
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]['scope'],'movies')
        self.assertNotIn('Private',str(result))

    def test_default_untitled_library_is_detected_without_attribution(self):
        (self.home/'Movies'/'Untitled.fcpbundle').mkdir()
        result=probe.inspect(self.root,self.job,home=self.home)
        self.assertIn({'scope':'movies',
                       'name':'default_untitled_library_present',
                       'attribution':'unverified_existing_or_new'},
                      result['discovery']['matches'])
        self.assertFalse(result['native_timeline_verified'])

    def test_malformed_receipt_rejected_without_mutating(self):
        r=self.job/probe.RECEIPT_NAME
        orig=r.read_text()
        r.write_text('{"status":"pass","target_library":"/tmp/foo.fcpbundle"}')
        with self.assertRaisesRegex(ValueError,'outside expected'):
            probe.inspect(self.root,self.job,home=self.home)
        r.write_text(orig)

    def test_other_directory_and_symlink_refused(self):
        another=self.root/'production'
        another.mkdir()
        with self.assertRaisesRegex(ValueError,'disposable Jane'):
            probe.inspect(self.root,another,home=self.home)
        alias=self.root/'fcp-jane-auto-link'
        alias.symlink_to(self.job)
        with self.assertRaisesRegex(ValueError,'disposable Jane'):
            probe.inspect(self.root,alias,home=self.home)

    def test_queue_folder_requires_canonical_uuid(self):
        for name in ('native-import-anything', 'native-import-../escape',
                     'native-import-11111111111111111111111111111111'):
            with self.subTest(name=name):
                folder = self.root / name
                folder.mkdir(parents=True)
                with self.assertRaisesRegex(ValueError, 'disposable Jane'):
                    probe.constrained_job(self.root, folder)

    def test_queue_folder_cannot_be_symlink(self):
        folder = self.root / 'native-import-11111111-1111-4111-8111-111111111111'
        folder.symlink_to(self.job)
        with self.assertRaisesRegex(ValueError, 'disposable Jane'):
            probe.constrained_job(self.root, folder)

    def test_process_errors_dont_claim_app_absent(self):
        def failed(cmd,**kw):
            return subprocess.CompletedProcess(cmd,1,stdout='',stderr='Denied')
        info=probe.process_names(run=failed)
        self.assertEqual(info['process_visibility'],'unavailable')
        self.assertNotIn('final_cut_process_present',info)

    def test_sent_flag_alone_is_not_zero_returncode_evidence(self):
        path = self.job / probe.RECEIPT_NAME
        receipt = json.loads(path.read_text())
        receipt['status'] = 'apple_event_failed'
        path.write_text(json.dumps(receipt))
        result = probe.inspect(self.root, self.job, home=self.home,
                               process_run=self.processes_good)
        self.assertIsNone(result['apple_event_returned_zero'])
        receipt['last_apple_event_returncode'] = 1
        path.write_text(json.dumps(receipt))
        result = probe.inspect(self.root, self.job, home=self.home,
                               process_run=self.processes_good)
        self.assertFalse(result['apple_event_returned_zero'])


if __name__=='__main__':
    unittest.main()
