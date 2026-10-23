"""No-model app-server MCP client tests. All subprocesses are mocked."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_interpreter_appserver_smoke as probe


class StubAppServer:
    def __init__(self, command, env, cwd=None):
        self.command = command
        self.cwd = cwd
        self.methods = []
        self.closed = False
        self.sentinel_allowed = False

    def request(self, method, params=None):
        self.methods.append(method)
        if method == 'initialize':
            return {'userAgent': 'open-interpreter-test'}
        if method == 'thread/start':
            assert params.get('ephemeral') is True
            assert params.get('sandbox') == 'read-only'
            return {'thread': {'id': 'synthetic-thread'}}
        if method == 'mcpServerStatus/list':
            assert params.get('threadId') == 'synthetic-thread'
            return {'data': [{'name': 'fcpxml', 'tools': {'inspect': {}}}]}
        if method == 'mcpServer/tool/call':
            assert params.get('server') == 'fcpxml'
            assert params.get('tool') == 'inspect'
            assert params.get('threadId') == 'synthetic-thread'
            filename = params['arguments']['args']['filepath']
            if filename.endswith('/sentinel.fcpxml'):
                if self.sentinel_allowed:
                    return {'content': [{'type': 'text', 'text': 'incorrectly accessible'}]}
                return {'content': [{'type': 'text', 'text':
                                     'Validation error: File path escapes the allowed roots'}]}
            dims = '1920x1080' if 'landscape' in filename else '1080x1920'
            return {'content': [{'type': 'text', 'text': dims + ' @ 60fps'}]}
        raise AssertionError('Unexpected RPC: ' + method)

    def send(self, notification):
        assert notification == {'method': 'initialized'}

    def close(self):
        self.closed = True


class AppServerTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.project = Path(d.name) / 'project'
        self.allowed = self.project / 'fixtures'
        self.allowed.mkdir(parents=True)
        self.stage = Path(d.name) / 'stage'
        self.instances = []

    def factory(self, argv, env, cwd):
        self.assertIn('app-server', argv)
        self.assertIn('sandbox_mode="read-only"', argv)
        self.assertIn('approval_policy="on-request"', argv)
        self.assertEqual(cwd, self.project)
        client = StubAppServer(argv, env, cwd)
        self.instances.append(client)
        return client

    def run_probe(self):
        with mock.patch.object(probe, 'validate_stage',
                               return_value=(self.stage, self.project, self.allowed)), \
             mock.patch.object(probe, 'Client', side_effect=self.factory):
            return probe.verify(self.stage, interpreter='interpreter-test')

    def test_actual_rpc_sequence_is_no_model_and_read_only(self):
        result = self.run_probe()
        self.assertEqual(result['status'], 'passed_interpreter_appserver_mcp_tool_call')
        self.assertTrue(result['open_interpreter_connected'])
        self.assertTrue(result['outside_root_refused'])
        self.assertFalse(result['model_turn_started'])
        self.assertFalse(result['native_final_cut_operated'])
        self.assertEqual(self.instances[0].methods,
                         ['initialize', 'thread/start', 'mcpServerStatus/list',
                          'mcpServer/tool/call', 'mcpServer/tool/call',
                          'mcpServer/tool/call'])
        self.assertTrue(self.instances[0].closed)

    def test_outside_root_access_fails_closed(self):
        def vulnerable_factory(argv, env, cwd):
            result = self.factory(argv, env, cwd)
            result.sentinel_allowed = True
            return result
        with mock.patch.object(probe, 'validate_stage',
                               return_value=(self.stage, self.project, self.allowed)), \
             mock.patch.object(probe, 'Client', side_effect=vulnerable_factory):
            with self.assertRaisesRegex(ValueError, 'outside-root refusal'):
                probe.verify(self.stage, interpreter='interpreter-test')
        self.assertTrue(self.instances[0].closed)


if __name__ == '__main__':
    unittest.main()
