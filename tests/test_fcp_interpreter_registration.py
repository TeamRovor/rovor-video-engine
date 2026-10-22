"""No-model Open Interpreter config discovery regressions; no CLI or MCP spawned."""
import json
import subprocess
import sys
import tempfile
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from pathlib import Path
from unittest import TestCase, main
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_host_smoke as smoke
import fcp_interpreter_stage as stage
import fcp_interpreter_registration as reg


class RegistrationTests(TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name) / 'stage'
        self.project = self.root / 'project'
        self.allowed = self.project / 'fixtures'
        self.root.mkdir()
        self.allowed.mkdir(parents=True)
        (self.project / '.openinterpreter').mkdir()
        (self.project / '.openinterpreter' / 'config.toml').write_text(stage.config_xml(self.allowed))
        (self.project / 'AGENTS.md').write_text('Test only')
        (self.project / 'sentinel.fcpxml').write_text('<fcpxml/>')
        for name, w, h in [('landscape',1920,1080), ('portrait',1080,1920)]:
            smoke.fixture(self.allowed / (name + '.fcpxml'), w, h)
        self.manifest = dict(
            status='staged_not_interpreter_verified',
            source_receipt_status='passed_direct_mcp',
            source_server_version='0.27.2',
            project=str(self.project),
            allowed_fcp_root=str(self.allowed),
            landscape=str(self.allowed / 'landscape.fcpxml'),
            portrait=str(self.allowed / 'portrait.fcpxml'),
            outside_root_sentinel=str(self.project / 'sentinel.fcpxml'),
            local_provider_request_started=False,
            interpreter_mcp_client_verified=False,
            native_final_cut_operated=False,
            allowed_mcp_tools=['inspect']
        )
        self.write_manifest()

    def write_manifest(self):
        (self.root / 'stage-receipt.json').write_text(json.dumps(self.manifest))

    def client(self, argv, **kwargs):
        self.assertEqual(argv[0], 'fake-interpreter')
        self.assertEqual(argv[-3:], ['mcp', 'list', '--json'])
        self.assertEqual(kwargs['cwd'], str(self.project))
        self.assertEqual(kwargs['timeout'], 45)
        override = argv[argv.index('-c') + 1]
        table = tomllib.loads('config = ' + override.split('=', 1)[1])['config']
        self.assertEqual(table['command'], 'uvx')
        self.assertEqual(table['args'], reg.PINNED_ARGS)
        self.assertEqual(table['enabled_tools'], ['inspect'])
        self.assertTrue(table['enabled'])
        self.assertTrue(table['required'])
        self.assertEqual(table['env']['FCP_PROJECTS_DIRS'], str(self.allowed))
        self.assertEqual(table['env']['FCP_MCP_AUTOPUSH'], '0')
        self.assertIn('sandbox_mode="read-only"', argv)
        self.assertIn('approval_policy="on-request"', argv)
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([
            {'name': 'fcpxml', 'enabled': True, 'disabled_reason': None,
             'transport': {'type': 'stdio', 'command': 'uvx',
                           'args': reg.PINNED_ARGS,
                           'env': {
                               'FCP_PROJECTS_DIR': str(self.allowed),
                               'FCP_PROJECTS_DIRS': str(self.allowed),
                               'FCP_MCP_AUTOPUSH': '0',
                               'FCP_MCP_INDEX': 'off',
                               'FCP_WATCH_DIR': '',
                               'UV_NO_BUILD': '1'}}}
        ]), stderr='')

    def test_explicit_override_works_without_trusting_project(self):
        report = reg.verify_cli(self.root, interpreter='fake-interpreter', runner=self.client)
        self.assertEqual(report['status'], 'passed_interpreter_registration_only')
        self.assertFalse(report['interpreter_mcp_client_verified'])
        self.assertFalse(report['model_or_mcp_server_launched'])
        wrapper = self.project / 'run-interpreter-fcp.sh'
        self.assertTrue(wrapper.exists())
        self.assertEqual(wrapper.stat().st_mode & 0o777, 0o700)
        self.assertIn("exec interpreter -c", wrapper.read_text())
        self.assertTrue((self.root / 'interpreter-registration-receipt.json').is_file())

    def test_raw_stage_config_is_not_sufficient_to_claim_registration(self):
        self.assertFalse((self.project / 'run-interpreter-fcp.sh').exists())
        self.assertEqual(reg.validate_stage(self.root)[2], self.allowed)
        self.assertFalse((self.root / 'interpreter-registration-receipt.json').exists())

    def test_untrusted_project_config_mismatch_fails_before_cli(self):
        cfg = self.project / '.openinterpreter' / 'config.toml'
        cfg.write_text(cfg.read_text().replace('enabled = true', 'enabled = false'))
        with self.assertRaisesRegex(ValueError, 'config changed'):
            reg.verify_cli(self.root, interpreter='fake-interpreter',
                           runner=lambda *_a, **_kw: self.fail('CLI must not run'))
        self.assertFalse((self.project / 'run-interpreter-fcp.sh').exists())

    def test_cli_reports_no_mcp_servers_does_not_claim_success(self):
        def empty(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout='[]', stderr='')
        with self.assertRaisesRegex(ValueError, 'ignored the ephemeral'):
            reg.verify_cli(self.root, interpreter='fake-interpreter', runner=empty)
        self.assertFalse((self.project / 'run-interpreter-fcp.sh').exists())

    def test_disabled_entry_blocks_wrapper(self):
        def disabled(argv, **kwargs):
            result = self.client(argv, **kwargs)
            entries = json.loads(result.stdout)
            entries[0]['enabled'] = False
            result.stdout = json.dumps(entries)
            return result
        with self.assertRaisesRegex(ValueError, 'different/unsafe'):
            reg.verify_cli(self.root, interpreter='fake-interpreter', runner=disabled)
        self.assertFalse((self.project / 'run-interpreter-fcp.sh').exists())

    def test_cli_failure_never_creates_wrapper(self):
        def fail(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 2, stdout='', stderr='error')
        with self.assertRaisesRegex(ValueError, 'exit 2'):
            reg.verify_cli(self.root, interpreter='fake-interpreter', runner=fail)
        self.assertFalse((self.project / 'run-interpreter-fcp.sh').exists())

    def test_retry_wont_overwrite_successful_wrapper(self):
        reg.verify_cli(self.root, interpreter='fake-interpreter', runner=self.client)
        with self.assertRaisesRegex(ValueError, 'Existing wrapper'):
            reg.verify_cli(self.root, interpreter='fake-interpreter', runner=self.client)

    def test_unexpected_stage_root_or_manifest_is_refused(self):
        self.manifest['allowed_fcp_root'] = '/tmp/private-client-media'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'Stage mismatch'):
            reg.verify_cli(self.root, interpreter='fake-interpreter',
                           runner=lambda *_a, **_kw: self.fail('CLI must not run'))


if __name__ == '__main__':
    main()
