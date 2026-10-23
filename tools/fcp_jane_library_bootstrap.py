#!/usr/bin/env python3
"""Jane: isolated native Final Cut library bootstrap, never imports XML.

The user's first live test proves "open FCPXML" can land in pre-existing
~/Movies/Untitled.fcpbundle despite an import-options target. Thus DO NOT
send another XML until this gate has created a fresh uniquely named library
and the native app's active library has been verified separately.

This script creates only a NEW library using Final Cut's File > New > Library
UI workflow. It never closes or edits existing libraries, never imports
any XML, never touches media, and never runs an AI model. It requires
foreground logged-in macOS Accessibility access. The script fails closed
if the Save dialog cannot be identified / navigated exactly. Do not blindly
retry after a partly completed OS dialog.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from fcp_jane_native_probe import constrained_job, read_receipt

ROOT = Path.home() / 'Documents' / 'Rovor'
APP = Path('/Applications/Final Cut Pro.app')
LIBRARY_BASENAME = 'ROVOR-Jane-Isolated'
BOOTSTRAP_PREFIX = 'fcp-jane-library-'
REPORT = 'native-library-bootstrap-receipt.json'

# Frontmost checks BEFORE UI keystrokes. Only opens Save panel, sets the
# target filename and navigates to a new empty job directory; only then Save.
# The path is supplied as argv, never interpolated into source statements.
APPLE_SCRIPT = r'''
on run argv
    if (count of argv) is not 3 then error "Expected directory, name and folder label"
    set destinationFolder to item 1 of argv
    set targetName to item 2 of argv
    set folderLabel to item 3 of argv
    if targetName is not "ROVOR-Jane-Isolated" then error "Library name not allowlisted"
    tell application "Final Cut Pro" to activate
    tell application "System Events"
        if not (exists process "Final Cut Pro") then error "FCP missing"
        tell process "Final Cut Pro"
            if frontmost is false then error "Final Cut must be frontmost"
            if (count of windows) < 1 then error "No FCP windows"
            if (count of sheets of front window) > 0 then error "Existing FCP sheet present; do not interfere"
            if not (exists menu bar item "File" of menu bar 1) then error "No File menu"
            if not (exists menu item "New" of menu 1 of menu bar item "File" of menu bar 1) then error "No File/New menu"
            if not (exists menu item "Library" of menu 1 of menu item "New" of menu 1 of menu bar item "File" of menu bar 1) then error "No File/New/Library command"
            click menu item "Library" of menu 1 of menu item "New" of menu 1 of menu bar item "File" of menu bar 1
            delay 0.8
            if (count of sheets of front window) is not 1 then error "New Library Save sheet not identified"
            tell sheet 1 of front window
                if not (exists button "Save") then error "Expected a native Save sheet"
                if not (exists text field 1) then error "Expected library name text field"
                set value of text field 1 to targetName
            end tell
            -- macOS standard Save-panel Go To Folder. Never uses clipboard.
            keystroke "g" using {command down, shift down}
            delay 0.7
            -- Must identify Go To Folder combo box before typing; no blind keystrokes.
            if (count of sheets of sheet 1 of front window) is less than 1 then error "Go To Folder sub-sheet not found"
            tell sheet 1 of sheet 1 of front window
                if not (exists combo box 1) then error "Go To Folder combo box absent"
                set value of combo box 1 to destinationFolder
                if not (exists button "Go") then error "Go To Folder Go button absent"
                click button "Go"
            end tell
            delay 0.7
            if (count of sheets of front window) is not 1 then error "Save sheet changed unexpectedly"
            tell sheet 1 of front window
                if not (exists button "Save") then error "Save button disappeared"
                if not (exists text field 1) then error "Filename field missing"
                if (value of text field 1 as text) is not targetName then error "Library name changed unexpectedly"
                -- Save destination must show the exact freshly created folder.
                -- A successful "Go" action alone is NOT evidence of location.
                set locationVerified to false
                repeat with locationPopUp in every pop up button
                    try
                        if (value of locationPopUp as text) is folderLabel then set locationVerified to true
                    end try
                    try
                        if (name of locationPopUp as text) is folderLabel then set locationVerified to true
                    end try
                end repeat
                if locationVerified is false then error "Save destination could not be verified; NO SAVE"
            end tell
            -- Important: the Save target directory is job-unique and empty.
            -- User/host must verify resulting fcpbundle, not AppleScript exit.
            click button "Save" of sheet 1 of front window
        end tell
    end tell
end run
'''


def atomic_report(folder, info):
    tmp = folder / ('receipt-' + secrets.token_hex(12) + '.tmp')
    try:
        with tmp.open('x') as out:
            json.dump(info, out, indent=2)
            out.write('\n')
        os.replace(tmp, folder / REPORT)
    finally:
        if tmp.exists():
            tmp.unlink()


def checkpoint(folder, report, status, **kwargs):
    report.update(kwargs)
    report['status'] = status
    report['updated_at_utc'] = datetime.now(timezone.utc).isoformat()
    atomic_report(folder, report)
    print('JANE LIBRARY ' + json.dumps({
        'status': status,
        'target': report['target_library'],
        'native_library_created': report['native_library_created'],
        'xml_import_attempted': False,
    }), flush=True)


def prepare(job, output, home=None):
    home = home or Path.home()
    root = home / 'Documents' / 'Rovor'
    _, job = constrained_job(root, job)
    prior, old_target = read_receipt(job)
    if (prior['status'] != 'native_library_not_observed'
            or prior.get('last_dispatched') != 'landscape'
            or old_target.exists() or old_target.is_symlink()):
        raise ValueError('Expected the confirmed original wrong-library trial')
    output = output.expanduser().absolute()
    if (output.parent != root or not output.name.startswith(BOOTSTRAP_PREFIX)
            or output.is_symlink() or output.exists()
            or root.is_symlink()):
        raise ValueError('Output must be a never-used fcp-jane-library-* folder in ROVOR')
    output.mkdir(mode=0o700)
    target = output / (LIBRARY_BASENAME + '.fcpbundle')
    report = {
        'schema_version': 1,
        'status': 'prepared_no_native_app_action',
        'prior_job': str(job),
        'target_library': str(target),
        'native_library_created': False,
        'native_library_directory_observed': False,
        'native_library_app_selected_verified': False,
        'xml_import_attempted': False,
        'existing_library_mutation_assessed': False,
        'model_turn_started': False,
    }
    atomic_report(output, report)
    return output, report


def create_library(output, report, run=subprocess.run, clock=time.monotonic,
                   sleeper=time.sleep, timeout=30):
    target = Path(report['target_library'])
    if (report['status'] != 'prepared_no_native_app_action'
            or target.exists() or target.is_symlink()):
        raise ValueError('Refusing existing or previously attempted native library')
    if not APP.is_dir():
        raise ValueError('Final Cut Pro missing at expected path')
    # Record attempt BEFORE any GUI action.
    checkpoint(output, report, 'ui_create_attempt_started')
    try:
        process = run(
            ['/usr/bin/osascript', '-e', APPLE_SCRIPT,
             str(output), LIBRARY_BASENAME, output.name],
            capture_output=True, text=True, timeout=65, check=False)
        if process.returncode:
            checkpoint(output, report, 'ui_create_failed_unverified',
                       error_code=process.returncode,
                       error_class='applescript_or_accessibility')
            return report
        checkpoint(output, report, 'ui_create_acknowledged_checking_filesystem')
        deadline = clock() + timeout
        while clock() < deadline and not target.is_dir():
            sleeper(1)
        if not target.is_dir():
            checkpoint(output, report, 'native_library_not_observed',
                       note='Do not re-run. Inspect dialog state read-only.')
            return report
        checkpoint(output, report, 'native_library_folder_created_app_selection_unverified',
                   native_library_created=True,
                   native_library_directory_observed=True)
        return report
    except (OSError, subprocess.TimeoutExpired):
        checkpoint(output, report, 'ui_create_exception_unverified',
                   note='No retry; a GUI dialog could still be pending.')
        return report


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--job', required=True, type=Path)
    a.add_argument('--output', required=True, type=Path)
    a.add_argument('--create', action='store_true',
                   help='Explicitly allow opening ONLY the New Library Save panel')
    args = a.parse_args(argv)
    try:
        output, report = prepare(args.job, args.output)
        if args.create:
            report = create_library(output, report)
        print(json.dumps(report, indent=2))
        return 0 if report['status'] in (
            'prepared_no_native_app_action',
            'native_library_folder_created_app_selection_unverified') else 2
    except Exception as exc:
        print('ROVOR Jane library bootstrap refused: ' +
              type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
