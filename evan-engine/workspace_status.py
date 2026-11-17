"""Report installed code, pending pulls and shared tasks without changing working files."""
import argparse
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parent.parent


def _git(repo, *args, timeout=10):
    # Status calls must not prompt for credentials or block an MCP conversation.
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')
    try:
        result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True,
            text=True, encoding='utf-8', errors='replace', env=env, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def workspace_status(repo=ROOT, fetch=False):
    repo = Path(repo)
    report = {'available': False, 'fetched_this_call': False,
              'remote_state': 'cached refs; use fetch=true or --fetch to refresh',
              'note': 'No pull, checkout, reset, install or render is performed.'}
    if _git(repo, 'rev-parse', '--is-inside-work-tree') != 'true':
        report['message'] = 'Git checkout unavailable; standalone installs cannot compare updates.'
        return report
    report['available'] = True
    if fetch:
        # Fetch only the configured origin. Never merge code or alter local branches.
        fetched = _git(repo, '-c', 'credential.interactive=never', 'fetch', '--no-tags',
                       '--no-recurse-submodules', 'origin', timeout=30)
        report['fetched_this_call'] = fetched is not None
        report['remote_state'] = ('origin fetched during this call' if fetched is not None
                                  else 'fetch failed; cached refs only')
    branch = _git(repo, 'symbolic-ref', '--quiet', '--short', 'HEAD')
    report['branch'] = branch
    report['commit'] = _git(repo, 'rev-parse', '--verify', 'HEAD')
    changes = _git(repo, 'status', '--porcelain', '--untracked-files=normal')
    report['local_changes'] = None if changes is None else bool(changes)
    upstream = _git(repo, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    report['upstream'] = upstream
    report['ahead'] = report['behind'] = None
    if report['commit'] and upstream:
        counts = _git(repo, 'rev-list', '--left-right', '--count', 'HEAD...@{upstream}')
        try:
            report['ahead'], report['behind'] = (int(n) for n in counts.split())
        except (AttributeError, TypeError, ValueError):
            pass
    ahead, behind = report['ahead'], report['behind']
    if not branch:
        report['next_action'] = 'Detached checkout: identify the intended branch before updating.'
    elif not report['commit']:
        report['next_action'] = 'No committed revision is available yet.'
    elif not upstream or ahead is None:
        report['next_action'] = 'Confirm the intended tracking branch before pulling; no upstream comparison is available.'
    elif ahead and behind:
        report['next_action'] = 'Local and upstream commits diverged. Preserve local work and arrange reconciliation; do not force reset.'
    elif behind and report['local_changes'] is not False:
        report['next_action'] = 'Updates are waiting. Preserve local changes before attempting a pull.'
    elif behind:
        report['next_action'] = 'The tracked branch has updates. A clean checkout can use git pull --ff-only after checking active work.'
    elif ahead:
        report['next_action'] = 'Local commits are ahead of the fetched upstream; publish the handoff so others can see them.'
    else:
        report['next_action'] = 'Local code matches the fetched upstream. Cached refs may be older than GitHub.'
    shared = {'ref': 'origin/main', 'commit': _git(repo, 'rev-parse', '--verify', 'refs/remotes/origin/main'),
              'available': False, 'tasks': []}
    if shared['commit']:
        raw = _git(repo, 'show', shared['commit'] + ':coordination/tasks.json')
        try:
            queue = json.loads(raw)
        except (TypeError, ValueError):
            queue = None
        if isinstance(queue, dict) and queue.get('version') == 1 and isinstance(queue.get('tasks'), list):
            shared['available'] = True
            for task in queue['tasks']:
                if not isinstance(task, dict) or task.get('status') == 'done':
                    continue
                # Include claims on all branches so cross-platform owners remain visible.
                shared['tasks'].append({key: task.get(key) for key in (
                    'id', 'title', 'status', 'owner', 'branch', 'scopes', 'depends_on',
                    'updated_at', 'next_action')})
        else:
            shared['message'] = 'Shared queue is missing or unreadable at the fetched main revision.'
    else:
        shared['message'] = 'Fetch origin/main to load the shared task queue.'
    shared['note'] = 'Read AGENTS.md and PROJECT-LOOP.md from origin/main before claiming work. This is a fetched snapshot, not a live task lock.'
    report['coordination'] = shared
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Refresh origin refs without pulling code')
    parser.add_argument('--repo', type=Path, default=ROOT)
    args = parser.parse_args()
    print(json.dumps(workspace_status(args.repo, fetch=args.fetch), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
