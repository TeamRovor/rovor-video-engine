#!/usr/bin/env python3
"""Run one explicitly approved OmniRoute draft in the existing Mac queue.

Leaves STOP present and the existing LaunchAgent unloaded. Never schedules,
installs, replays, enables native adapters, or approves generated output.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import ghost_worker as worker
import ghost_omniroute_job as omni
import omniroute_workpack_runner as runner
import omniroute_draft_review as review

DEDUPE = 'rovor-first-approved-omniroute-foreground-v1'
PACKET = 'supervisor-resilience'
LABEL = 'com.rovor.ghost-worker.readonly'
JOBS = {PACKET: DEDUPE,
        'overnight-acceptance': 'rovor-overnight-acceptance-checklist-v1'}


def verify_queue(conn, dedupe=DEDUPE):
    if conn.execute('SELECT 1 FROM jobs WHERE dedupe_key=?', (dedupe,)).fetchone():
        raise ValueError('This approved attempt already exists; inspect it, never replay')
    if conn.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
        raise ValueError('A worker job is running; leave it alone')
    kinds = sorted(worker.ALLOWED | {worker.OMNI_KIND})
    marks = ','.join('?' for _ in kinds)
    if conn.execute(f"SELECT 1 FROM jobs WHERE status='queued' AND kind IN ({marks})", kinds).fetchone():
        raise ValueError('Other eligible jobs are queued; refusing to run a different job')


def ensure_stop(path):
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if path.is_symlink() or not path.is_file():
            raise ValueError('Unsafe STOP marker')
    else:
        with os.fdopen(fd, 'w') as stream:
            stream.write('Paused after bounded OmniRoute foreground attempt\n')


def service_absent_from_domain(result):
    """A failed service query alone never proves an unloaded LaunchAgent."""
    if result.returncode or not isinstance(result.stdout,str):
        return False
    inside=False
    for line in result.stdout.splitlines():
        if line.strip() == 'services = {':
            inside=True
        elif inside:
            if line.strip() == '}':
                return True
            if LABEL in line.split():
                return False
    return False


def run_one(conn, state, workspace, *, run=subprocess.run, execute=worker.run_once,
            packet=PACKET):
    dedupe=JOBS[packet]
    stop = state / 'STOP'
    ensure_stop(stop)
    target = f'gui/{os.getuid()}/{LABEL}'
    observed = run(['launchctl', 'print', target], capture_output=True, timeout=10)
    if observed.returncode:
        domain=run(['launchctl','print',f'gui/{os.getuid()}'],capture_output=True,text=True,timeout=10)
        if not service_absent_from_domain(domain):
            raise ValueError('Existing LaunchAgent state not confirmed; STOP retained')
    else:
        unloaded = run(['launchctl', 'bootout', target], capture_output=True, timeout=10)
        if unloaded.returncode:
            raise ValueError('Could not pause existing LaunchAgent; STOP retained')
        if run(['launchctl', 'print', target], capture_output=True, timeout=10).returncode == 0:
            raise ValueError('LaunchAgent still loaded; STOP retained')
    verify_queue(conn,dedupe)
    jid = worker.enqueue(conn, worker.OMNI_KIND, {'packet': packet}, dedupe)
    try:
        stop.unlink()
        result = execute(conn, workspace, owner='rovor-approved-omni-foreground',
                         allow_omniroute_model_use=True, omniroute_queue_job_id=jid)
        if not result or result['id'] != jid:
            raise ValueError('Exact approved job did not execute; inspect queue')
        return result
    finally:
        ensure_stop(stop)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--approve-one-free-job', action='store_true')
    parser.add_argument('--packet',choices=tuple(JOBS),default=PACKET)
    args = parser.parse_args(argv)
    if not args.approve_one_free_job:
        print(json.dumps({'status': 'no_approval_no_calls', 'scheduling_enabled': False}))
        return 0
    if sys.platform != 'darwin':
        raise ValueError('This entrypoint requires the existing Mac host')
    home = Path.home()
    state = home / 'Documents/Codex/2026-10-22/new-chat/jane-worker-state'
    workspace = home / 'Documents/Rovor'
    for path in (state, workspace):
        if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_dir():
            raise ValueError('Existing canonical worker folders required')
    if stat.S_IMODE(state.stat().st_mode) & 0o077:
        raise ValueError('Existing worker state must be private')
    root = Path(__file__).resolve().parents[1]
    packet=args.packet
    runner.load_packet(root, packet)
    print(json.dumps({'phase': 'verify_live_free_only_catalog'}), flush=True)
    catalog = omni.read_combo_catalog()
    omni.verify_route(packet, catalog)
    # Resolve credentials before queue claim; never print them or CLI output.
    print(json.dumps({'phase': 'verify_existing_keychain_key'}), flush=True)
    runner.access_key()
    conn = worker.connect(state)
    try:
        verify_queue(conn,JOBS[packet])
        print(json.dumps({'phase': 'pause_existing_schedule_then_one_job'}), flush=True)
        result = run_one(conn, state, workspace,packet=packet)
        print(json.dumps(result, sort_keys=True))
        if 'error' in result:
            return 2
        folder = state / 'omniroute-drafts' / result['id']
        verdict = review.inspect(root, folder, packet)
        print(json.dumps({'private_receipt': str(folder / (packet + '.receipt.json')),
                          'quality_status': verdict['status'],
                          'reasons': verdict.get('reasons', []),
                          'approval_granted': False, 'STOP_present': (state/'STOP').is_file(),
                          'scheduling_enabled': False}, sort_keys=True))
        return 0 if verdict['status'] == 'draft_ready_for_human_review' else 2
    finally:
        conn.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # Private upstream errors must not disclose credentials/provider output.
        print(json.dumps({'status': 'blocked_no_automatic_retry',
                          'error_class': type(exc).__name__, 'scheduling_enabled': False}))
        raise SystemExit(2)
