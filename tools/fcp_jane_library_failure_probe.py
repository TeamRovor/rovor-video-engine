#!/usr/bin/env python3
"""Read-only Jane isolated library bootstrap failure diagnosis.

Inspects ONLY prior Jane bootstrap receipt, expected test library's existence,
and small booleans for current Final Cut window / File > New > Library menu
availability. Sends NO keystrokes, clicks, import events, or app activation.
Never enumerates or logs the user's other library/project names.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from fcp_jane_library_bootstrap import BOOTSTRAP_PREFIX, LIBRARY_BASENAME, REPORT

UI_SCRIPT = r'''
tell application "System Events"
    if not (exists process "Final Cut Pro") then return "APP|MISSING"
    tell process "Final Cut Pro"
        set findings to "APP|RUNNING"
        try
            set findings to findings & linefeed & "FRONTMOST|" & (frontmost as text)
        on error
            set findings to findings & linefeed & "FRONTMOST|UNKNOWN"
        end try
        try
            set findings to findings & linefeed & "WINDOWS|" & ((count of windows) as text)
            if (count of windows) > 0 then
                set findings to findings & linefeed & "SHEETS|" & ((count of sheets of front window) as text)
            end if
        on error
            set findings to findings & linefeed & "WINDOWS|UNKNOWN"
        end try
        try
            set hasFile to exists menu bar item "File" of menu bar 1
            set findings to findings & linefeed & "FILE_MENU|" & (hasFile as text)
            if hasFile then
                try
                    set hasNew to exists menu item "New" of menu 1 of menu bar item "File" of menu bar 1
                    set findings to findings & linefeed & "NEW_MENU|" & (hasNew as text)
                    if hasNew then
                        try
                            set hasLibrary to exists menu item "Library" of menu 1 of menu item "New" of menu 1 of menu bar item "File" of menu bar 1
                            set findings to findings & linefeed & "LIBRARY_MENU|" & (hasLibrary as text)
                        on error errText number errNo
                            set findings to findings & linefeed & "LIBRARY_MENU|ERROR"
                            set findings to findings & linefeed & "MENU_ERRNO|" & (errNo as text)
                        end try
                    end if
                on error errText number errNo
                    set findings to findings & linefeed & "NEW_MENU|ERROR"
                    set findings to findings & linefeed & "MENU_ERRNO|" & (errNo as text)
                end try
            end if
        on error errText number errNo
            set findings to findings & linefeed & "FILE_MENU|ERROR"
            set findings to findings & linefeed & "MENU_ERRNO|" & (errNo as text)
        end try
        return findings
    end tell
end tell
'''


def error_category(stderr):
    """Never echo raw Automation stderr; it may mention private window names."""
    lower = (stderr or '').lower()
    if any(x in lower for x in ('not authorized', 'not allowed', 'accessibility',
                                 'permission', '-1743', '-25211', '-1719')):
        return 'macos_automation_or_accessibility_denied'
    if 'timed out' in lower:
        return 'macos_ui_reply_timeout'
    if 'can’t get' in lower or "can't get" in lower or '-1728' in lower:
        return 'ui_element_not_found'
    if 'syntax error' in lower or '-2741' in lower:
        return 'applescript_syntax'
    return 'unclassified_ui_read_error'


def parse_ui(lines):
    if not isinstance(lines, str) or len(lines) > 16384:
        return {'ui_status': 'invalid_or_oversized_reply'}
    allowed = {
        'APP': {'RUNNING', 'MISSING'},
        'FRONTMOST': {'true', 'false', 'UNKNOWN'},
        'FILE_MENU': {'true', 'false', 'ERROR'},
        'NEW_MENU': {'true', 'false', 'ERROR'},
        'LIBRARY_MENU': {'true', 'false', 'ERROR'}
    }
    result = {}
    for line in lines.strip().splitlines():
        if '|' not in line:
            return {'ui_status': 'invalid_reply'}
        k, v = line.split('|', 1)
        if k in allowed:
            if v not in allowed[k] or k in result:
                return {'ui_status': 'invalid_reply'}
            result[k.lower()] = v
        elif k in ('WINDOWS', 'SHEETS'):
            if v != 'UNKNOWN':
                if not re.fullmatch(r'\d{1,3}', v):
                    return {'ui_status': 'invalid_reply'}
                n = int(v)
                if n > 100:
                    return {'ui_status': 'invalid_reply'}
                result[k.lower()] = n
            else:
                result[k.lower()] = None
        elif k == 'MENU_ERRNO':
            if not re.fullmatch(r'-?\d{1,6}', v):
                return {'ui_status': 'invalid_reply'}
            result['menu_error_number'] = int(v)
        else:
            return {'ui_status': 'invalid_reply'}
    if result.get('app') not in ('RUNNING', 'MISSING'):
        return {'ui_status': 'invalid_reply'}
    result['ui_status'] = 'read_only_menu_inspection'
    result['ui_controls_used'] = False
    result['native_library_app_selected_verified'] = False
    return result


def ui_read(run=subprocess.run):
    try:
        process = run(['/usr/bin/osascript', '-e', UI_SCRIPT],
                      timeout=15, check=False, capture_output=True, text=True)
        if process.returncode:
            return {
                'ui_status': 'query_failed',
                'error_category': error_category(process.stderr),
                'osascript_exit_code': process.returncode,
                'ui_controls_used': False,
            }
        return parse_ui(process.stdout)
    except subprocess.TimeoutExpired:
        return {'ui_status': 'query_timed_out', 'ui_controls_used': False}
    except OSError:
        return {'ui_status': 'osascript_unavailable', 'ui_controls_used': False}


def diagnose(job, home=None, run=subprocess.run):
    home = home or Path.home()
    root = home / 'Documents' / 'Rovor'
    job = job.expanduser().absolute()
    if (root.is_symlink() or job.is_symlink() or job.parent != root
            or not job.name.startswith(BOOTSTRAP_PREFIX) or not job.is_dir()):
        raise ValueError('Must target one existing Jane isolated-library job')
    receipt_path = job / REPORT
    if (receipt_path.is_symlink() or not receipt_path.is_file()
            or receipt_path.stat().st_size > 16384):
        raise ValueError('Missing or unsafe Jane library bootstrap receipt')
    receipt = json.loads(receipt_path.read_bytes())
    expected = job / (LIBRARY_BASENAME + '.fcpbundle')
    if (not isinstance(receipt, dict)
            or receipt.get('target_library') != str(expected)
            or receipt.get('xml_import_attempted') is not False
            or receipt.get('status') not in (
                'prepared_no_native_app_action',
                'ui_create_attempt_started',
                'ui_create_failed_unverified',
                'ui_create_exception_unverified',
                'ui_create_acknowledged_checking_filesystem',
                'native_library_not_observed',
                'native_library_folder_created_app_selection_unverified')):
        raise ValueError('Receipt not a recognized isolated, no-XML job')
    if expected.is_symlink():
        raise ValueError('Native test library symlink unexpected')
    return {
        'status': 'jane_read_only_bootstrap_diagnosis',
        'job_dir': str(job),
        'previous_status': receipt['status'],
        'previous_error_class': receipt.get('error_class'),
        'previous_osascript_exit_code': receipt.get('error_code'),
        'intended_library_exists_now': expected.is_dir(),
        'ui': ui_read(run=run),
        'native_library_app_selected_verified': False,
        'xml_import_attempted': False,
        'existing_library_contents_examined': False,
        'no_clicks_imports_retries_or_file_writes': True,
        'note': ('Native Save dialog could have different AX hierarchy; this '
                 'probe checks menu availability without manipulating FCP. '
                 'Prior error detail was not preserved by old bootstrap.'),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job', required=True, type=Path)
    args = p.parse_args(argv)
    try:
        print(json.dumps(diagnose(args.job), indent=2))
        return 0
    except Exception as e:
        print('Jane read-only bootstrap diagnosis refused: ' +
              type(e).__name__ + ': ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
