#!/usr/bin/env python3
"""Read-only coordination checks. No dependencies, network, or automatic task claims."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys

STATE = 'coordination/tasks.json'
STATUSES = {'ready', 'active', 'blocked', 'done'}
RESERVED = {'active', 'blocked'}


def timestamp(value):
    date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if date.tzinfo is None:
        raise ValueError('timezone required')
    return date


def overlaps(left, right):
    """Scopes are file/directory paths, or named subsystem: resources."""
    if left.startswith('subsystem:') or right.startswith('subsystem:'):
        return left == right
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def validate(data, now=None):
    errors, warnings = [], []
    now = now or datetime.now(timezone.utc)
    if not isinstance(data, dict) or type(data.get('version')) is not int or data.get('version') != 1 or not isinstance(data.get('tasks'), list):
        return ['Expected version 1 and a tasks array'], []
    tasks, ids = data['tasks'], set()
    valid = []
    for index, task in enumerate(tasks):
        label = 'task[%d]' % index
        if not isinstance(task, dict):
            errors.append(label + ': expected an object')
            continue
        label = str(task.get('id', label))
        required = ['id', 'title', 'branch', 'next_action', 'acceptance']
        for key in required:
            if not isinstance(task.get(key), str) or not task[key].strip():
                errors.append(label + ': missing ' + key)
        ident = task.get('id')
        if isinstance(ident, str):
            if ident in ids:
                errors.append(label + ': duplicate id')
            ids.add(ident)
        if not isinstance(task.get('status'), str) or task['status'] not in STATUSES:
            errors.append(label + ': invalid status')
            continue
        if type(task.get('priority')) is not int or task['priority'] < 1:
            errors.append(label + ': priority must be a positive integer')
        scopes = task.get('scopes')
        if not isinstance(scopes, list) or not scopes or any(
            not isinstance(s, str) or not s or '\\' in s or s.startswith('/')
            or (':' in s and (not s.startswith('subsystem:') or not s[10:] or '/' in s))
            or s.endswith('/') or any(p in {'.', '..', ''} for p in s.split('/'))
            for s in scopes
        ):
            errors.append(label + ': scopes must be normalized relative paths or subsystem:name')
        else:
            valid.append(task)
        deps = task.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            errors.append(label + ': depends_on must be an array of ids')
        if task.get('status') in RESERVED | {'done'}:
            for key in ['owner', 'updated_at']:
                if not isinstance(task.get(key), str) or not task[key].strip():
                    errors.append(label + ': missing ' + key)
            try:
                age = (now - timestamp(task.get('updated_at', ''))).total_seconds()
                if age < -300:
                    errors.append(label + ': updated_at is in the future')
                if age > 86400 and task.get('status') in RESERVED:
                    warnings.append(label + ': claim older than 24h; check owner, do not take over automatically')
            except (ValueError, TypeError, AttributeError):
                errors.append(label + ': updated_at needs an ISO timestamp with timezone')
        if task.get('status') in RESERVED and (not isinstance(task.get('next_update'), str) or not task['next_update'].strip()):
            errors.append(label + ': active/blocked work needs next_update')
        if task.get('status') == 'blocked' and (not isinstance(task.get('blocker'), str) or not task['blocker'].strip()):
            errors.append(label + ': blocked work needs blocker')
        if task.get('status') == 'done':
            evidence = task.get('evidence')
            if not isinstance(evidence, list) or not evidence:
                errors.append(label + ': done requires evidence')
            else:
                for item in evidence:
                    if not isinstance(item, dict) or any(
                        not isinstance(item.get(k), str) or not item[k].strip()
                        for k in ['commit', 'platform', 'check', 'result', 'reference']
                    ):
                        errors.append(label + ': evidence requires commit, platform, check, result and reference')
        if task.get('status') == 'ready' and task.get('owner'):
            errors.append(label + ': ready task must be unclaimed; use active or blocked for owned work')
    by_id = {t['id']: t for t in tasks if isinstance(t, dict) and isinstance(t.get('id'), str)}
    for ident, task in by_id.items():
        deps = task.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            continue
        for dep in deps:
            if dep not in by_id:
                errors.append(ident + ': unknown dependency ' + dep)
            elif task.get('status') in {'active', 'done'} and by_id[dep].get('status') != 'done':
                errors.append(ident + ': dependency is not done: ' + dep)
    visiting, visited = set(), set()

    def visit(ident):
        if ident in visiting:
            errors.append(ident + ': dependency cycle')
            return
        if ident in visited:
            return
        visiting.add(ident)
        deps = by_id[ident].get('depends_on', [])
        if isinstance(deps, list):
            for dep in deps:
                if isinstance(dep, str) and dep in by_id:
                    visit(dep)
        visiting.remove(ident)
        visited.add(ident)

    for ident in by_id:
        visit(ident)
    reserved = [t for t in valid if t.get('status') in RESERVED]
    for i, left in enumerate(reserved):
        for right in reserved[i + 1:]:
            if any(overlaps(a, b) for a in left['scopes'] for b in right['scopes']):
                errors.append('%s / %s: overlapping claims; arrange a handoff' % (left['id'], right['id']))
    return errors, warnings


def suggestions(data):
    tasks = data['tasks']
    done = {t['id'] for t in tasks if t['status'] == 'done'}
    reserved = [s for t in tasks if t['status'] in RESERVED for s in t['scopes']]
    return sorted((t for t in tasks if t['status'] == 'ready'
                   and set(t.get('depends_on', [])) <= done
                   and not any(overlaps(a, b) for a in t['scopes'] for b in reserved)),
                  key=lambda t: (t['priority'], t['id']))


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
                            text=True, timeout=15, check=False)
    if result.returncode:
        raise ValueError('Git command failed: ' + ' '.join(args[:1]))
    return result.stdout.strip()


def load_state(repo, ref=None):
    # Resolve refs to a commit before git show: no option injection or arbitrary path reads.
    if ref:
        sha = git(repo, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')
        return json.loads(git(repo, 'show', sha + ':' + STATE))
    return json.loads((repo / STATE).read_text(encoding='utf-8'))


def doctor(repo):
    print('Platform: ' + platform.system() + ' / Python ' + platform.python_version())
    for tool in ['git', 'node', 'ffmpeg', 'ffprobe', 'rhubarb', 'whisper']:
        print('%s: %s' % (tool, 'found on PATH' if shutil.which(tool) else 'not on PATH (may use local_tools.json)'))
    try:
        print('Branch: ' + git(repo, 'branch', '--show-current'))
        print('Commit: ' + git(repo, 'rev-parse', 'HEAD'))
        dirty = bool(git(repo, 'status', '--porcelain'))
        print('Working tree: ' + ('has local changes; preserve them' if dirty else 'clean'))
        try:
            print('Local ahead/behind upstream: ' + git(repo, 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}'))
        except ValueError:
            print('Upstream: not configured')
    except ValueError as exc:
        print(str(exc))
    print('Read-only snapshot. Fetch first for current remote state. PATH detection is not runtime verification.')
    print('Use the existing engine launcher --check on the intended branch for actual configured tool checks.')
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'check', 'doctor'])
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--ref', help='Read task state from a locally fetched Git ref (does not fetch)')
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            return doctor(args.repo)
        data = load_state(args.repo, args.ref)
        errors, warnings = validate(data)
        for message in warnings:
            print('WARN: ' + message)
        for message in errors:
            print('ERROR: ' + message)
        if errors:
            return 1
        print('Coordination structure valid; evidence remains subject to review.')
        if args.command == 'status':
            print('Source: ' + (args.ref or 'local working copy') + ' (fetch/push required to share)')
            for task in sorted(data['tasks'], key=lambda t: (t['priority'], t['id'])):
                print('[%s] %s | %s | %s' % (task['status'], task['id'], task.get('owner') or 'unclaimed', task['branch']))
                print('  Next: ' + task['next_action'])
            print('Available next tasks (not automatically claimed):')
            for task in suggestions(data):
                print('  ' + task['id'] + ': ' + task['title'])
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
