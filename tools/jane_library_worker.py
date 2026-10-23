#!/usr/bin/env python3
"""One explicit, durable Jane native library creation command.

Uses the existing SQLite ghost-worker DB and onepass native UI adapter.
Without --create: no DB, model, app or filesystem writes.
With --create: only a fresh unique FCP library; NEVER imports XML, never
edits or replays an earlier job, never auto-approves/launches a daemon.
Exit code 3 means a one-time GUI attempt was recorded and still needs review;
exit code 2 means the request was refused or not dispatched. Exit 0 is
reserved for read-only status/dry-run, not an unverified GUI result.
This is not a generic unattended executor.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

import fcp_jane_library_onepass as jane
import ghost_worker as worker
import ghost_worker_loop as loop

STATE_NAME = 'jane-native-worker-state'


def resolve_root(home):
    root = home / 'Documents' / 'Rovor'
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Expected existing non-symlinked user ROVOR root')
    return root


def read_status(home):
    """Read only: do not initialize SQLite or run any queued work."""
    base = resolve_root(home)
    state = base / STATE_NAME
    db = state / 'jobs.sqlite3'
    if state.is_symlink() or db.is_symlink():
        raise ValueError('Unsafe redirected worker state')
    if not db.is_file():
        return {'status':'not_initialized','read_only':True,
                'native_library_app_selected_verified':False,'jobs':[]}
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = [dict(row) for row in conn.execute(
            "SELECT id,status,attempts,result,error FROM jobs WHERE kind=? "
            "ORDER BY created_at DESC LIMIT 10", (worker.LIBRARY_KIND,))]
    return {
        'status':'recorded','read_only':True,
        'native_library_app_selected_verified':False,
        'jobs': [{
            'id':row['id'],'status':row['status'],'attempts':row['attempts'],
            'app_selection_verified':False,
            'native_result_status': (
                (json.loads(row['result']) or {}).get('status')
                if row['result'] else None),
            'has_error':bool(row['error']),
        } for row in rows],
    }


def execute(home, job_id, *, create=False):
    root = resolve_root(home)
    # Always validate job ID before opening the persistent queue.
    folder = jane.path_for(root, job_id)
    if not create:
        return jane.onepass(home, job_id, create=False)
    if sys.platform != 'darwin':
        raise ValueError('Native library creation needs foreground macOS')
    state = root / STATE_NAME
    with closing(worker.connect(state)) as conn:
        # A STOP request must not even enqueue a GUI operation; no latent
        # authorized action should be left for an unattended future loop.
        if loop.stop_requested(state):
            return {'status':'stop_requested_no_queue_or_native_action',
                    'job_id':job_id,'xml_import_attempted':False}
        key = 'jane-library-create:' + job_id
        job = worker.enqueue(conn, worker.LIBRARY_KIND,
                             {'job_id':job_id}, key)
        old = conn.execute('SELECT status,attempts,result FROM jobs WHERE id=?',
                           (job,)).fetchone()
        if old['status'] != 'queued':
            return {
                'status':'existing_queued_work_finished_or_started_no_replay',
                'job_id':job,'job_status':old['status'],
                'attempts':old['attempts'],
                'native_gui_attempted_again':False,
                'xml_import_attempted':False,
            }
        # Use the exact SQLite ID, not the oldest task of another kind.
        receipt = worker.run_once(
            conn, root, owner='jane-local-create-once',
            allow_jane_library_create=True, jane_library_only=True,
            jane_queue_job_id=job)
        if not receipt:
            return {'status':'queued_not_dispatched',
                    'job_id':job,
                    'reason':'STOP or concurrent worker owns this job',
                    'xml_import_attempted':False}
        native_result = receipt.get('result')
        # A recorded attempt is not a successful FCP operation. The native
        # package may still be absent and app selection is never proven here.
        observed = (isinstance(native_result, dict)
                    and native_result.get('target_library_exists') is True)
        return {'status':'creation_attempt_recorded',
                'job_id':job,'job_status':receipt['status'],
                'native':native_result,
                'error_class':receipt.get('error'),
                'native_library_folder_observed':bool(observed),
                'review_required':True,
                'native_library_app_selected_verified':False,
                'xml_import_attempted':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group()
    group.add_argument('--create',action='store_true',
                       help='Explicit one-time native library creation approval')
    group.add_argument('--status',action='store_true',
                       help='Read-only worker state, no initialization')
    p.add_argument('--job-id',help='Stable unique slug, never reuse failed IDs')
    args=p.parse_args(argv)
    try:
        if args.status:
            if args.job_id:
                p.error('--status does not require a job ID')
            result=read_status(Path.home())
        else:
            if not args.job_id:
                p.error('--job-id is required for create and dry-run')
            result=execute(Path.home(),args.job_id,create=args.create)
        print(json.dumps(result,indent=2,sort_keys=True))
        if args.create:
            # Exit 3 = the native attempt was recorded, but requires review.
            # Exit 2 = refused/not dispatched. Never exit 0 for an unverified
            # native GUI action: wrappers must not infer success from rc=0.
            return 3 if result['status'] == 'creation_attempt_recorded' else 2
        return 0
    except (ValueError, OSError, sqlite3.Error) as e:
        print(json.dumps({'status':'blocked',
                          'error_class':type(e).__name__,
                          'message':str(e),
                          'native_library_app_selected_verified':False,
                          'xml_import_attempted':False}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
