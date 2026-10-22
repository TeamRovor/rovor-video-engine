#!/usr/bin/env python3
"""Jane read-only macOS native import diagnosis. NEVER sends an Apple event.

Checks one already-attempted disposable Final Cut import, process presence and
bounded library discovery. Does not launch Final Cut, call AppleScript, ask
for access, read personal media, alter projects, or re-dispatch anything.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path.home() / 'Documents' / 'Rovor'
JOB_PREFIX = 'fcp-jane-auto-'
RECEIPT_NAME = 'native-auto-import-receipt.json'
MAX_RECEIPT = 65536
SCAN_LIMIT = 800


def constrained_job(root, job):
    root = root.expanduser().absolute()
    job = job.expanduser().absolute()
    if (root.is_symlink() or not root.is_dir() or job.is_symlink()
            or job.parent != root or not job.name.startswith(JOB_PREFIX)
            or not job.is_dir()):
        raise ValueError('Use one existing disposable Jane job directly in the ROVOR root')
    return root, job


def read_receipt(job):
    path = job / RECEIPT_NAME
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RECEIPT:
        raise ValueError('Expected bounded, non-symlinked original job receipt')
    d = json.loads(path.read_bytes())
    if not isinstance(d, dict) or not isinstance(d.get('status'), str):
        raise ValueError('Invalid Jane receipt')
    expected = job / 'ROVOR-Jane-Test.fcpbundle'
    if d.get('target_library') != str(expected):
        raise ValueError('Receipt points outside expected disposable library')
    return d, expected


def validate_import_xml(job, target):
    results = {}
    for label in ('landscape', 'portrait'):
        file = job / (label + '-auto.fcpxml')
        if (file.is_symlink() or not file.is_file()
                or file.stat().st_size > 256000):
            results[label] = 'missing_or_unsafe'
            continue
        try:
            top = ET.parse(file).getroot()
            options = [e.get('value') for e in
                       top.findall('./import-options/option')
                       if e.get('key') == 'library location']
            format_elem = top.find('./resources/format')
            sequence = top.find('./library/event/project/sequence')
            if (top.tag == 'fcpxml' and top.get('version') == '1.13'
                    and options == [target.as_uri()]
                    and format_elem is not None
                    and format_elem.get('frameDuration') == '1/60s'
                    and sequence is not None
                    and sequence.get('duration') == '30s'
                    and not top.findall('.//asset')):
                results[label] = 'import_target_and_empty_30s_sequence_present'
            else:
                results[label] = 'unexpected_xml_or_target'
        except (ET.ParseError, OSError, ValueError):
            results[label] = 'invalid_xml'
    return results


def process_names(run=subprocess.run):
    """Collect only process executable NAMES, never args/env/user messages."""
    try:
        result = run(['/bin/ps', '-axo', 'comm='], check=False,
                     capture_output=True, text=True, timeout=8)
        if result.returncode or len(result.stdout) > 1_000_000:
            return {'process_visibility': 'unavailable'}
        names = [x.strip().rsplit('/', 1)[-1] for x in result.stdout.splitlines()]
        return {
            'process_visibility': 'observed',
            'final_cut_process_present': 'Final Cut Pro' in names,
            'osascript_process_present': 'osascript' in names,
            'python_process_present': any(x in ('Python', 'Python3', 'python3') for x in names),
        }
    except (OSError, subprocess.TimeoutExpired):
        return {'process_visibility': 'unavailable'}


def nearby_libraries(root, job, home, limit=SCAN_LIMIT):
    """Enumerate only one level below known roots; never traverse other data."""
    results = []
    inspected = 0
    scopes = [(job, 'job'), (root, 'rovor-root'), (home / 'Movies', 'movies')]
    for directory, scope in scopes:
        if directory.is_symlink() or not directory.is_dir():
            continue
        try:
            for child in directory.iterdir():
                inspected += 1
                if inspected > limit:
                    return {'scan_status': 'bounded_scan_limit',
                            'matches': results, 'inspected': limit}
                if (child.suffix.lower() == '.fcpbundle'
                        and child.name.startswith(('ROVOR-', 'Rovor-', 'Jane-'))
                        and not child.is_symlink() and child.is_dir()):
                    results.append({'scope': scope, 'name': child.name})
        except (OSError, PermissionError):
            continue
    return {'scan_status': 'limited_3_directories', 'matches': results,
            'inspected': inspected}


def inspect(root, job, home=None, process_run=subprocess.run):
    root, job = constrained_job(root, job)
    receipt, target = read_receipt(job)
    if target.is_symlink():
        raise ValueError('Refusing symlink target')
    home = home or Path.home()
    proc = process_names(run=process_run)
    result = {
        'status': 'diagnosis_only_no_native_app_control',
        'job_dir': str(job),
        'original_job_status': receipt['status'],
        'original_job_error': receipt.get('error'),
        'last_dispatched': receipt.get('last_dispatched'),
        'apple_event_returned_zero': receipt.get('apple_event_sent') is True,
        'expected_library_created': target.is_dir(),
        'native_timeline_verified': False,
        'portrait_dispatched': receipt.get('last_dispatched') == 'portrait',
        'xml_files': validate_import_xml(job, target),
        'app_installed': Path('/Applications/Final Cut Pro.app').is_dir(),
        'process': proc,
        'discovery': nearby_libraries(root, job, home),
        'no_second_import_started': True,
        'diagnosis_note': ('AppleScript return zero indicates event handling acknowledged, '
                           'NOT that an XML project was imported. A blocked dialog or app '
                           'import issue remains possible. No UI was queried.'),
        'next_step': ('If expected library is absent, check app dialog/permissions '
                      'in a separate native app probe; do not replay previous job.'),
    }
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--job', type=Path, required=True)
    args = ap.parse_args(argv)
    try:
        print(json.dumps(inspect(args.root, args.job), indent=2))
        return 0
    except Exception as exc:
        print('Jane native diagnosis refused: ' + type(exc).__name__ +
              ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
