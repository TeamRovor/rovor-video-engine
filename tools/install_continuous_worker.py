#!/usr/bin/env python3
"""Roll the existing research LaunchAgent to an immutable paced runtime.

Dry-run by default. Recovery preserves an installed continuous worker's claim
budget and spacing; legacy-loop migration uses 144/day and 601-second spacing.
Existing failed IDs never replay; preflight blockers prevent service changes.
Only the existing service is changed. STOP and rollback protect failed activation.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import time
import uuid

from omniroute_dispatch_pacing import LABEL, snapshot, recommended_interval


def configured_budget(args):
    values = []
    for flag in ('--max-claims-per-day', '--min-interval-seconds'):
        if args.count(flag) != 1 or args.index(flag) + 1 >= len(args):
            raise ValueError('Missing or repeated installed budget')
        values.append(int(args[args.index(flag) + 1]))
    cap, interval = values
    if not 1 <= cap <= 144 or interval < recommended_interval(cap):
        raise ValueError('Unsafe installed budget')
    return cap, interval


def rollout_preflight(state, config):
    import ghost_omniroute_job
    from omniroute_continuous import queue_health
    blockers = []
    cap, interval = configured_budget(config['ProgramArguments'])
    with snapshot(state) as conn:
        health = queue_health(conn, state, max_claims=cap, interval=interval, now=time.time())
    if os.path.lexists(Path(state) / 'STOP'):
        blockers.append('stop_requested')
    if health['consecutive_recorded_failures'] >= 3:
        blockers.append('failure_circuit_requires_review')
    if health['running']:
        blockers.append('existing_work_running')
    try:
        ghost_omniroute_job.background_preflight()
    except ValueError:
        blockers.append('background_route_or_gateway_auth_unverified')
    return blockers


def atomic_write(path, blob):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('Invalid deployment file')
    fd, name = tempfile.mkstemp(prefix='.rovor-continuous-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(blob)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def build_config(original, runtime):
    if original.get('Label') != LABEL:
        raise ValueError('Unexpected LaunchAgent label')
    args = original.get('ProgramArguments')
    if not isinstance(args, list) or len(args) < 2 or Path(args[1]).name not in {
            'ghost_worker_loop.py', 'omniroute_continuous.py'}:
        raise ValueError('Unexpected installed executor')
    def argument(flag):
        if args.count(flag) != 1 or args.index(flag) + 1 >= len(args):
            raise ValueError('Missing or repeated installed option')
        return args[args.index(flag) + 1]
    state, workspace = argument('--state'), argument('--workspace')
    python = args[0]
    cap, interval = (configured_budget(args) if Path(args[1]).name ==
                     'omniroute_continuous.py' else (144, 601))
    cadence = original.get('StartInterval', 301)
    if type(cadence) is not int or not 1 <= cadence <= 3600:
        raise ValueError('Unsafe installed schedule')
    result = dict(original)
    result.update(ProgramArguments=[python, str(Path(runtime) / 'tools/omniroute_continuous.py'),
        '--state', state, '--workspace', workspace, '--max-claims-per-day', str(cap),
        '--min-interval-seconds', str(interval), '--approve-continuous-research'],
        StartInterval=cadence, RunAtLoad=True, KeepAlive=False)
    return result, Path(state)


def activate(plist, proposed, state, *, run=subprocess.run, uid=None):
    """Restore the original plist/service with STOP held on uncertain activation."""
    plist, state = Path(plist), Path(state)
    stop = state / 'STOP'
    if os.path.lexists(stop):
        raise ValueError('Existing STOP must remain respected')
    with snapshot(state) as conn:
        if conn.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
            raise ValueError('Active job must finish before rollout')
    target = f'gui/{os.getuid() if uid is None else uid}/{LABEL}'
    domain = target.rsplit('/', 1)[0]
    if run(['launchctl', 'print', target], capture_output=True, timeout=10).returncode:
        raise ValueError('Existing service was not positively observed')
    original = plist.read_bytes()
    token = ('ROVOR continuous rollout ' + str(uuid.uuid4()) + '\n').encode()
    fd = os.open(stop, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(token)
    backup = plist.with_name(plist.name + '.before-continuous-' + uuid.uuid4().hex)
    paused = changed = False
    import ghost_worker
    conn = ghost_worker.connect(state)
    try:
        # Hold the claim lock through bootout: an older process that checked
        # STOP just before rollout cannot sneak a new claim between checks.
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
            raise ValueError('A job started before STOP; rollout paused')
        if run(['launchctl', 'bootout', target], capture_output=True, timeout=10).returncode:
            raise ValueError('Existing service could not be paused')
        paused = True
        conn.execute('COMMIT')
        atomic_write(backup, original)
        atomic_write(plist, plistlib.dumps(proposed))
        changed = True
        if run(['launchctl', 'bootstrap', domain, str(plist)],
               capture_output=True, timeout=10).returncode:
            raise ValueError('New service bootstrap failed')
        if run(['launchctl', 'print', target], capture_output=True, timeout=10).returncode:
            raise ValueError('New service presence was not verified')
        if stop.is_symlink() or stop.read_bytes() != token:
            raise ValueError('STOP ownership changed; will not clear it')
        stop.unlink()
        # The first RunAtLoad may have observed STOP. Schedule one real tick now.
        # Once STOP is cleared the new service may already own a live job.
        # Do not boot it out merely because kickstart reports it is active.
        tick_requested = run(['launchctl', 'kickstart', target],
                             capture_output=True, timeout=10).returncode == 0
        cap, interval = configured_budget(proposed['ProgramArguments'])
        return {'status': 'same_service_activated_receipt_pending',
                'max_claims_24h': cap, 'min_interval_seconds': interval,
                'first_tick_requested': tick_requested,
                'model_completion_verified': False, 'second_service_created': False}
    except Exception:
        if conn.in_transaction:
            conn.execute('ROLLBACK')
        if not os.path.lexists(stop):
            fd = os.open(stop, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(token)
        if changed:
            run(['launchctl', 'bootout', target], capture_output=True, timeout=10)
            atomic_write(plist, original)
        if paused:
            run(['launchctl', 'bootstrap', domain, str(plist)],
                capture_output=True, timeout=10)
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise ValueError('Existing Mac host required')
    runtime = Path(__file__).resolve().parent.parent
    for command in (['git', '-C', str(runtime), 'rev-parse', 'HEAD'],
                    ['git', '-C', str(runtime), 'status', '--porcelain']):
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        if (command[-1] == 'HEAD' and result.stdout.strip() != args.expected_commit
                or command[-1] == '--porcelain' and result.stdout.strip()):
            raise ValueError('Immutable clean candidate commit required')
    plist = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
    if plist.is_symlink() or not plist.is_file():
        raise ValueError('Existing ordinary LaunchAgent required')
    config, state = build_config(plistlib.loads(plist.read_bytes()), runtime)
    if state.is_symlink() or stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise ValueError('Existing private worker state required')
    blockers = rollout_preflight(state, config)
    if not args.apply:
        cap, interval = configured_budget(config['ProgramArguments'])
        print(json.dumps({'status': 'dry_run_blocked' if blockers else 'dry_run',
                          'activation_ready': not blockers, 'blockers': blockers,
                          'max_claims_24h': cap,
                          'min_interval_seconds': interval, 'model_requests': 0,
                          'catalogue_assignments': 168, 'state_modified': False}))
        return 0
    if blockers:
        raise ValueError('Rollout prerequisites require review')
    # Compile the tick before stopping a working service; this does not run code.
    compile((runtime / 'tools/omniroute_continuous.py').read_text(),
            'omniroute_continuous.py', 'exec')
    print(json.dumps(activate(plist, config, state), sort_keys=True))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print(json.dumps({'status': 'rollout_blocked_or_rolled_back',
                          'STOP_may_be_held': True, 'private_error_exposed': False}))
        raise SystemExit(2)
