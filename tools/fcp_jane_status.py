#!/usr/bin/env python3
"""Read-only status inspection of Jane's FIRST native FCP import attempt.

No app launch, AppleScript, network, model use, file mutation or retries.
Only reads known private ROVOR per-job receipts. A missing receipt is never
reported as an import failure or success.
"""
import argparse
import json
from pathlib import Path
import sys

PREFIX = 'fcp-jane-auto-'
RECEIPT = 'native-auto-import-receipt.json'
MAX_RECEIPT = 65536


def status(root, job=None):
    root = root.expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError('ROVOR work root does not exist or is a symlink')
    if job is None:
        candidates = [
            child for child in root.iterdir()
            if child.name.startswith(PREFIX) and child.is_dir()
            and not child.is_symlink() and child.parent == root
        ]
        if not candidates:
            return {
                'status': 'no_jane_auto_import_job_found',
                'action_required': 'none',
                'native_timeline_verified': False,
            }
        job = max(candidates, key=lambda p: p.name)
    else:
        job = job.expanduser().absolute()
        if (job.parent != root or not job.name.startswith(PREFIX)
                or job.is_symlink() or not job.is_dir()):
            raise ValueError('Job must be one existing Jane output inside root')
    receipt = job / RECEIPT
    state = {
        'job_dir': str(job),
        'read_only': True,
        'native_timeline_verified': False,
        'native_library_exists': False,
        'apple_event_sent': None,
        'original_media_modified': None,
    }
    if receipt.is_symlink() or not receipt.is_file():
        state.update(status='no_receipt_yet_preparing_or_interrupted',
                     next_action='Read command output; do not blindly rerun')
        return state
    if receipt.stat().st_size > MAX_RECEIPT:
        raise ValueError('Job receipt oversized')
    data = json.loads(receipt.read_bytes())
    if not isinstance(data, dict) or not isinstance(data.get('status'), str):
        raise ValueError('Invalid Jane receipt format')
    target = data.get('target_library')
    expected = job / 'ROVOR-Jane-Test.fcpbundle'
    if target != str(expected):
        raise ValueError('Receipt names unexpected native library target')
    if expected.is_symlink():
        raise ValueError('Refusing symlinked library target')
    xml = [
        job / 'landscape-auto.fcpxml',
        job / 'portrait-auto.fcpxml',
    ]
    state.update(
        status=data['status'],
        last_dispatched=data.get('last_dispatched'),
        updated_at_utc=data.get('updated_at_utc'),
        apple_event_dispatch_attempted=data.get('apple_event_dispatch_attempted'),
        apple_event_sent=data.get('apple_event_sent'),
        library_creation_observed=data.get('library_creation_observed'),
        native_library_exists=expected.is_dir(),
        native_timeline_verified=False,  # app timeline is NOT inspected by this command
        original_media_modified=data.get('original_media_modified'),
        xml_candidates_present=all(p.is_file() and not p.is_symlink() for p in xml),
        error=data.get('error'),
        next_action=('Do not rerun. Inspect status / local macOS Automation dialog'
                     if data['status'] not in ('apple_events_sent_timeline_unverified',)
                     else 'Native project/timeline proof still needed'),
    )
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path,
                   default=Path.home() / 'Documents' / 'Rovor')
    p.add_argument('--job', type=Path)
    a = p.parse_args(argv)
    try:
        print(json.dumps(status(a.root, a.job), indent=2))
        return 0
    except Exception as exc:
        print('Jane read-only status error: ' + type(exc).__name__ +
              ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
