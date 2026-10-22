"""Offline tests for preparing an Open Interpreter-only FCP read-only project.

Never invoke uvx, Interpreter, a provider or Final Cut.
"""
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_host_smoke as smoke
import fcp_interpreter_stage as stage


class StageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / 'host-evidence'
        self.evidence.mkdir()
        (self.evidence / 'fixtures').mkdir()
        self.out = self.root / 'new-interpreter-stage'
        reply = {}
        for name, width, height in [('landscape', 1920, 1080), ('portrait', 1080, 1920)]:
            smoke.fixture(self.evidence / 'fixtures' / (name + '.fcpxml'), width, height)
            reply[name] = {'content': [{'type': 'text', 'text': f'{width}x{height} @ 60fps'}],
                           'isError': False}
        self.receipt = {
            'status': 'passed_direct_mcp', 'stage': 'complete',
            'server': {'name': 'fcp-mcp-server', 'version': '0.27.2'},
            'available_tool_names': ['inspect', 'edit'],
            'native_final_cut_operated': False,
            'interpreter_mcp_client_verified': False,
            'fixture_results': reply,
            'outside_root_refusal': {'content': [
                {'type': 'text', 'text': 'Validation error: File path escapes the allowed roots'}
            ]}
        }
        self.write_receipt()

    def write_receipt(self):
        (self.evidence / 'receipt.json').write_text(json.dumps(self.receipt))

    def test_stage_uses_host_proof_and_no_model_or_native_application(self):
        with mock.patch.object(stage, 'fixture', wraps=smoke.fixture) as fixture_spy:
            with mock.patch('subprocess.Popen', side_effect=AssertionError('must not run process')):
                with mock.patch('builtins.print'):
                    manifest = stage.make_stage(self.evidence, self.out)
        self.assertEqual(fixture_spy.call_count, 2)
        self.assertEqual(manifest['status'], 'staged_not_interpreter_verified')
        self.assertFalse(manifest['interpreter_mcp_client_verified'])
        self.assertFalse(manifest['native_final_cut_operated'])
        self.assertFalse(manifest['local_provider_request_started'])
        with (self.out / 'project' / '.openinterpreter' / 'config.toml').open('rb') as file:
            config = tomllib.load(file)
        self.assertEqual(config['sandbox_mode'], 'read-only')
        self.assertEqual(config['approval_policy'], 'on-request')
        mcp = config['mcp_servers']['fcpxml']
        self.assertTrue(mcp['enabled'])
        self.assertTrue(mcp['required'])
        self.assertEqual(mcp['enabled_tools'], ['inspect'])
        self.assertEqual(mcp['default_tools_approval_mode'], 'prompt')
        self.assertEqual(mcp['args'],
                         ['--no-build', '--python', '3.11', '--with',
                          'cryptography==46.0.5', '--from',
                          'fcp-mcp-server==0.27.2', 'fcp-mcp-server'])
        self.assertEqual(mcp['env']['FCP_PROJECTS_DIRS'], str(self.out / 'project' / 'fixtures'))
        self.assertEqual(mcp['env']['FCP_PROJECTS_DIR'], mcp['env']['FCP_PROJECTS_DIRS'])
        self.assertEqual(mcp['env']['FCP_MCP_AUTOPUSH'], '0')
        self.assertEqual(mcp['env']['UV_NO_BUILD'], '1')
        self.assertEqual((self.out / 'stage-receipt.json').stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.out.stat().st_mode & 0o777, 0o700)
        self.assertTrue((self.out / 'project' / 'sentinel.fcpxml').is_file())
        self.assertFalse((self.out / 'project' / 'fixtures' / 'sentinel.fcpxml').exists())

    def test_failed_receipt_does_not_create_stage(self):
        self.receipt['status'] = 'failed'
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'Not a passing'):
            stage.make_stage(self.evidence, self.out)
        self.assertFalse(self.out.exists())

    def test_missing_refusal_or_wrong_version_blocks_stage(self):
        self.receipt['outside_root_refusal'] = {'content': []}
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'refusal'):
            stage.make_stage(self.evidence, self.out)
        self.assertFalse(self.out.exists())
        self.receipt['outside_root_refusal'] = {
            'content': [{'text': 'File path escapes the allowed roots'}]
        }
        self.receipt['server']['version'] = 'unexpected-version'
        self.write_receipt()
        with self.assertRaisesRegex(ValueError, 'Not a passing'):
            stage.make_stage(self.evidence, self.out)
        self.assertFalse(self.out.exists())

    def test_symlink_fixture_is_rejected_before_stage(self):
        target = self.root / 'other.fcpxml'
        target.write_text('<fcpxml/>')
        sample = self.evidence / 'fixtures' / 'landscape.fcpxml'
        sample.unlink()
        sample.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'unsafe evidence file'):
            stage.make_stage(self.evidence, self.out)
        self.assertFalse(self.out.exists())

    def test_refuses_reusing_evidence_or_existing_stage(self):
        with self.assertRaisesRegex(ValueError, 'must not overlap'):
            stage.make_stage(self.evidence, self.evidence / 'new-stage')
        self.out.mkdir()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            stage.make_stage(self.evidence, self.out)

    def test_wrong_geometry_is_rejected(self):
        smoke.fixture(self.evidence / 'fixtures' / 'portrait.fcpxml', 1920, 1080)
        with self.assertRaisesRegex(ValueError, 'wrong geometry'):
            stage.make_stage(self.evidence, self.out)


if __name__ == '__main__':
    unittest.main()
