#!/usr/bin/env python3
"""Prove staged Jane FCP MCP registration via Open Interpreter CLI, without inference.

The separately staged .openinterpreter/config.toml may be IGNORED in an untrusted
directory. Instead supply one restricted, ephemeral -c mcp_servers.fcpxml=...
override to the actual interpreter mcp list --json CLI. No config is registered
globally, no model or MCP server is launched and no Final Cut file is modified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys

from fcp_interpreter_stage import config_xml


PINNED_ARGS = ['--no-build', '--python', '3.11', '--with',
               'cryptography==46.0.5', '--from', 'fcp-mcp-server==0.27.2',
               'fcp-mcp-server']


def _regular(path):
    if path.is_symlink() or not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Required staged file missing or unsafe: ' + str(path))


def validate_stage(stage_root):
    root = stage_root.expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Stage root missing or symlinked')
    project = root / 'project'
    allowed = project / 'fixtures'
    if any(p.is_symlink() or not p.is_dir() for p in (project, allowed, project / '.openinterpreter')):
        raise ValueError('Stage directory missing or symlinked')
    receipt = root / 'stage-receipt.json'
    _regular(receipt)
    if receipt.stat().st_size > 100_000:
        raise ValueError('Stage receipt too large')
    data = json.loads(receipt.read_text(encoding='utf-8'))
    expected = {
        'status': 'staged_not_interpreter_verified',
        'source_receipt_status': 'passed_direct_mcp',
        'source_server_version': '0.27.2',
        'project': str(project),
        'allowed_fcp_root': str(allowed),
        'landscape': str(allowed / 'landscape.fcpxml'),
        'portrait': str(allowed / 'portrait.fcpxml'),
        'outside_root_sentinel': str(project / 'sentinel.fcpxml'),
        'local_provider_request_started': False,
        'interpreter_mcp_client_verified': False,
        'native_final_cut_operated': False,
        'allowed_mcp_tools': ['inspect'],
    }
    for key, value in expected.items():
        if data.get(key) != value:
            raise ValueError('Stage mismatch in ' + key)
    cfg = project / '.openinterpreter' / 'config.toml'
    _regular(cfg)
    if cfg.read_text(encoding='utf-8') != config_xml(allowed):
        raise ValueError('Staged Open Interpreter config changed; refuse registration')
    for p in (allowed / 'landscape.fcpxml', allowed / 'portrait.fcpxml',
              project / 'sentinel.fcpxml', project / 'AGENTS.md'):
        _regular(p)
    return root, project, allowed


def override_for(allowed):
    """Produce a single valid TOML inline table for -c, no external TOML library."""
    q = json.dumps
    args = ', '.join(q(x) for x in PINNED_ARGS)
    path = q(str(allowed))
    return (
        'mcp_servers.fcpxml={'
        'enabled=true, required=true, command="uvx", '
        'args=[' + args + '], '
        'enabled_tools=["inspect"], default_tools_approval_mode="prompt", '
        'startup_timeout_sec=180, tool_timeout_sec=60, '
        'env={FCP_PROJECTS_DIR=' + path + ', FCP_PROJECTS_DIRS=' + path
        + ', FCP_MCP_AUTOPUSH="0", FCP_MCP_INDEX="off", '
        'FCP_WATCH_DIR="", UV_NO_BUILD="1"}}'
    )


def argv_for(interpreter, override, *subcommand):
    return [interpreter, '-c', override, '-c', 'sandbox_mode="read-only"',
            '-c', 'approval_policy="on-request"', *subcommand]


def verify_cli(stage_root, interpreter=None, runner=subprocess.run):
    root, project, allowed = validate_stage(stage_root)
    command = interpreter or shutil.which('interpreter')
    if not command:
        raise ValueError('Open Interpreter CLI not found on PATH')
    override = override_for(allowed)
    argv = argv_for(command, override, 'mcp', 'list', '--json')
    try:
        p = runner(argv, cwd=str(project), capture_output=True,
                   text=True, timeout=45, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Open Interpreter config-only probe exceeded 45s') from exc
    if p.returncode != 0:
        raise ValueError('Open Interpreter rejected per-run MCP config (exit ' +
                         str(p.returncode) + '); see private local CLI stderr')
    try:
        listed = json.loads(p.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError('Open Interpreter did not return an MCP JSON list') from exc
    if not isinstance(listed, list):
        raise ValueError('Unexpected Open Interpreter MCP list format')
    entries = [x for x in listed if isinstance(x, dict) and x.get('name') == 'fcpxml']
    if len(entries) != 1:
        raise ValueError('Open Interpreter ignored the ephemeral fcpxml registration')
    entry = entries[0]
    transport = entry.get('transport')
    wanted_env = {'FCP_PROJECTS_DIR': str(allowed), 'FCP_PROJECTS_DIRS': str(allowed),
                  'FCP_MCP_AUTOPUSH': '0', 'FCP_MCP_INDEX': 'off',
                  'FCP_WATCH_DIR': '', 'UV_NO_BUILD': '1'}
    if (entry.get('enabled') is not True or
            entry.get('disabled_reason') is not None or
            not isinstance(transport, dict) or
            transport.get('type') != 'stdio' or
            transport.get('command') != 'uvx' or
            transport.get('args') != PINNED_ARGS or
            transport.get('env') != wanted_env):
        raise ValueError('Open Interpreter loaded a different/unsafe fcpxml configuration')

    # Produce the ONLY approved invocation wrapper AFTER checking the actual CLI.
    # Does not edit ~/.openinterpreter/config.toml or mark a project trusted.
    wrapper = project / 'run-interpreter-fcp.sh'
    if wrapper.exists() or wrapper.is_symlink():
        raise ValueError('Existing wrapper present; refuse to overwrite')
    shell_argv = [shlex.quote(x) for x in argv_for('interpreter', override)]
    script = ('#!/bin/sh\nset -eu\n'
              'cd ' + shlex.quote(str(project)) + '\n'
              'exec ' + ' '.join(shell_argv) + ' "$@"\n')
    wrapper.write_text(script, encoding='utf-8')
    wrapper.chmod(0o700)
    receipt = {
        'status': 'passed_interpreter_registration_only',
        'interpreter_mcp_client_verified': False,
        'native_final_cut_operated': False,
        'model_or_mcp_server_launched': False,
        'read_only': True,
        'server_name': 'fcpxml',
        'tool_allowlist': ['inspect'],
        'wrapper_path': str(wrapper),
        'cli_registration_sha256': hashlib.sha256(p.stdout.encode()).hexdigest()
    }
    record = root / 'interpreter-registration-receipt.json'
    if record.exists() or record.is_symlink():
        wrapper.unlink()
        raise ValueError('Registration receipt already exists; preserve original')
    record.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    record.chmod(0o600)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True,
                        help='Already-generated private fcp-interpreter-stage-* directory')
    args = parser.parse_args(argv)
    try:
        report = verify_cli(args.stage)
        print(json.dumps(report, indent=2))
        print('MCP configuration is registered for the wrapper only; NO MCP handshake yet.')
        print('To inspect registration safely: ' +
              shlex.quote(report['wrapper_path']) + ' mcp get fcpxml')
        print('Foreground model use requires separate explicit opt-in.')
        return 0
    except ValueError as exc:
        print('NOT REGISTERED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
