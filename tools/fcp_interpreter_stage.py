#!/usr/bin/env python3
"""Stage an approval-gated Open Interpreter FCP MCP project from an actual Mac smoke receipt.

No agent, MCP process, software installer, inference, Final Cut, or client media is run.
Requires the previously verified direct Mac MCP receipt and its synthetic fixtures.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import sys
import xml.etree.ElementTree as ET

from fcp_host_smoke import fixture


def plain_file(path):
    """Reject symlinks and non-regular source files, including symlink parents."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or unsafe evidence file: ' + str(path))
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Not a regular evidence file: ' + str(path))


def prove(evidence):
    evidence = evidence.expanduser().absolute()
    if evidence.is_symlink() or not evidence.is_dir():
        raise ValueError('Evidence directory missing or symlink')
    receipt_path = evidence / 'receipt.json'
    plain_file(receipt_path)
    if receipt_path.stat().st_size > 100_000:
        raise ValueError('Oversized MCP receipt')
    report = json.loads(receipt_path.read_text(encoding='utf-8'))
    if (report.get('status') != 'passed_direct_mcp' or
            report.get('stage') != 'complete' or
            report.get('server', {}).get('version') != '0.27.2' or
            report.get('native_final_cut_operated') is not False or
            report.get('interpreter_mcp_client_verified') is not False):
        raise ValueError('Not a passing, read-only direct MCP host receipt')
    refusal = report.get('outside_root_refusal', {}).get('content', [])
    if not any('escapes the allowed roots' in block.get('text', '').lower()
               for block in refusal if isinstance(block, dict)):
        raise ValueError('No outside-root refusal evidence')
    if 'inspect' not in report.get('available_tool_names', []):
        raise ValueError('Host server did not advertise inspect')
    for name, width, height in [('landscape', 1920, 1080), ('portrait', 1080, 1920)]:
        path = evidence / 'fixtures' / (name + '.fcpxml')
        plain_file(path)
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Oversized source fixture')
        root = ET.parse(path).getroot()
        formats = root.findall('./resources/format')
        if (root.get('version') != '1.13' or
                not any(x.get('width') == str(width) and
                        x.get('height') == str(height) and
                        x.get('frameDuration') == '1/60s' for x in formats)):
            raise ValueError('Prior host fixture has wrong geometry/frame rate')
        reply = report.get('fixture_results', {}).get(name, {})
        texts = '\n'.join(x.get('text', '') for x in reply.get('content', [])
                          if isinstance(x, dict))
        if reply.get('isError') or f'{width}x{height} @ 60fps' not in texts:
            raise ValueError('Prior host MCP response not verified: ' + name)
    return evidence, report


def config_xml(allowed):
    path = json.dumps(str(allowed))
    return (
        '# ROVOR local one-use read-only MCP stage; do not commit this file.\n'
        'sandbox_mode = "read-only"\n'
        'approval_policy = "on-request"\n'
        '[mcp_servers.fcpxml]\n'
        'enabled = true\n'
        'required = true\n'
        'command = "uvx"\n'
        'args = ["--no-build", "--python", "3.11", "--with", "cryptography==46.0.5", '
        '"--from", "fcp-mcp-server==0.27.2", "fcp-mcp-server"]\n'
        'enabled_tools = ["inspect"]\n'
        'default_tools_approval_mode = "prompt"\n'
        'startup_timeout_sec = 180\n'
        'tool_timeout_sec = 60\n'
        '[mcp_servers.fcpxml.env]\n'
        'FCP_PROJECTS_DIR = ' + path + '\n'
        'FCP_PROJECTS_DIRS = ' + path + '\n'
        'FCP_MCP_AUTOPUSH = "0"\n'
        'FCP_MCP_INDEX = "off"\n'
        'FCP_WATCH_DIR = ""\n'
        'UV_NO_BUILD = "1"\n'
    )


def make_stage(evidence, output):
    source, report = prove(evidence)
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; choose a new directory')
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Evidence and output must not overlap')
    output.mkdir(mode=0o700, parents=False)
    project = output / 'project'
    project.mkdir(mode=0o700)
    allowed = project / 'fixtures'
    allowed.mkdir(mode=0o700)
    config_dir = project / '.openinterpreter'
    config_dir.mkdir(mode=0o700)
    for name, width, height in [('landscape', 1920, 1080), ('portrait', 1080, 1920)]:
        fixture(allowed / (name + '.fcpxml'), width, height)
    sentinel = project / 'sentinel.fcpxml'
    sentinel.write_text('<fcpxml version="1.13"><event name="OUTSIDE_ROOT_SENTINEL"/></fcpxml>\n')
    config_dir.joinpath('config.toml').write_text(config_xml(allowed))
    project.joinpath('AGENTS.md').write_text(
        '# Jane: one-time FCP MCP read-only verification\n\n'
        'Use the fcpxml inspect tool only, with manual approval for each invocation.\n'
        'First verify the MCP server is connected, not merely listed in config.\n'
        'Call inspect.analyze_timeline on fixtures/landscape.fcpxml and '
        'fixtures/portrait.fcpxml (both 60fps), then on sentinel.fcpxml; '
        'the sentinel outside FCP_PROJECTS_DIRS must be refused.\n'
        'Use absolute paths within this stage. Do not call shell, execute code, '
        'open other files, use write/edit/preview/deliver tools or initiate any paid '
        'model request without operator consent. No client files or original libraries.\n'
        'Report actual tool output and errors; a registration list is not an MCP handshake.\n'
    )
    manifest = {
        'schema_version': 1,
        'status': 'staged_not_interpreter_verified',
        'source_receipt_status': report['status'],
        'source_server_version': report['server']['version'],
        'evidence_dir': str(source),
        'project': str(project),
        'allowed_fcp_root': str(allowed),
        'landscape': str(allowed / 'landscape.fcpxml'),
        'portrait': str(allowed / 'portrait.fcpxml'),
        'outside_root_sentinel': str(sentinel),
        'local_provider_request_started': False,
        'interpreter_mcp_client_verified': False,
        'native_final_cut_operated': False,
        'allowed_mcp_tools': ['inspect']
    }
    (output / 'stage-receipt.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    print('\nNext: run from Mac Terminal (not from GitHub):')
    print('cd ' + json.dumps(str(project)) + ' && interpreter mcp list && interpreter mcp get fcpxml')
    print('Then, only if effective config is correct and you opt in to a model call:')
    print('cd ' + json.dumps(str(project)) + ' && interpreter')
    print('In the TUI, check /debug-config and /mcp before manually asking Jane to inspect.')
    print('Nothing has invoked Open Interpreter, a model, Final Cut or the MCP server.')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path,
                        help='Prior Mac output folder with passed_direct_mcp/receipt.json')
    parser.add_argument('--output', required=True, type=Path,
                        help='New empty stage root; refuses overwrite')
    args = parser.parse_args(argv)
    make_stage(args.evidence, args.output)


if __name__ == '__main__':
    main()
