#!/usr/bin/env python3
"""Pinned FCPXML MCP smoke: synthetic files only, no model or native app calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import time
import xml.etree.ElementTree as ET


def fixture(path, width, height):
    root = ET.Element('fcpxml', version='1.13')
    resources = ET.SubElement(root, 'resources')
    ET.SubElement(resources, 'format', id='r1', frameDuration='1/60s', width=str(width), height=str(height), colorSpace='1-1-1 (Rec. 709)')
    library = ET.SubElement(root, 'library')
    event = ET.SubElement(library, 'event', name='ROVOR Synthetic MCP Test')
    project = ET.SubElement(event, 'project', name='ROVOR Diagnostic ' + path.stem)
    sequence = ET.SubElement(project, 'sequence', format='r1', duration='1s', tcStart='0s', tcFormat='NDF', audioLayout='stereo', audioRate='48k')
    spine = ET.SubElement(sequence, 'spine')
    ET.SubElement(spine, 'gap', name='Gap', offset='0s', start='0s', duration='1s')
    ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)


class Client:
    def __init__(self, command, env, cwd=None):
        self.child = subprocess.Popen(command, env=env, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.child.stdout, selectors.EVENT_READ)
        self.selector.register(self.child.stderr, selectors.EVENT_READ)
        self.buffer = bytearray()
        self.errors = bytearray()
        self.total = 0
        self.deadline = time.monotonic() + 180
        self.sequence = 0

    def send(self, message):
        self.child.stdin.write((json.dumps({'jsonrpc': '2.0', **message}) + '\n').encode())
        self.child.stdin.flush()

    def request(self, method, params=None):
        self.sequence += 1
        self.send({'id': self.sequence, 'method': method, 'params': params or {}})
        while time.monotonic() < self.deadline:
            while b'\n' in self.buffer:
                line, _, remaining = self.buffer.partition(b'\n')
                self.buffer = bytearray(remaining)
                if not line.strip():
                    continue
                message = json.loads(line)
                if message.get('id') == self.sequence:
                    if 'error' in message:
                        raise ValueError('MCP returned protocol error: ' + str(message['error']))
                    return message['result']
            events = self.selector.select(min(1, max(0, self.deadline - time.monotonic())))
            for key, _ in events:
                chunk = os.read(key.fileobj.fileno(), 8192)
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    continue
                self.total += len(chunk)
                if self.total > 2_000_000:
                    raise ValueError('MCP output exceeded smoke-test bound')
                if key.fileobj is self.child.stdout:
                    self.buffer.extend(chunk)
                else:
                    self.errors.extend(chunk[:max(0, 16384 - len(self.errors))])
            if self.child.poll() is not None and not self.selector.get_map():
                raise ValueError(f'MCP exited before replying (exit code {self.child.returncode}); inspect private server-error.txt')
        raise TimeoutError('MCP startup/test exceeded 180 seconds')

    def close(self):
        try:
            os.killpg(self.child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError:
            if self.child.poll() is None:
                self.child.kill()
        self.child.wait(timeout=5)
        self.selector.close()
        for stream in [self.child.stdin, self.child.stdout, self.child.stderr]:
            stream.close()


def text_result(result):
    return '\n'.join(block.get('text', '') for block in result.get('content', []))


def verify(client, allowed, outside):
    init = client.request('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {}, 'clientInfo': {'name': 'rovor-deterministic-smoke', 'version': '1'}})
    if init.get('serverInfo', {}).get('version') != '0.27.2':
        raise ValueError('Unexpected MCP server version')
    client.send({'method': 'notifications/initialized'})
    tools = client.request('tools/list')
    if 'inspect' not in [tool['name'] for tool in tools['tools']]:
        raise ValueError('Pinned server did not advertise inspect')
    results = {}
    for name, dimensions in [('landscape', '1920x1080'), ('portrait', '1080x1920')]:
        result = client.request('tools/call', {'name': 'inspect', 'arguments': {'action': 'analyze_timeline', 'args': {'filepath': str(allowed / (name + '.fcpxml'))}}})
        text = text_result(result)
        if dimensions not in text or '@ 60fps' not in text or result.get('isError'):
            raise ValueError('Synthetic timeline dimensions/frame rate not confirmed: ' + name)
        results[name] = result
    refused = client.request('tools/call', {'name': 'inspect', 'arguments': {'action': 'analyze_timeline', 'args': {'filepath': str(outside)}}})
    denial = text_result(refused)
    refusal_wording = ('escapes the allowed roots', 'outside allowed roots')
    if (not denial.startswith('Validation error: ') or
            not any(phrase in denial.lower() for phrase in refusal_wording) or
            'FCP_PROJECTS_DIRS' not in denial or
            'OUTSIDE_ROOT_SENTINEL' in denial):
        raise ValueError('Outside-root read did not produce the expected authorization refusal')
    return {'server': init['serverInfo'], 'available_tool_names': [t['name'] for t in tools['tools']], 'fixture_results': results, 'outside_root_refusal': refused, 'native_final_cut_operated': False, 'interpreter_mcp_client_verified': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.expanduser().absolute()
    if output.exists():
        raise ValueError('Use a new output directory; preserve earlier evidence')
    output.mkdir(mode=0o700)

    # Record failures in early host preparation too (missing DTD, xmllint, uvx).
    # These errors previously escaped before a receipt could be written.
    report = {
        'status': 'failed',
        'stage': 'prepare_fixtures',
        'native_final_cut_operated': False,
        'interpreter_mcp_client_verified': False,
    }
    client = None
    try:
        allowed = output / 'fixtures'
        allowed.mkdir(mode=0o700)
        outside = output / 'sentinel.fcpxml'
        outside.write_text('<fcpxml version="1.13"><event name="OUTSIDE_ROOT_SENTINEL"/></fcpxml>')
        source = Path('/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_13.dtd')
        dtd = output / 'installed-1.13.dtd'
        shutil.copyfile(source, dtd)
        report['installed_dtd_sha256'] = hashlib.sha256(dtd.read_bytes()).hexdigest()
        report['stage'] = 'validate_fixtures'
        for name, w, h in [('landscape', 1920, 1080), ('portrait', 1080, 1920)]:
            path = allowed / (name + '.fcpxml')
            fixture(path, w, h)
            subprocess.run(['xmllint', '--nonet', '--noout', '--dtdvalid', str(dtd), str(path)], check=True)

        env = dict(os.environ)
        env.update(FCP_PROJECTS_DIR=str(allowed), FCP_PROJECTS_DIRS=str(allowed),
                   FCP_MCP_AUTOPUSH='0', FCP_MCP_INDEX='off', FCP_WATCH_DIR='',
                   UV_TOOL_DIR=str(output / 'uv-tools'), UV_CACHE_DIR=str(output / 'uv-cache'),
                   UV_PYTHON_INSTALL_DIR=str(output / 'uv-python'))
        report['stage'] = 'start_mcp'
        # No optional AI/transcription extras and no provider credentials configured.
        client = Client(['uvx', '--no-build', '--python', '3.11', '--with', 'cryptography==46.0.5',
                         '--from', 'fcp-mcp-server==0.27.2', 'fcp-mcp-server'], env, cwd=output)
        report['stage'] = 'verify_mcp'
        report.update(verify(client, allowed, outside))
        report['status'] = 'passed_direct_mcp'
        report['stage'] = 'complete'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if client is not None:
            # Snapshot exit status BEFORE cleanup could terminate a healthy server.
            report['mcp_exit_code_before_cleanup'] = client.child.poll()
            report['server_stderr_bytes_retained'] = len(client.errors)
            report['server_stderr_sha256'] = hashlib.sha256(client.errors).hexdigest()
            try:
                client.close()
            except Exception as exc:
                report['status'] = 'needs_review'
                report['cleanup_error'] = f'{type(exc).__name__}: {exc}'
        # Error logs and evidence are saved under the newly created private root.
        (output / 'server-error.txt').write_bytes(client.errors if client is not None else b'')
        (output / 'receipt.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('Private test evidence:', output)
    return 0 if report['status'] == 'passed_direct_mcp' else 2

if __name__ == '__main__':
    raise SystemExit(main())
