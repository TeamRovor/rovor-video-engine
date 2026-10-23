#!/usr/bin/env python3
"""Jane: read-only Final Cut UI + default-library forensic probe for failed import.

ONLY inspects the prior disposable job. Does NOT open/import FCPXML, send
files to FCP, create/edit projects, press UI buttons, start the app, or
read files *inside* an FCP library. UI inspection (optional) may require
macOS Accessibility consent. Window names are redacted to category flags.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

import fcp_jane_native_probe as native

# Inspect top-level window titles and sheet counts, NEVER UI contents,
# user text, document content, controls or button clicks.
READ_ONLY_GUI_APPLESCRIPT = r'''
tell application "System Events"
    if not (exists application process "Final Cut Pro") then
        return "APP_NOT_RUNNING"
    end if
    tell process "Final Cut Pro"
        set finalResult to "APP_RUNNING"
        set wins to every window
        set finalResult to finalResult & linefeed & ("WINDOW_COUNT|" & (count of wins))
        repeat with win in wins
            set winTitle to ""
            try
                set winTitle to (name of win as text)
            end try
            set sheetCount to 0
            try
                set sheetCount to count of sheets of win
            end try
            set finalResult to finalResult & linefeed & "WINDOW|" & sheetCount & "|" & winTitle
        end repeat
        return finalResult
    end tell
end tell
'''

WINDOW_CLASSES = {
    'import_dialog': re.compile(r'\b(import|xml)\b', re.I),
    'library_picker': re.compile(r'\b(select|choose|open|library)\b', re.I),
    'error_dialog': re.compile(r'\b(error|warning|invalid|failed|alert)\b', re.I),
}


def classify_window_titles(raw):
    if not isinstance(raw, str) or len(raw) > 64000:
        return {'ui_status': 'unavailable'}
    lines = raw.splitlines()
    if not lines:
        return {'ui_status': 'unavailable'}
    if lines[0] == 'APP_NOT_RUNNING':
        return {'ui_status': 'app_not_running'}
    if lines[0] != 'APP_RUNNING':
        return {'ui_status': 'unexpected_reply'}
    count = None
    flags = {key: False for key in WINDOW_CLASSES}
    sheets_total = 0
    seen = 0
    for line in lines[1:]:
        if line.startswith('WINDOW_COUNT|'):
            try:
                count = int(line.split('|', 1)[1])
            except ValueError:
                return {'ui_status': 'unexpected_reply'}
            if count < 0 or count > 100:
                return {'ui_status': 'window_count_outside_limit'}
            continue
        if line.startswith('WINDOW|'):
            if seen >= 50:
                return {'ui_status': 'window_count_outside_limit'}
            parts = line.split('|', 2)
            if len(parts) != 3:
                return {'ui_status': 'unexpected_reply'}
            try:
                n_sheets = int(parts[1])
            except ValueError:
                return {'ui_status': 'unexpected_reply'}
            if n_sheets < 0 or n_sheets > 50:
                return {'ui_status': 'unexpected_reply'}
            sheets_total += n_sheets
            seen += 1
            title = parts[2]
            for key, pattern in WINDOW_CLASSES.items():
                flags[key] |= bool(pattern.search(title))
    return {'ui_status': 'read_only_window_inspection',
            'window_count': count, 'windows_observed': seen,
            'sheets_observed': sheets_total,
            'window_title_category_flags': flags,
            'window_names_redacted': True,
            'ui_contents_not_read': True,
            'ui_buttons_clicked': False,
            'native_timeline_verified': False}


def gui_status(run=subprocess.run):
    command = ['/usr/bin/osascript', '-e', READ_ONLY_GUI_APPLESCRIPT]
    try:
        r = run(command, capture_output=True, text=True,
                check=False, timeout=12)
        if r.returncode:
            detail = ((r.stderr or '') + ' ' + (r.stdout or '')).lower()
            denied = any(k in detail for k in (
                'not authorized', 'not allowed', 'permission',
                'accessibility', '-1743', '-1719', '-25211'))
            return {'ui_status': 'accessibility_or_automation_denied'
                    if denied else 'ui_query_failed',
                    'exit_code': r.returncode,
                    'native_timeline_verified': False,
                    'ui_buttons_clicked': False}
        return classify_window_titles(r.stdout.strip())
    except subprocess.TimeoutExpired:
        return {'ui_status': 'ui_query_timed_out',
                'native_timeline_verified': False,
                'ui_buttons_clicked': False}
    except OSError:
        return {'ui_status': 'osascript_unavailable',
                'native_timeline_verified': False,
                'ui_buttons_clicked': False}


def stamp(path):
    try:
        st = path.stat()
        return {'creation_utc': datetime.fromtimestamp(
                    getattr(st, 'st_birthtime', st.st_ctime),
                    timezone.utc).isoformat(),
                'modified_utc': datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat()}
    except OSError:
        return None


def analyze(root, job, home=None, run=subprocess.run, with_ui=True):
    home = home or Path.home()
    root, job = native.constrained_job(root, job)
    receipt, target = native.read_receipt(job)
    initial = native.inspect(root, job, home=home, process_run=run)
    default_library = home / 'Movies' / 'Untitled.fcpbundle'
    library_metadata = None
    if default_library.is_dir() and not default_library.is_symlink():
        libstat, jobstat = stamp(default_library), stamp(job)
        library_metadata = {
            'exists': True, 'metadata_only': True,
            'creation_utc': libstat['creation_utc'] if libstat else None,
            'modified_utc': libstat['modified_utc'] if libstat else None,
            'job_directory_creation_utc': jobstat['creation_utc'] if jobstat else None,
            'predates_job': (libstat['creation_utc'] < jobstat['creation_utc']
                             if libstat and jobstat else None),
            'attributed_to_jane': False,
            'library_package_contents_examined': False,
        }
    else:
        library_metadata = {'exists': False,
                            'library_package_contents_examined': False,
                            'attributed_to_jane': False}
    initial['default_untitled_library_metadata'] = library_metadata
    initial['ui'] = gui_status(run=run) if with_ui else {'ui_status': 'skipped'}
    initial['app_ui_observed'] = initial['ui']['ui_status'] == 'read_only_window_inspection'
    initial['no_second_import_started'] = True
    initial['native_timeline_verified'] = False
    initial['result_note'] = ('A library file timestamp and a Final Cut window title '
                              'are not proof that this import succeeded.')
    return initial


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=native.ROOT)
    p.add_argument('--job', type=Path, required=True)
    p.add_argument('--no-ui', action='store_true',
                   help='Skip macOS read-only Accessibility query')
    a = p.parse_args(argv)
    try:
        print(json.dumps(analyze(a.root, a.job,
                                 with_ui=not a.no_ui), indent=2))
        return 0
    except Exception as e:
        print('Jane host evidence failed closed: ' +
              type(e).__name__ + ': ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
