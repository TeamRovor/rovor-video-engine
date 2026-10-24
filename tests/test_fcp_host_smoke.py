import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_host_smoke as smoke


class FakeClient:
    version = '0.27.2'
    deny = True
    geometry = True
    def request(self, method, params=None):
        if method == 'initialize':
            return {'serverInfo': {'name': 'fake-test-server', 'version': self.version}}
        if method == 'tools/list':
            return {'tools': [{'name': 'inspect'}]}
        path = params['arguments']['args']['filepath']
        if path.endswith('sentinel.fcpxml'):
            text = 'Validation error: File path escapes the allowed roots: not under any of /fixture. Add its directory to FCP_PROJECTS_DIRS to allow it.' if self.deny else 'OUTSIDE_ROOT_SENTINEL'
        else:
            text = ('1920x1080' if 'landscape' in path else '1080x1920') + (' @ 60fps' if self.geometry else ' @ 59.94fps')
        return {'content': [{'type': 'text', 'text': text}]}
    def send(self, message):
        pass


class SmokeTests(unittest.TestCase):
    def test_synthetic_geometry_and_no_external_assets(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'fixture.fcpxml'
            smoke.fixture(path, 1080, 1920)
            tree = ET.parse(path)
            self.assertEqual(tree.find('.//format').attrib['frameDuration'], '1/60s')
            self.assertEqual(tree.find('.//format').attrib['height'], '1920')
            self.assertEqual(tree.find('.//sequence').attrib['duration'], '1s')
            self.assertEqual(tree.findall('.//asset'), [])

    def test_direct_mcp_does_not_claim_interpreter_or_app(self):
        result = smoke.verify(FakeClient(), Path('/fixture'), Path('/outside/sentinel.fcpxml'))
        self.assertFalse(result['interpreter_mcp_client_verified'])
        self.assertFalse(result['native_final_cut_operated'])

    def test_unpinned_version_refused(self):
        client = FakeClient(); client.version = '0.27.1'
        with self.assertRaisesRegex(ValueError, 'version'):
            smoke.verify(client, Path('/fixture'), Path('/outside/sentinel.fcpxml'))

    def test_wrong_frame_rate_refused(self):
        client = FakeClient(); client.geometry = False
        with self.assertRaisesRegex(ValueError, 'dimensions/frame rate'):
            smoke.verify(client, Path('/fixture'), Path('/outside/sentinel.fcpxml'))

    def test_outside_root_leak_refused(self):
        client = FakeClient(); client.deny = False
        with self.assertRaisesRegex(ValueError, 'authorization refusal'):
            smoke.verify(client, Path('/fixture'), Path('/outside/sentinel.fcpxml'))

    def test_real_jsonrpc_transport_with_fake_server(self):
        import os
        with tempfile.TemporaryDirectory() as root:
            script = Path(root) / 'fake.py'
            script.write_text('import json,sys\nfor line in sys.stdin:\n m=json.loads(line)\n if "id" not in m: continue\n print(json.dumps({"jsonrpc":"2.0","id":m["id"],"result":{"echo":m["method"]}}),flush=True)\n')
            client = smoke.Client([sys.executable, str(script)], dict(os.environ))
            try:
                self.assertEqual(client.request('tools/list'), {'echo': 'tools/list'})
                self.assertEqual(client.request('next'), {'echo': 'next'})
            finally:
                client.close()
            self.assertIsNotNone(client.child.poll())

    def test_mcp_early_exit_captures_exit_status_and_private_error(self):
        import os
        with tempfile.TemporaryDirectory() as root:
            script = Path(root) / 'early_exit.py'
            script.write_text(r"""import sys
sys.stdin.readline()
sys.stderr.write("FATAL_STARTUP_TEST\n")
sys.stderr.flush()
sys.exit(7)
""")
            client = smoke.Client([sys.executable, str(script)], dict(os.environ))
            try:
                with self.assertRaisesRegex(ValueError, 'exit code 7'):
                    client.request('initialize')
                self.assertEqual(client.child.poll(), 7)
                self.assertIn(b'FATAL_STARTUP_TEST', client.errors)
            finally:
                client.close()


    def test_interpreter_and_codex_fcp_configs_match_wheel_only_pin(self):
        try:
            import tomllib
        except ModuleNotFoundError:
            import tomli as tomllib
        repo_root = Path(__file__).resolve().parents[1]
        expected = ['--no-build', '--python', '3.11', '--with', 'cryptography==46.0.5',
                    '--from', 'fcp-mcp-server==0.27.2', 'fcp-mcp-server']
        for config_path in ('.openinterpreter/config.toml', '.codex/config.toml'):
            with self.subTest(config=config_path):
                with (repo_root / config_path).open('rb') as file:
                    config = tomllib.load(file)
                mcp = config['mcp_servers']['fcpxml']
                self.assertFalse(mcp['enabled'])
                self.assertEqual(mcp['args'], expected)
                self.assertEqual(mcp['command'], 'uvx')
                self.assertEqual(mcp['env']['FCP_MCP_AUTOPUSH'], '0')
                self.assertEqual(mcp['env']['FCP_PROJECTS_DIR'], mcp['env']['FCP_PROJECTS_DIRS'])
                self.assertEqual(mcp['env']['FCP_PROJECTS_DIRS'], '/REPLACE_WITH_ABSOLUTE_DISPOSABLE_FCP_PATH')

    def test_missing_installed_dtd_still_writes_failure_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'diagnostics'
            with mock.patch.object(smoke.shutil, 'copyfile', side_effect=FileNotFoundError('FCP schema not installed')):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = smoke.main(['--output', str(target)])
            self.assertEqual(code, 2)
            report = json.loads((target / 'receipt.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['stage'], 'prepare_fixtures')
            self.assertIn('FileNotFoundError', report['error'])
            self.assertFalse(report['native_final_cut_operated'])
            self.assertFalse(report['interpreter_mcp_client_verified'])
            self.assertEqual((target / 'server-error.txt').read_bytes(), b'')

    def test_missing_uvx_after_fixture_validation_still_writes_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'diagnostics'
            def fake_copy(_source, dest):
                Path(dest).write_text('test dtd')
            with mock.patch.object(smoke.shutil, 'copyfile', side_effect=fake_copy), \
                 mock.patch.object(smoke.subprocess, 'run'), \
                 mock.patch.object(smoke, 'Client', side_effect=FileNotFoundError('uvx missing')) as client_ctor:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = smoke.main(['--output', str(target)])
            self.assertEqual(code, 2)
            command = client_ctor.call_args.args[0]
            self.assertEqual(command[:6], ['uvx', '--no-build', '--python', '3.11', '--with', 'cryptography==46.0.5'])
            self.assertEqual(command[-3:], ['--from', 'fcp-mcp-server==0.27.2', 'fcp-mcp-server'])
            report = json.loads((target / 'receipt.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(report['stage'], 'start_mcp')
            self.assertIn('FileNotFoundError', report['error'])
            self.assertIn('installed_dtd_sha256', report)
            self.assertEqual((target / 'server-error.txt').read_bytes(), b'')
