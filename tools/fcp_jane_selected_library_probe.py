#!/usr/bin/env python3
"""Read-only, fail-closed evidence for an isolated Jane library selected in FCP.

Does not activate Final Cut, click, type, import XML, create/modify any project,
open the library or read its contents. Uses only System Events AX inspection
and lsof of that exact Final Cut process. Personal UI titles and other open
file paths are NEVER emitted. This is a point-in-time observation only; a
matching selection does NOT authorize future FCPXML import or edits.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import fcp_jane_library_bootstrap as bootstrap

MAX_RECEIPT = 16384
MAX_UI = 2048
MAX_LSOF = 2097152
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{2,55}$')
NATIVE_NAMES = frozenset({'CurrentVersion.flexolibrary', 'CurrentVersion.fcpevent'})

# This is a READ-ONLY AX lookup; no activates, clicks, keystrokes, or menu actions.
# An exact match in the SELECTED ROW of a library outline is required.
# Titles of unrelated projects are examined only in the Mac's private AX
# process and never returned. AX errors and exceeding time budget fail closed.
UI_SCRIPT = r'''
on run argv
    if (count of argv) is not 1 then return "STATE|INVALID_INPUT"
    set expectedName to item 1 of argv
    tell application "System Events"
        if not (exists process "Final Cut Pro") then return "STATE|APP_MISSING"
        tell process "Final Cut Pro"
            if frontmost is false then return "STATE|NOT_FRONTMOST"
            if (count of windows) is 0 then return "STATE|NO_WINDOW"
            if (count of sheets of front window) is greater than 0 then return "STATE|SHEET_PRESENT"
            set appPid to unix id
            set hitCount to 0
            set inspected to 0
            try
                set allItems to entire contents of front window
                repeat with anItem in allItems
                    set inspected to inspected + 1
                    if inspected > 1300 then return "STATE|UI_BUDGET_EXCEEDED"
                    try
                        if (role of anItem as text) is "AXRow" then
                            set isSelected to false
                            try
                                set isSelected to (value of attribute "AXSelected" of anItem) as boolean
                            end try
                            if isSelected then
                                set displayed to ""
                                try
                                    set displayed to name of anItem as text
                                end try
                                if displayed is not expectedName then
                                    try
                                        set displayed to value of static text 1 of anItem as text
                                    end try
                                end if
                                if displayed is expectedName then
                                    set ancestor to anItem
                                    set inOutline to false
                                    repeat 8 times
                                        try
                                            set ancestor to parent of ancestor
                                            if (role of ancestor as text) is "AXOutline" then
                                                set inOutline to true
                                                exit repeat
                                            end if
                                        on error
                                            exit repeat
                                        end try
                                    end repeat
                                    if inOutline then set hitCount to hitCount + 1
                                end if
                            end if
                        end if
                    end try
                end repeat
            on error
                return "STATE|AX_FAILED"
            end try
            if hitCount is 1 then
                return "STATE|READY" & linefeed & "PID|" & (appPid as text) & linefeed & "SELECTED|true"
            end if
            return "STATE|READY" & linefeed & "PID|" & (appPid as text) & linefeed & "SELECTED|false"
        end tell
    end tell
end run
'''


def inspect_target(home, job_id):
    if not isinstance(job_id, str) or not ID.fullmatch(job_id):
        raise ValueError('Invalid bounded Jane job ID')
    root = home / 'Documents' / 'Rovor'
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Missing or redirected ROVOR root')
    job = root / (bootstrap.BOOTSTRAP_PREFIX + job_id)
    if job.is_symlink() or not job.is_dir():
        raise ValueError('Jane isolated job not present or redirected')
    bundle = bootstrap.expected_library(job)
    receipt = job / bootstrap.REPORT
    if receipt.is_symlink() or not receipt.is_file():
        raise ValueError('Missing trusted Jane creation receipt')
    if receipt.stat().st_size > MAX_RECEIPT:
        raise ValueError('Oversized Jane creation receipt')
    info = json.loads(receipt.read_bytes())
    if (not isinstance(info, dict)
            or info.get('schema_version') != 2
            or info.get('status') != 'native_library_folder_created_app_selection_unverified'
            or info.get('target_library') != str(bundle)
            or info.get('xml_import_attempted') is not False
            or info.get('native_library_directory_observed') is not True):
        raise ValueError('Native creation receipt not eligible for selection proof')
    if bundle.is_symlink() or not bundle.is_dir():
        raise ValueError('Expected native bundle missing or redirected')
    return job, bundle


def parse_ui(response):
    if not isinstance(response, str) or len(response) > MAX_UI:
        return {'ui_status': 'invalid_response', 'selected_exact_row': False}
    reply = response.strip()
    denied = {'INVALID_INPUT', 'APP_MISSING', 'NOT_FRONTMOST', 'NO_WINDOW',
              'SHEET_PRESENT', 'UI_BUDGET_EXCEEDED', 'AX_FAILED'}
    if reply.startswith('STATE|') and reply[6:] in denied:
        return {'ui_status': reply[6:].lower(), 'selected_exact_row': False}
    matched = re.fullmatch(r'STATE\|READY\nPID\|([1-9][0-9]{0,7})\nSELECTED\|(true|false)', reply)
    if not matched:
        return {'ui_status': 'invalid_response', 'selected_exact_row': False}
    return {'ui_status': 'read_only_selected_row_query', 'pid': int(matched[1]),
            'selected_exact_row': matched[2] == 'true'}


def ui_query(expected, run=subprocess.run):
    try:
        reply = run(['/usr/bin/osascript','-e',UI_SCRIPT,expected],
                    timeout=20,capture_output=True,text=True,check=False)
    except subprocess.TimeoutExpired:
        return {'ui_status': 'timed_out', 'selected_exact_row': False}
    except OSError:
        return {'ui_status': 'unavailable', 'selected_exact_row': False}
    if reply.returncode:
        return {'ui_status': 'denied_or_failed', 'selected_exact_row': False}
    return parse_ui(reply.stdout)


def has_native_handle(stdout, bundle, pid):
    """Return boolean ONLY; no unrelated file names, paths or contents."""
    if not isinstance(stdout, str) or len(stdout.encode('utf-8')) > MAX_LSOF:
        return False
    seen_pid = False
    matched_handle = False
    root = str(bundle)
    for line in stdout.splitlines():
        if len(line) > 4096:
            return False
        if line.startswith('p'):
            if line != 'p'+str(pid) or seen_pid:
                return False
            seen_pid = True
        if not line.startswith('n'):
            continue
        p = line[1:]
        # Exact logical containment and native FCP DB basename.
        # Avoid resolving links inside any third-party/private library.
        if not p.startswith(root + os.sep):
            continue
        relative = p[len(root)+1:]
        parts = Path(relative).parts
        # A synthetic file in Original Media/Render Files must never stand
        # in for an actual native library DB. Accept only the canonical
        # bundle root flexolibrary DB or a shallow event fcpevent DB.
        if (relative == 'CurrentVersion.flexolibrary'
                or (2 <= len(parts) <= 3
                    and all(part not in ('', '.', '..', 'Original Media',
                                         'Optimized Media', 'Proxy Media',
                                         'Render Files', 'Analysis Files')
                            for part in parts[:-1])
                    and parts[-1] == 'CurrentVersion.fcpevent')):
            matched_handle = True
    return seen_pid and matched_handle


def native_handle_query(pid, bundle, run=subprocess.run):
    # PID comes from the strictly validated System Events reply, never user input.
    try:
        reply = run(['/usr/sbin/lsof','-nP','-p',str(pid),'-Fn'],
                    timeout=12,capture_output=True,text=True,check=False)
    except subprocess.TimeoutExpired:
        return {'handle_status': 'timed_out', 'native_db_handle': False}
    except OSError:
        return {'handle_status': 'unavailable', 'native_db_handle': False}
    if reply.returncode != 0:
        return {'handle_status': 'unavailable_or_denied', 'native_db_handle': False}
    return {'handle_status': 'checked_read_only',
            'native_db_handle': has_native_handle(reply.stdout, bundle, pid)}


def verify(home, job_id, ui=ui_query, handles=native_handle_query):
    job, bundle = inspect_target(home, job_id)
    observed = ui(bundle.stem)
    selected = observed.get('selected_exact_row') is True
    inspected_handles = (
        handles(observed['pid'], bundle)
        if selected and observed.get('ui_status') == 'read_only_selected_row_query'
           and type(observed.get('pid')) is int
        else {'handle_status': 'not_queried', 'native_db_handle': False}
    )
    proof = bool(selected and inspected_handles.get('native_db_handle') is True)
    return {
        'status': 'selected_library_evidence_observed' if proof else 'selection_unverified',
        'job_dir': str(job),
        'target_library': str(bundle),
        'native_library_app_selected_verified': proof,
        'ui_status': observed.get('ui_status', 'invalid_response'),
        'selected_exact_row': selected,
        'handle_status': inspected_handles.get('handle_status','invalid'),
        'native_db_handle': inspected_handles.get('native_db_handle') is True,
        'read_only': True,
        'no_xml_import_or_app_changes': True,
        'timeline_or_import_verified': False,
        'next_gate': 'Selection is point-in-time only; import stays disabled',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job-id',required=True)
    args = parser.parse_args(argv)
    try:
        result = verify(Path.home(),args.job_id)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0 if result['native_library_app_selected_verified'] else 2
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({'status':'selection_verification_refused',
                          'reason':type(exc).__name__,
                          'native_library_app_selected_verified':False,
                          'read_only':True,
                          'no_xml_import_or_app_changes':True}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
