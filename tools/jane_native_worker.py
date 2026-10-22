#!/usr/bin/env python3
"""Run the existing blank Final Cut import through the durable Jane worker.

Default is a read-only plan. --execute allows ONE native diagnostic job. No AI
model, service installation, personal media or publishing is involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

import fcp_native_auto_import as native
import ghost_worker as worker
import ghost_worker_loop as loop


def candidate_folder(root):
    """Reuse the newest valid prepared candidate, never rerun prior setup."""
    folders = sorted((p for p in root.glob('fcp-native-import-*')
                      if p.is_dir() and not p.is_symlink()),
                     key=lambda p: p.name, reverse=True)
    for folder in folders:
        try:
            native.candidates_from_receipt(folder)
        except (ValueError, OSError, ET.ParseError):
            continue
        return folder
    raise ValueError('No validated native candidate found; preserve the previous Mac candidate receipt')


def run(root, execute=False):
    root = Path(root).expanduser().resolve(strict=True)
    candidates = candidate_folder(root)
    source_receipt = json.loads((candidates / 'native-candidate-receipt.json').read_text())
    identity = {'version': 1, 'fcpxml_sha256': source_receipt['fcpxml_sha256']}
    key = 'jane-native-' + hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode()).hexdigest()
    state = root / 'jane-native-worker-state'
    result = {'candidates': str(candidates), 'dedupe_key': key,
              'state': str(state), 'native_timeline_verified': False,
              'model_turn_started': False, 'execute': execute}
    if not execute:
        return result
    prior = status(root)
    manual_receipts = [item for item in prior['receipts']
                       if Path(item['path']).parent.name.startswith('fcp-jane-auto-')]
    with worker.connect(state) as conn:
        existing = conn.execute('SELECT id FROM jobs WHERE dedupe_key=?', (key,)).fetchone()
        if not existing and manual_receipts:
            raise ValueError('An earlier manual native import exists; inspect --status before starting another job')
        job = existing['id'] if existing else worker.enqueue(
            conn, worker.NATIVE_KIND,
            {'candidates': candidates.relative_to(root).as_posix()}, key)
        row = conn.execute('SELECT status FROM jobs WHERE id=?', (job,)).fetchone()
        if row['status'] == 'queued':
            result['loop'] = loop.poll(conn, root, state, worker_id='jane-native',
                                       max_jobs=1, max_seconds=420, poll_seconds=2,
                                       allow_native_import=True)
        row = conn.execute('SELECT status,attempts,result,error FROM jobs WHERE id=?', (job,)).fetchone()
        result.update(job_id=job, job=dict(row))
    return result


def status(root):
    """Inspect persisted work without creating a database or retrying anything."""
    root = Path(root).expanduser().resolve(strict=True)
    state = root / 'jane-native-worker-state'
    db = state / 'jobs.sqlite3'
    result = {'status': 'not_initialized', 'jobs': [], 'receipts': [],
              'native_timeline_verified': False}
    if state.is_symlink() or db.is_symlink():
        raise ValueError('Worker status paths may not be symlinks')
    if db.is_file():
        with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as conn:
            conn.row_factory = sqlite3.Row
            result['jobs'] = [dict(row) for row in conn.execute(
                'SELECT id,status,attempts,error FROM jobs WHERE kind=? ORDER BY created_at DESC LIMIT 10',
                (worker.NATIVE_KIND,))]
        result['status'] = 'recorded'
    # Include the existing manual attempt so its pending command can be
    # inspected before this queue has been deployed on the Mac.
    folders = [root / ('native-import-' + row['id']) for row in result['jobs']]
    folders.extend(sorted(root.glob('fcp-jane-auto-*'), reverse=True)[:3])
    for folder in folders:
        file = folder / 'native-auto-import-receipt.json'
        if folder.is_symlink() or file.is_symlink() or not file.is_file():
            continue
        try:
            if file.stat().st_size > 128000:
                raise ValueError('Receipt exceeds status size bound')
            receipt = json.loads(file.read_text())
            result['receipts'].append({'path': str(file), 'receipt': receipt})
        except (ValueError, OSError) as exc:
            result['receipts'].append({'path': str(file), 'error': str(exc)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--status', action='store_true', help='Read queue and import checkpoints; never dispatch')
    args = parser.parse_args(argv)
    try:
        if args.execute and args.status:
            raise ValueError('Use --status alone; status never executes')
        root = Path.home() / 'Documents' / 'Rovor'
        result = status(root) if args.status else run(root, args.execute)
        print(json.dumps(result, indent=2))
        return 0 if not args.execute or result['job']['status'] == 'succeeded' else 2
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
