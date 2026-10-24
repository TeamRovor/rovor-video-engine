#!/usr/bin/env python3
"""Jane: one-shot, exactly-once native Final Cut isolated-library job.

Intended as a future Walter/Jane local worker adapter: one bounded command
with one immutable ID, stages, host evidence, and a safety gate. No model,
no FCPXML, no exports and NO writes to existing user libraries. If called
twice with the same ID, it ONLY reports the existing result; it NEVER retries.
Creation requires --create. Without it, only an explicit dry-run is performed.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time

import fcp_jane_library_bootstrap as bootstrap
import fcp_jane_library_failure_probe as probe

JOB_ID = re.compile(r'^[a-z0-9][a-z0-9_-]{2,55}$')
RECEIPT_MAX = 16384
REPORT_NAME = bootstrap.REPORT


def root_for(home):
    base = home / 'Documents' / 'Rovor'
    if not base.is_dir() or base.is_symlink():
        raise ValueError('Authorized local ROVOR root missing or unsafe')
    return base


def path_for(base, job_id):
    if not isinstance(job_id, str) or not JOB_ID.fullmatch(job_id):
        raise ValueError('Job ID must be a bounded lowercase alphanumeric slug')
    dest = base / (bootstrap.BOOTSTRAP_PREFIX + job_id)
    if dest.parent != base or dest.is_symlink():
        raise ValueError('Unsafe job path')
    return dest


def known_attempt(path):
    """Recover exactly once; never run again after any receipt or output."""
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Existing job path is unsafe; refusing reuse')
    receipt = path / REPORT_NAME
    if receipt.is_symlink() or not receipt.is_file():
        return {
            'status': 'existing_job_without_valid_receipt_no_retry',
            'job_dir': str(path),
            'native_library_app_selected_verified': False,
            'xml_import_attempted': False,
            'native_gui_attempted_again': False,
        }
    if receipt.stat().st_size > RECEIPT_MAX:
        raise ValueError('Receipt too large; refusing replay')
    obj = json.loads(receipt.read_bytes())
    if (not isinstance(obj, dict)
            or obj.get('target_library') != str(bootstrap.expected_library(path))
            or obj.get('xml_import_attempted') is not False
            or obj.get('status') not in (
                'prepared_no_native_app_action',
                'ui_create_attempt_started',
                'ui_create_failed_unverified',
                'ui_create_exception_unverified',
                'ui_create_acknowledged_checking_filesystem',
                'native_library_not_observed',
                'native_library_folder_created_app_selection_unverified')):
        raise ValueError('Existing receipt inconsistent; refusing replay')
    return {
        'status': 'previous_job_observed_no_retry',
        'previous_status': obj['status'],
        'job_dir': str(path),
        'last_ui_stage': obj.get('last_ui_stage'),
        'error_class': obj.get('error_class'),
        'apple_error_number': obj.get('apple_error_number'),
        'library_directory_observed': bootstrap.expected_library(path).is_dir(),
        'native_library_app_selected_verified': False,
        'xml_import_attempted': False,
        'native_gui_attempted_again': False,
    }


def legacy_marker(path):
    """Only stat() a known legacy default library. No contents are read."""
    if path.is_symlink() or not path.is_dir():
        return {'present': False}
    try:
        st = path.stat()
        return {'present': True, 'mtime_ns': st.st_mtime_ns}
    except OSError:
        return {'present': False}


def onepass(home, job_id, *, create=False, ui_read=probe.ui_read,
            prepare=bootstrap.prepare_isolated, create_native=bootstrap.create_library):
    base = root_for(home)
    folder = path_for(base, job_id)
    prior = known_attempt(folder)
    if prior is not None:
        return prior
    if not create:
        return {
            'status': 'dry_run_only',
            'proposed_job_dir': str(folder),
            'unique_library_name': bootstrap.unique_library_name(folder),
            'native_gui_attempted': False,
            'xml_import_attempted': False,
            'model_turn_started': False,
        }
    preflight = ui_read()
    # A submenu may not be exposed until it is expanded. Do not consider
    # library_menu=false a blocker. No write if application isn't present.
    if (preflight.get('ui_status') != 'read_only_menu_inspection'
            or preflight.get('app') != 'RUNNING'
            or preflight.get('windows', 0) < 1
            or preflight.get('sheets') != 0
            or preflight.get('file_menu') != 'true'
            or preflight.get('new_menu') != 'true'):
        return {
            'status': 'native_ui_preflight_failed_no_job_created',
            'reason': 'Final Cut UI is not in a safe New Library starting state',
            'ui': preflight,
            'native_gui_attempted': False,
            'xml_import_attempted': False,
        }
    legacy = home / 'Movies' / 'Untitled.fcpbundle'
    before = legacy_marker(legacy)
    output, state = prepare(folder, home=home)
    result = create_native(output, state)
    after = legacy_marker(legacy)
    changed = (before.get('present') and after.get('present')
               and before.get('mtime_ns') != after.get('mtime_ns'))
    # The previous wrong-target incident was caused by XML import.
    # Here no XML or project payload is ever sent. If a pre-existing FCP
    # library changes from app autosave, record that fact without attribution.
    after_ui = ui_read()
    return {
        'status': 'library_created_app_selection_unverified'
                  if result['status'] == 'native_library_folder_created_app_selection_unverified'
                  else 'library_bootstrap_not_verified',
        'native_status': result['status'],
        'job_dir': str(output),
        'target_library': result['target_library'],
        'target_library_exists': Path(result['target_library']).is_dir(),
        'last_ui_stage': result.get('last_ui_stage'),
        'error_class': result.get('error_class'),
        'apple_error_number': result.get('apple_error_number'),
        'preexisting_untitled_library_present': bool(before.get('present')),
        'preexisting_library_mtime_changed_unattributed': bool(changed),
        'app_ui_after_attempt': after_ui,
        'native_library_app_selected_verified': False,
        'xml_import_attempted': False,
        'model_turn_started': False,
        'native_gui_attempted_again': False,
        'next_gate': 'Confirm exact intended library is open/selected in FCP before XML',
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job-id', required=True,
                   help='Stable ID: same ID is NEVER executed more than once')
    p.add_argument('--create', action='store_true',
                   help='Explicitly allow one native File/New/Library attempt')
    args = p.parse_args(argv)
    try:
        result = onepass(Path.home(), args.job_id, create=args.create)
        print(json.dumps(result, indent=2))
        return 0 if result['status'] in (
            'dry_run_only', 'previous_job_observed_no_retry',
            'library_created_app_selection_unverified') else 2
    except Exception as exc:
        print('Jane onepass refused: ' + type(exc).__name__ + ': ' +
              str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
