#!/usr/bin/env python3
"""Prepare one task + its routing policy together, without claiming/pushing work."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import project_loop
import work_brief

TASKS = 'coordination/tasks.json'
ROUTING = 'coordination/work-routing.json'


def _paired_paths(root):
    root = Path(root)
    parent = root / 'coordination'
    if parent.is_symlink():
        raise ValueError('Refusing redirected coordination directory')
    paths = [root / TASKS, root / ROUTING]
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('Refusing missing or redirected coordination file')
    return paths


def read_pair(root):
    paths = _paired_paths(root)
    raw = [p.read_bytes() for p in paths]
    if any(len(data) > 5_000_000 for data in raw):
        raise ValueError('Coordination file is unexpectedly large')
    return json.loads(raw[0]), json.loads(raw[1]), raw


def validate_pair(queue, routing):
    errors, _warnings = project_loop.validate(queue)
    if errors:
        raise ValueError('Invalid shared task queue: ' + '; '.join(errors))
    if not isinstance(routing, dict) or routing.get('version') != 1 or not isinstance(routing.get('tasks'), dict):
        raise ValueError('Expected routing version 1 and tasks map')
    ids = {t['id'] for t in queue['tasks']}
    policy_ids = set(routing['tasks'])
    if ids != policy_ids:
        raise ValueError('Routing mismatch: missing=%s stale=%s' %
                         (sorted(ids - policy_ids), sorted(policy_ids - ids)))
    # Reuse the actual router's capability and lane validation.
    work_brief.route(queue, routing, 'paired intake validation',
                     {'github-read', 'github-write'}, 'any')


def prepare_pair(queue, routing, task, lane, requires):
    """Return a validated new queue and policy, leaving all inputs untouched."""
    validate_pair(queue, routing)
    if not isinstance(task, dict) or not isinstance(task.get('id'), str) or not task['id'].strip():
        raise ValueError('Expected a new task with a nonempty id')
    if task.get('status') not in {'ready', 'active'}:
        raise ValueError('A new intake task must be ready or actively claimed')
    if task['id'] in {t['id'] for t in queue['tasks']}:
        raise ValueError('Task id already exists: ' + task['id'])
    if lane not in work_brief.LANES:
        raise ValueError('Invalid work lane')
    if not isinstance(requires, list) or len(set(requires)) != len(requires) or any(
            c not in work_brief.CAPABILITIES for c in requires):
        raise ValueError('Invalid, duplicate or unverified capability rule')
    next_queue, next_routing = copy.deepcopy(queue), copy.deepcopy(routing)
    next_queue['tasks'].append(copy.deepcopy(task))
    next_routing['tasks'][task['id']] = {'lane': lane, 'requires': sorted(requires)}
    validate_pair(next_queue, next_routing)
    return next_queue, next_routing


def _git_sources_clean(root):
    cmd = ['git', '-C', str(root), 'status', '--porcelain', '--', TASKS, ROUTING]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode or result.stdout.strip():
        raise ValueError('Coordination source files not in a clean tracked checkout')


def apply_pair(root, old_bytes, next_queue, next_routing):
    """Guarded local two-file update. Caller must commit both files together."""
    root = Path(root)
    paths = _paired_paths(root)
    _git_sources_clean(root)
    if [p.read_bytes() for p in paths] != old_bytes:
        raise ValueError('Coordination files changed since preparation')
    encoded = [(json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
               for obj in (next_queue, next_routing)]
    temps = []
    for p, data in zip(paths, encoded):
        with tempfile.NamedTemporaryFile(dir=str(p.parent), prefix='.rovor-pair-',
                                         suffix='.tmp', delete=False) as tf:
            tf.write(data)
            temps.append(Path(tf.name))
    first_applied = False
    try:
        if [p.read_bytes() for p in paths] != old_bytes:
            raise ValueError('Coordination files changed before apply')
        os.replace(str(temps[0]), str(paths[0]))
        first_applied = True
        os.replace(str(temps[1]), str(paths[1]))
    except Exception:
        # Two independent filesystem renames are not a transaction.
        # Make a best-effort rollback; do not assert success on an error.
        if first_applied:
            paths[0].write_bytes(old_bytes[0])
        raise
    finally:
        for temp in temps:
            if temp.exists():
                temp.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--check', action='store_true', help='Verify paired queue/routing only')
    parser.add_argument('--task-json', type=Path, help='Local task JSON object to add')
    parser.add_argument('--lane', choices=sorted(work_brief.LANES))
    parser.add_argument('--require', action='append', default=[],
                        choices=sorted(work_brief.CAPABILITIES))
    parser.add_argument('--apply', action='store_true',
                        help='Write both files to a clean local checkout; commit together separately')
    args = parser.parse_args(argv)
    try:
        queue, routing, previous = read_pair(args.repo)
        if args.check:
            if args.task_json or args.lane or args.apply or args.require:
                raise ValueError('--check cannot prepare or apply a new task')
            validate_pair(queue, routing)
            print('ROVOR paired routing valid: %d tasks / %d rules' %
                  (len(queue['tasks']), len(routing['tasks'])))
            return 0
        if not args.task_json or not args.lane:
            raise ValueError('Supply --task-json and --lane, or use --check')
        task = json.loads(args.task_json.read_text(encoding='utf-8'))
        new_queue, new_routing = prepare_pair(queue, routing, task, args.lane,
                                               args.require)
        if args.apply:
            apply_pair(args.repo, previous, new_queue, new_routing)
        print(json.dumps({'task': task['id'], 'lane': args.lane,
                          'required_capabilities': sorted(args.require),
                          'status': 'applied_local_pair' if args.apply else 'validated_dry_run',
                          'task_count': len(new_queue['tasks']),
                          'rule_count': len(new_routing['tasks']),
                          'note': 'No ownership takeover or GitHub commit performed; '
                                  'review and commit both files together.'},
                         indent=2))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
