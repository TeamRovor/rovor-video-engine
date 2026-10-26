#!/usr/bin/env python3
"""One bounded operations report. No model, network, shell, task claims or client actions."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time

import project_loop
import work_brief

INPUTS = ('coordination/tasks.json', 'coordination/work-routing.json', 'business/operating-plan.json')
CODE = {'runtime/ops_worker.py': Path(__file__), 'runtime/work_brief.py': Path(work_brief.__file__),
        'runtime/project_loop.py': Path(project_loop.__file__)}
MAX_INPUT = 2 * 1024 * 1024
MAX_REPORT = 512 * 1024
MAX_TASKS = 500


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n').encode('utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_bounded(path, limit):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing or symlinked input/artifact: ' + path.name)
    with path.open('rb') as f:
        data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError('File exceeds byte limit: ' + path.name)
    return data


def save(path, data):
    if path.exists() or path.is_symlink():
        raise ValueError('Refusing to overwrite artifact: ' + path.name)
    temp = path.with_suffix(path.suffix + '.partial')
    with temp.open('xb') as f:
        f.write(data)
    temp.replace(path)


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get('version') != 1:
        raise ValueError('Expected operating plan version 1')
    objectives = plan.get('objectives')
    if not isinstance(objectives, list) or not objectives:
        raise ValueError('Objectives required')
    ids = []
    for o in objectives:
        if (not isinstance(o, dict) or not isinstance(o.get('id'), str) or not o['id']
                or not isinstance(o.get('outcome'), str) or not o['outcome']
                or not isinstance(o.get('metrics'), list)
                or not o['metrics'] or any(not isinstance(m, str) or not m for m in o['metrics'])):
            raise ValueError('Invalid business objective')
        ids.append(o['id'])
    order = plan.get('priority_order')
    if len(set(ids)) != len(ids) or not isinstance(order, list) or order != list(dict.fromkeys(order)) or set(order) != set(ids):
        raise ValueError('Priority order must list every objective exactly once')
    w = plan.get('worker')
    if not isinstance(w, dict) or type(w.get('enabled')) is not bool:
        raise ValueError('Worker enabled must be boolean')
    if not w['enabled']:
        raise ValueError('Operations worker disabled by operating plan')
    if w.get('action') != 'operations-report':
        raise ValueError('Only operations-report is implemented')
    for field, maximum in [('max_input_bytes', MAX_INPUT), ('max_report_bytes', MAX_REPORT),
                           ('max_tasks', MAX_TASKS), ('max_recommendations_per_lane', 3),
                           ('max_runtime_seconds', 30), ('max_attempts_per_fingerprint', 1)]:
        if type(w.get(field)) is not int or not 1 <= w[field] <= maximum:
            raise ValueError('Invalid bounded worker setting: ' + field)
    for field in ['llm_calls', 'external_messages', 'production_writes']:
        if type(w.get(field)) is not int or w[field] != 0:
            raise ValueError('Unsupported worker permission: ' + field)
    return w


def report(data, routing, plan, now):
    limits = validate_plan(plan)
    errors, warnings = project_loop.validate(data, now)
    if errors:
        raise ValueError('Invalid task queue: ' + '; '.join(errors))
    if len(data['tasks']) > limits['max_tasks']:
        raise ValueError('Too many tasks for one operations report')
    objective_ids = set(plan['priority_order'])
    mapping = routing.get('tasks', {}) if isinstance(routing, dict) else {}
    if not isinstance(mapping, dict):
        raise ValueError('Routing tasks must be an object')
    for ident, rule in mapping.items():
        if isinstance(rule, dict) and rule.get('objective') is not None and rule['objective'] not in objective_ids:
            raise ValueError('Unknown business objective for ' + ident)
    lanes = {}
    # This is a hypothetical GitHub-write-capable human session, NOT this read-only worker's permission.
    for lane in sorted(work_brief.LANES):
        packet = work_brief.route(data, routing, plan.get('business', 'Rovor') + ' / unclaimed-report-preview',
                                  {'github-read', 'github-write'}, lane)
        candidates = ([packet['recommended']] if packet['recommended'] else []) + packet['alternatives']
        lanes[lane] = [dict(id=t['id'], title=t['title'], branch=t['branch'], scopes=t['scopes'],
                            next_action=t['next_action'], acceptance=t['acceptance'],
                            objective=mapping[t['id']].get('objective', 'not-classified'), links=t.get('links', []))
                       for t in candidates[:limits['max_recommendations_per_lane']]]
        warnings += packet['warnings']
    counts = dict(Counter(t['status'] for t in data['tasks']))
    blockers = [dict(id=t['id'], owner=t['owner'], reason=t['blocker'], next_action=t['next_action'])
                for t in data['tasks'] if t['status'] == 'blocked']
    unclassified = [t['id'] for t in data['tasks'] if t['status'] != 'done' and t['id'] not in mapping]
    return dict(version=1, observed_at=now.isoformat(), kind='operations-report', status='review_required',
                business=plan.get('business', 'Rovor Digital'), counts=counts, blockers=blockers,
                warnings=sorted(set(warnings)), unclassified=unclassified, next_work_by_lane=lanes,
                objectives=plan['objectives'], priority_order=plan['priority_order'],
                metric_baseline=plan.get('baseline_status', 'Not measured'),
                limits=limits, implemented_action='Read repository snapshots and write this report only',
                boundary='Recommendations are for a future authorized session. No task was claimed or executed. '
                         'Task done is not proof of merged, delivered, profitable or visually approved work. '
                         'PR status, local computer health and client metrics were not fetched.')


def markdown(r):
    # Treat task text as data, not instructions. Strip line breaks in compact fields for readable output.
    def line(v):
        return str(v).replace('\r', ' ').replace('\n', ' ')
    parts = ['# Rovor operations briefing', '', 'Observed: ' + r['observed_at'],
             'Snapshot fingerprint: ' + r['fingerprint'], 'Revision label: ' + r['revision'],
             '', r['boundary'], '', '## Queue health']
    parts += ['- ' + k + ': ' + str(v) for k, v in sorted(r['counts'].items())]
    parts += ['', '## Attention needed']
    parts += ['- ' + line(w) for w in r['warnings']]
    parts += ['- ' + line(b['id']) + ' — ' + line(b['reason']) + ' Next: ' + line(b['next_action']) for b in r['blockers']]
    parts += ['- Classify capabilities before selection: ' + line(i) for i in r['unclassified']]
    parts += ['', '## Next useful work by lane', 'These are unclaimed suggestions; refresh main and publish a claim before edits.']
    for lane, tasks in r['next_work_by_lane'].items():
        parts += ['', '### ' + lane]
        if not tasks:
            parts += ['No eligible GitHub-only task. Inspect blockers/capabilities; do not take over owned work.']
        for t in tasks:
            parts += ['- ' + line(t['id']) + ' | outcome: ' + line(t['objective']),
                      '  Branch: ' + line(t['branch']) + '; scope: ' + line(', '.join(t['scopes'])),
                      '  Next: ' + line(t['next_action']), '  Acceptance: ' + line(t['acceptance'])]
    parts += ['', '## Business measures', r['metric_baseline']]
    for o in r['objectives']:
        parts += ['- ' + line(o['id']) + ': ' + line(', '.join(o['metrics']))]
    parts += ['', '## Worker limits', 'No LLM calls, client messages, production writes, paid APIs, or remote laptop operations.',
              'This worker is an operations reporter, not a general AI employee or native Moho renderer.']
    return '\n'.join(parts) + '\n'


def run(repo, out, revision='working-copy', now=None):
    start = time.monotonic()
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Timezone-aware observation time required')
    if revision != 'working-copy' and not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Revision must be a full Git SHA or working-copy')
    repo = repo.resolve()
    if out.is_symlink():
        raise ValueError('Output root must not be a symlink')
    out = out.resolve()
    if out == repo or repo in out.parents:
        raise ValueError('Keep worker state outside the source checkout')
    sources = {name: repo / name for name in INPUTS}
    sources.update(CODE)
    raw = {name: read_bounded(path, MAX_INPUT) for name, path in sources.items()}
    plan = json.loads(raw[INPUTS[2]])
    limits = validate_plan(plan)
    if sum(len(x) for x in raw.values()) > limits['max_input_bytes']:
        raise ValueError('Total input exceeds byte budget')
    # Freeze one in-memory snapshot, reject files changed while capturing it.
    if any(read_bounded(sources[name], MAX_INPUT) != content for name, content in raw.items()):
        raise ValueError('Inputs changed during capture; refresh the snapshot')
    hashes = {name: sha(content) for name, content in raw.items()}
    # Same inputs within 15 minutes reuse verified output; a later invocation refreshes time-sensitive warnings.
    key = sha(encoded(dict(inputs=hashes, revision=revision, time_bucket=int(now.timestamp()) // 900)))
    out.mkdir(parents=True, exist_ok=True)
    lock = out / '.operations-lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise ValueError('Worker lock exists; inspect active process before any manual recovery')
    path = out / key
    created = False
    try:
        if time.monotonic() - start > limits['max_runtime_seconds']:
            raise ValueError('Runtime budget exceeded before report')
        if path.is_symlink():
            raise ValueError('Job directory must not be a symlink')
        if path.exists():
            receipt = json.loads(read_bounded(path / 'receipt.json', MAX_REPORT))
            if not isinstance(receipt, dict):
                raise ValueError('Invalid receipt')
            if receipt.get('state') != 'complete' or receipt.get('fingerprint') != key:
                raise ValueError('Previous attempt incomplete/failed; inspect it, do not automatically replay')
            if receipt.get('inputs') != hashes or not isinstance(receipt.get('outputs'), dict) or set(receipt.get('outputs', {})) != {'report.json', 'report.md'}:
                raise ValueError('Receipt does not match this snapshot')
            for name, expected in receipt['outputs'].items():
                if sha(read_bounded(path / name, limits['max_report_bytes'])) != expected:
                    raise ValueError('Cached artifact checksum mismatch: ' + name)
            return dict(state='complete', cached=True, fingerprint=key, directory=str(path))
        path.mkdir()
        created = True
        save(path / 'started.json', encoded(dict(fingerprint=key, observed_at=now.isoformat(), inputs=hashes)))
        r = report(json.loads(raw[INPUTS[0]]), json.loads(raw[INPUTS[1]]), plan, now)
        r.update(fingerprint=key, revision=revision, inputs=hashes)
        outputs = {'report.json': encoded(r), 'report.md': markdown(r).encode('utf-8')}
        if sum(len(content) for content in outputs.values()) > limits['max_report_bytes']:
            raise ValueError('Report exceeds byte budget')
        if time.monotonic() - start > limits['max_runtime_seconds']:
            raise ValueError('Runtime budget exceeded; no report published')
        for name, content in outputs.items():
            save(path / name, content)
        save(path / 'receipt.json', encoded(dict(state='complete', fingerprint=key, inputs=hashes,
             outputs={name: sha(content) for name, content in outputs.items()}, observed_at=now.isoformat())))
        return dict(state='complete', cached=False, fingerprint=key, directory=str(path))
    except Exception as exc:
        if created:
            save(path / 'failure.json', encoded(dict(state='failed', error=type(exc).__name__, reason=str(exc)[:2000])))
        raise
    finally:
        lock.rmdir()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--out', type=Path, required=True, help='Private worker state outside repository')
    p.add_argument('--revision', default='working-copy', help='Optional checkout SHA label; input hashes remain authoritative')
    a = p.parse_args(argv)
    try:
        result = run(a.repo, a.out, a.revision)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
