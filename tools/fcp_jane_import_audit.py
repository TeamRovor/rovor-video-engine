#!/usr/bin/env python3
"""ROVOR Jane: targeted READ-ONLY scan for own synthetic project markers.

After a native XML import unexpectedly updated a pre-existing 'Untitled'
Final Cut library, inspect only project-directory names and small FCP library
DATABASE/METADATA files for the exact two known ROVOR test identifiers.

Does NOT edit, reopen or export any library; no AppleScript, no app launch,
no personal media, no network, and NO exposure of unrelated project names.
A missing byte string is NOT proof that the project was not imported:
Final Cut's proprietary database can transform, compress, or encode metadata.
"""
import argparse
import json
from pathlib import Path
import sys

import fcp_jane_native_probe as native

MARKERS = {
    'landscape': 'ROVOR NATIVE IMPORT TEST landscape',
    'portrait': 'ROVOR NATIVE IMPORT TEST portrait',
}
DATABASE_FILES = {'CurrentVersion.flexolibrary', 'CurrentVersion.fcpevent'}
DB_SUFFIXES = {'.sqlite', '.sqlite3', '.db'}
SKIP_DIRS = {
    'Original Media', 'Optimized Media', 'Proxy Media', 'Transcoded Media',
    'Render Files', 'Analysis Files', 'High Quality Media',
}
FILE_LIMIT = 1024 * 1024 * 12
TOTAL_LIMIT = 1024 * 1024 * 48
ENTRY_LIMIT = 850
DEPTH_LIMIT = 5


def match_small_file(path, needles, max_bytes):
    """Use short overlapping reads; never return source contents."""
    found = set()
    with path.open('rb') as stream:
        tail = b''
        used = 0
        while used < max_bytes:
            buf = stream.read(min(262144, max_bytes - used))
            if not buf:
                break
            used += len(buf)
            haystack = tail + buf
            for label, variants in needles.items():
                if any(v in haystack for v in variants):
                    found.add(label)
            tail = haystack[-256:]
            if len(found) == len(needles):
                break
    return found


def audit(job, home=None):
    home = home or Path.home()
    root = home / 'Documents' / 'Rovor'
    _, job = native.constrained_job(root, job)
    receipt, expected = native.read_receipt(job)
    if receipt['status'] != 'native_library_not_observed':
        raise ValueError('This audit is only for the documented failed import')
    if receipt.get('last_dispatched') != 'landscape':
        raise ValueError('Only first landscape event should have been sent')
    if expected.exists() or expected.is_symlink():
        raise ValueError('Expected native library state changed; pause audit')
    for label in MARKERS:
        source = job / (label + '-auto.fcpxml')
        if source.is_symlink() or not source.is_file():
            raise ValueError('Known XML file is missing or unsafe')
    lib = home / 'Movies' / 'Untitled.fcpbundle'
    if not lib.is_dir() or lib.is_symlink():
        return {
            'status': 'known_untitled_library_not_present',
            'native_timeline_verified': False,
            'read_only': True,
            'no_import_or_replay': True,
        }
    needles = {
        k: (v.encode('utf-8'), v.encode('utf-16le'), v.encode('utf-16be'))
        for k, v in MARKERS.items()
    }
    found = {key: set() for key in MARKERS}
    used = 0
    inspected = 0
    files_read = 0
    limits_reached = False
    # Walk package without reading any actual media, cached render or thumbnails.
    pending = [(lib, 0)]
    while pending and inspected < ENTRY_LIMIT:
        directory, depth = pending.pop()
        if depth > DEPTH_LIMIT or directory.is_symlink():
            continue
        try:
            entries = list(directory.iterdir())
        except (OSError, PermissionError):
            continue
        for item in entries:
            inspected += 1
            if inspected > ENTRY_LIMIT:
                limits_reached = True
                break
            if item.is_symlink():
                continue
            if item.is_dir():
                for key, marker in MARKERS.items():
                    if item.name == marker:
                        found[key].add('directory_name')
                if depth < DEPTH_LIMIT and item.name not in SKIP_DIRS:
                    pending.append((item, depth + 1))
                continue
            if not item.is_file():
                continue
            if (item.name not in DATABASE_FILES
                    and item.suffix.lower() not in DB_SUFFIXES):
                continue
            try:
                size = item.stat().st_size
                if size > FILE_LIMIT or used + size > TOTAL_LIMIT:
                    limits_reached = True
                    continue
                used += size
                files_read += 1
                for key in match_small_file(item, needles, size):
                    found[key].add('native_database_byte_match')
            except (OSError, PermissionError):
                continue
    return {
        'status': 'read_only_targeted_marker_audit',
        'job_dir': str(job),
        'existing_untitled_library_scanned': True,
        'original_job_status': receipt['status'],
        'marker_presence': {
            k: {
                'found': bool(found[k]),
                'evidence_types': sorted(found[k]),
            } for k in MARKERS
        },
        'preexisting_untitled_library_ownership': 'unattributed',
        'native_timeline_verified': False,
        'database_search_limit_hit': limits_reached or bool(pending),
        'package_entries_inspected': inspected,
        'native_metadata_files_read': files_read,
        'native_metadata_bytes_scanned': used,
        'no_unrelated_names_or_contents_returned': True,
        'no_media_files_read': True,
        'no_import_or_replay': True,
        'conclusion': (
            'Positive exact-name presence may indicate this preexisting library '
            'was the wrong destination; zero matches are INCONCLUSIVE and do '
            'not prove a native project is absent or failed.')
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job', type=Path, required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(audit(a.job.expanduser().absolute()), indent=2))
        return 0
    except Exception as exc:
        print('ROVOR Jane audit refused: ' + type(exc).__name__ +
              ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
