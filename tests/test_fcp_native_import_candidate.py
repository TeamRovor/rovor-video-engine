"""Offline regression gates for native Final Cut import candidate preparation."""
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
import fcp_native_import_candidate as pilot


class NativeCandidateTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.stage = self.root / 'prior-stage'
        self.stage.mkdir()
        self.project = self.stage / 'project'
        self.project.mkdir()
        self.allowed = self.project / 'fixtures'
        self.allowed.mkdir()
        self.output = self.root / 'new-native-output'
        self.dtd = self.root / 'installed.dtd'
        self.dtd.write_text('fake source DTD, only subprocess can validate')
        self.called = []

    def validator(self, argv, **kwargs):
        self.called.append(argv)
        self.assertEqual(argv[1:4], ['--nonet', '--noout', '--dtdvalid'])
        self.assertEqual(argv[4], str(self.dtd))
        self.assertEqual(kwargs['timeout'], 30)
        self.assertTrue(Path(argv[5]).is_file())
        return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')

    def prepare(self, validator=None):
        with mock.patch.object(pilot, 'validate_stage',
                               return_value=(self.stage, self.project, self.allowed)), \
             mock.patch.object(pilot.shutil, 'which', return_value='/fake/xmllint'):
            return pilot.prepare(self.stage, self.output, self.dtd,
                                 run=validator or self.validator)

    def test_prepares_only_empty_30s_landscape_and_portrait(self):
        with mock.patch('subprocess.Popen',
                        side_effect=AssertionError('No process should start in unit test')):
            report = self.prepare()
        self.assertEqual(report['status'], 'candidate_prepared_native_not_imported')
        self.assertFalse(report['native_final_cut_import_verified'])
        self.assertFalse(report['model_turn_started'])
        self.assertFalse(report['media_modified'])
        self.assertEqual(len(self.called), 2)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        self.assertTrue((self.output / 'READ_ME_FIRST.txt').exists())
        self.assertIn('create a new EMPTY library',
                      (self.output / 'READ_ME_FIRST.txt').read_text())
        for name, width, height in (
            ('landscape', 1920, 1080), ('portrait', 1080, 1920)
        ):
            p = self.output / f'ROVOR-NATIVE-IMPORT-{name}-30s-60fps.fcpxml'
            doc = ET.parse(p).getroot()
            self.assertEqual(doc.attrib['version'], '1.13')
            fmt = doc.find('./resources/format')
            self.assertEqual((fmt.get('width'), fmt.get('height')),
                             (str(width), str(height)))
            self.assertEqual(fmt.get('frameDuration'), '1/60s')
            self.assertEqual(doc.find('./library/event/project/sequence').get('duration'), '30s')
            self.assertEqual(doc.find('./library/event/project/sequence/spine/gap').get('duration'), '30s')
            self.assertEqual(doc.findall('.//asset'), [])
            self.assertEqual(doc.findall('.//asset-clip'), [])
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),
                             report['fcpxml_sha256'][p.name])

    def test_missing_apple_dtd_fails_without_creating_output(self):
        self.dtd.unlink()
        with self.assertRaisesRegex(ValueError, 'DTD not installed'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_dtd_rejection_fails_without_output(self):
        def reject(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, stdout='', stderr='schema invalid')
        with self.assertRaisesRegex(ValueError, 'DTD rejected'):
            self.prepare(validator=reject)
        self.assertFalse(self.output.exists())

    def test_refuses_to_overwrite_any_existing_candidate(self):
        self.output.mkdir()
        with self.assertRaisesRegex(ValueError, 'brand-new'):
            self.prepare()

    def test_refuses_overlapping_source_stage(self):
        self.output = self.stage / 'new-output'
        with self.assertRaisesRegex(ValueError, 'inside prior evidence'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_manifest_explicitly_disclaims_native_and_model(self):
        self.prepare()
        receipt = json.loads((self.output / 'native-candidate-receipt.json').read_text())
        self.assertEqual(receipt['duration_seconds'], 30)
        self.assertEqual(receipt['frame_rate'], 60)
        self.assertEqual(receipt['referenced_media_files'], 0)
        self.assertFalse(receipt['native_final_cut_operated'])
        self.assertFalse(receipt['native_final_cut_import_verified'])
        self.assertFalse(receipt['model_turn_started'])


if __name__ == '__main__':
    unittest.main()
