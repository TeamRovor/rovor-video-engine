#!/usr/bin/env python3
"""Compatibility entrypoint for the existing bounded research adapter.

--check is offline. --run uses the user's existing ChatGPT login once and keeps
its receipt outside the disposable research workspace. No scheduler is started.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

LEGACY = ['exec', '--sandbox', 'read-only', '--ask-for-approval', 'untrusted', '--ephemeral', '-']


def command(binary):
    # Approval is a top-level option in the installed Interpreter 0.0.56.
    # on-request keeps approval available; noninteractive requests can fail.
    return [binary, '--ask-for-approval', 'on-request', '--search', 'exec',
            '--sandbox', 'read-only', '--ephemeral', '--ignore-user-config',
            '--skip-git-repo-check',
            '-c', 'features.multi_agent=false', '-']


def check(binary):
    for args, required in [(['--help'], ['--ask-for-approval', 'on-request', '--search']),
                           (['exec', '--help'], ['--sandbox', '--ephemeral', '--ignore-user-config', '--skip-git-repo-check'])]:
        result = subprocess.run([binary] + args, capture_output=True, text=True, timeout=10)
        if result.returncode or any(flag not in result.stdout for flag in required):
            raise ValueError('Installed Interpreter lacks required compatibility options')
    result = subprocess.run(command(binary)[:-1] + ['--help'],
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError('Installed Interpreter rejects the corrected command')


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    binary = shutil.which('interpreter')
    if not binary:
        raise ValueError('Interpreter is not on PATH')
    if args == LEGACY:
        # This shim accepts only the adapter's fixed read-only argument list.
        # Keep bounded startup diagnostics in the PRIVATE answer on failure.
        os.dup2(sys.stdout.fileno(), sys.stderr.fileno())
        os.execv(binary, command(binary))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--approve-model-use', action='store_true')
    parser.add_argument('--output', type=Path)
    opts = parser.parse_args(args)
    check(binary)
    if not opts.run:
        print('PASS: top-level approval and exact corrected exec arguments accepted; no model invoked.')
        return 0
    if not opts.approve_model_use:
        parser.error('--run requires --approve-model-use')
    if opts.output is None:
        parser.error('--output is required for receipts')
    output = opts.output.expanduser().absolute()
    if output.exists():
        raise ValueError('Output already exists; refusing automatic replay. Inspect its receipt first.')
    output.mkdir(mode=0o700, parents=False)
    workspace = output / 'research'
    state = output / 'receipts'
    workspace.mkdir(mode=0o700)
    state.mkdir(mode=0o700)
    packet = {
        'version': 1, 'job_id': 'jane-finalcut-host-001', 'topic': 'final-cut-pro',
        'questions': [
            'Using official Apple documentation, cite URLs for FCPXML import/export and explain its limits versus live Final Cut UI control.',
            'Give a practical workflow for original animated 1920x1080 60fps YouTube videos and 1080x1920 60fps reels, preserving narration and editable sources.',
            'Describe a disposable FCPXML validation/import test and what actual evidence is required before enabling an unattended editing worker.'
        ], 'source_files': []
    }
    (workspace / 'packet.json').write_text(json.dumps(packet, indent=2) + '\n')
    # GitHub contents downloads do not preserve executable mode. Make only
    # this private copy executable; leave the checked-out source unchanged.
    shim = output / 'interpreter-compat.py'
    shim.write_bytes(Path(__file__).read_bytes())
    shim.chmod(0o700)
    # Preserve the existing tested timeout, STOP, output and replay controls.
    import interpreter_research_job as adapter
    packet, sha = adapter.read_packet(workspace, 'packet.json')
    report = adapter.execute(workspace, state, packet, sha,
                             adapter.make_prompt(workspace, packet),
                             interpreter_binary=str(shim), timeout=300)
    print(json.dumps(report, indent=2))
    print('Answer and receipt:', state)
    return 0 if report['status'] == 'completed_unverified' else 2


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('ROVOR host job:', exc, file=sys.stderr)
        raise SystemExit(2)
