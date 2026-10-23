#!/usr/bin/env python3
"""Direct Open Interpreter app-server -> FCP MCP tool-call proof. No AI model turn.

This is NOT a GUI or native Final Cut edit; operates only synthetic staged XML.
Calls app-server's native JSON-RPC MCP tool endpoint with an ephemeral thread
rather than asking a model to perform an action. No model inference is requested.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

from fcp_host_smoke import Client, text_result
from fcp_interpreter_registration import validate_stage, override_for, argv_for

ALLOWED_SERVER = "fcpxml"


def tool_call(client, thread_id, file):
    return client.request('mcpServer/tool/call', {
        'threadId': thread_id,
        'server': ALLOWED_SERVER,
        'tool': 'inspect',
        'arguments': {'action': 'analyze_timeline', 'args': {'filepath': str(file)}},
    })


def verify(stage, interpreter=None):
    root, project, allowed = validate_stage(stage)
    command = interpreter or shutil.which('interpreter')
    if not command:
        raise ValueError('interpreter executable not found')
    env = dict(os.environ)
    env.update(UV_NO_BUILD='1', FCP_MCP_AUTOPUSH='0',
               FCP_MCP_INDEX='off', FCP_WATCH_DIR='')
    # Override one project-specific server even when untrusted; do not read any
    # original FCP libraries or start paid model turns.
    argv = argv_for(command, override_for(allowed), 'app-server')
    client = None
    try:
        client = Client(argv, env, cwd=project)
        initialized = client.request('initialize', {
            'clientInfo': {'name': 'rovor-fcpxml-offline-inspection',
                           'version': '1.0.0'},
            'capabilities': {}
        })
        if 'userAgent' not in initialized:
            raise ValueError('Open Interpreter app-server did not initialize')
        client.send({'method': 'initialized'})
        thread_response = client.request('thread/start', {
            'cwd': str(project), 'ephemeral': True,
            'sandbox': 'read-only', 'approvalPolicy': 'on-request'
        })
        thread_id = thread_response.get('thread', {}).get('id')
        if not isinstance(thread_id, str) or not thread_id:
            raise ValueError('Missing ephemeral app-server thread id')

        statuses = client.request('mcpServerStatus/list', {'threadId': thread_id})
        matching = [row for row in statuses.get('data', [])
                    if row.get('name') == ALLOWED_SERVER]
        if len(matching) != 1:
            raise ValueError('FCP server absent from Interpreter app-server MCP status')
        status = matching[0]
        if 'inspect' not in status.get('tools', {}):
            raise ValueError('Interpreter app-server did not discover FCP inspect tool')
        # Do not silently accept a disconnected or failed status.
        if status.get('toolsError'):
            raise ValueError('Interpreter MCP tools discovery failed')

        results = {}
        for name, dimensions in (('landscape', '1920x1080'),
                                 ('portrait', '1080x1920')):
            result = tool_call(client, thread_id, allowed / (name + '.fcpxml'))
            answer = text_result(result)
            if result.get('isError') or dimensions not in answer or '@ 60fps' not in answer:
                raise ValueError('Interpreter app-server FCP inspect failed for ' + name)
            results[name] = {'expected': dimensions + ' @ 60fps',
                             'response_sha256': __import__('hashlib').sha256(
                                 json.dumps(result, sort_keys=True).encode()).hexdigest()}
        sentinel = project / 'sentinel.fcpxml'
        refusal = tool_call(client, thread_id, sentinel)
        refusal_text = text_result(refusal)
        if not refusal_text.lower().startswith('validation error: ') or \
                'escapes the allowed roots' not in refusal_text.lower():
            raise ValueError('Interpreter app-server did not enforce outside-root refusal')
        result = {
            'status': 'passed_interpreter_appserver_mcp_tool_call',
            'open_interpreter_connected': True,
            'server': ALLOWED_SERVER,
            'inspected': results,
            'outside_root_refused': True,
            'native_final_cut_operated': False,
            'model_turn_started': False,
            'media_modified': False,
        }
        return result
    finally:
        if client is not None:
            client.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(verify(args.stage), indent=2))
    except Exception as exc:
        print(json.dumps({'status': 'failed',
                          'open_interpreter_connected': False,
                          'native_final_cut_operated': False,
                          'error': type(exc).__name__ + ': ' + str(exc)}, indent=2),
              file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
