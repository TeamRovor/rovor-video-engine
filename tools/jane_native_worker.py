#!/usr/bin/env python3
"""Run the existing blank Final Cut import through the durable Jane worker.

Default is a read-only plan. --execute allows ONE native diagnostic job. No AI
model, service installation, personal media or publishing is involved.
"""
import argparse
import hashlib
import json
from pathlib import Path
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
    key = 'jane-native-' + hashlib.sha256(
        str(candidates).encode() + (candidates / 'native-candidate-receipt.json').read_bytes()).hexdigest()
    state = root / 'jane-native-worker-state'
    result = {'candidates': str(candidates), 'dedupe_key': key,
              'state': str(state), 'native_timeline_verified': False,
              'model_turn_started': False, 'execute': execute}
    if not execute:
        return result
    with worker.connect(state) as conn:
        job = worker.enqueue(conn, worker.NATIVE_KIND,
                             {'candidates': candidates.relative_to(root).as_posix()}, key)
        row = conn.execute('SELECT status FROM jobs WHERE id=?', (job,)).fetchone()
        if row['status'] == 'queued':
            result['loop'] = loop.poll(conn, root, state, worker_id='jane-native',
                                       max_jobs=1, max_seconds=420, poll_seconds=2,
                                       allow_native_import=True)
        row = conn.execute('SELECT status,attempts,result,error FROM jobs WHERE id=?', (job,)).fetchone()
        result.update(job_id=job, job=dict(row))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = run(Path.home() / 'Documents' / 'Rovor', args.execute)
        print(json.dumps(result, indent=2))
        return 0 if not args.execute or result['job']['status'] == 'succeeded' else 2
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'blocked', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
