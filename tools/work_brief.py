#!/usr/bin/env python3
"""Read-only, capability-aware work brief; never claims work or probes a machine."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import project_loop

ROUTING = 'coordination/work-routing.json'
LANES = {'efficiency', 'animation', 'integration', 'coordination', 'sales', 'delivery', 'operations'}
CAPABILITIES = {'github-read', 'github-write', 'hosted-ci', 'local-exec',
                'original-assets', 'visual-review', 'moho-runtime',
                'blender-runtime', 'final-cut-runtime'}


def ready_task_explanations(tasks, rules, capabilities):
    """Read-only reasons a ready task cannot start in this session.

    Preserve the exact task owner/scope and dependency status; avoid guessing
    whether another machine is available. These explanations never claim work.
    """
    by_id = {t['id']: t for t in tasks}
    reserved = [t for t in tasks if t['status'] in {'active', 'blocked'}]
    explanations = []
    for task in tasks:
        if task['status'] != 'ready':
            continue
        dependencies = [
            {'id': dep, 'status': by_id[dep]['status'],
             'owner': by_id[dep].get('owner')}
            for dep in task.get('depends_on', [])
            if by_id[dep]['status'] != 'done'
        ]
        conflicts = []
        for other in reserved:
            for wanted in task['scopes']:
                for occupied in other['scopes']:
                    if project_loop.overlaps(wanted, occupied):
                        conflicts.append({
                            'id': other['id'], 'status': other['status'],
                            'owner': other.get('owner'), 'wanted_scope': wanted,
                            'reserved_scope': occupied,
                        })
        rule = rules.get(task['id'])
        missing = sorted((set(rule['requires']) |
                          {'github-read', 'github-write'}) - capabilities) if rule else []
        if dependencies or conflicts or missing or rule is None:
            explanations.append({
                'id': task['id'], 'priority': task['priority'],
                'lane': rule['lane'] if rule else None,
                'dependencies': dependencies, 'reserved_scope_conflicts': conflicts,
                'missing_capabilities': missing,
                'unclassified': rule is None,
            })
    explanations.sort(key=lambda t: (t['priority'], t['id']))
    return explanations


def route(data, policy, participant, capabilities, lane='any', fallback_any_lane=False):
    errors, warnings = project_loop.validate(data)
    if errors:
        raise ValueError('Invalid shared queue: ' + '; '.join(errors))
    if lane != 'any' and lane not in LANES:
        raise ValueError('Unknown work lane: ' + lane)
    if not participant.strip():
        raise ValueError('A stable participant/session identifier is required')
    if not capabilities <= CAPABILITIES:
        raise ValueError('Unknown capabilities: ' + ', '.join(sorted(capabilities - CAPABILITIES)))
    if not isinstance(policy, dict) or policy.get('version') != 1 or not isinstance(policy.get('tasks'), dict):
        raise ValueError('Expected routing version 1 and tasks object')
    rules = policy['tasks']
    for ident, rule in rules.items():
        if (not isinstance(rule, dict) or not isinstance(rule.get('lane'), str) or rule['lane'] not in LANES
                or not isinstance(rule.get('requires'), list)
                or any(not isinstance(c, str) or c not in CAPABILITIES for c in rule['requires'])):
            raise ValueError('Invalid capability rule: ' + ident)
    tasks = data['tasks']
    ids = {t['id'] for t in tasks}
    warnings += ['Routing references missing task: ' + i for i in rules if i not in ids]
    ready_explanations = ready_task_explanations(tasks, rules, capabilities)
    available = {t['id'] for t in project_loop.suggestions(data)}
    candidates, other_lane, excluded = [], [], []
    for task in tasks:
        if task['status'] == 'done':
            continue
        reason = None
        own = task.get('owner') == participant
        rule = rules.get(task['id'])
        if task['status'] == 'blocked':
            reason = 'blocked (ownership retained): ' + task['blocker']
        elif task['status'] == 'active' and not own:
            reason = 'reserved by ' + task['owner']
        elif task['status'] == 'ready' and task['id'] not in available:
            reason = 'unfinished dependency or reserved scope'
        elif rule is None:
            reason = 'capabilities not classified; inspect task before adding a routing rule'
        else:
            # Capabilities are independently confirmed by the caller, never
            # inferred from the session's name, device or another worker.
            missing = (set(rule['requires']) | {'github-read', 'github-write'}) - capabilities
            if missing:
                reason = 'missing confirmed capabilities: ' + ', '.join(sorted(missing))
            elif lane != 'any' and rule['lane'] != lane:
                if fallback_any_lane:
                    other_lane.append({**task, 'action': 'resume' if own else 'claim',
                                       'lane': rule['lane']})
                else:
                    reason = 'outside selected lane: ' + rule['lane']
        if reason:
            excluded.append({'id': task['id'], 'reason': reason})
        elif rule is not None and not (
                lane != 'any' and rule['lane'] != lane and fallback_any_lane):
            candidates.append({**task, 'action': 'resume' if own else 'claim',
                               'lane': rule['lane']})
    selection = 'requested_lane' if candidates else 'none'
    if not candidates and fallback_any_lane and other_lane:
        candidates = other_lane
        selection = 'fallback_other_lane'
    elif other_lane:
        excluded.extend({'id': t['id'], 'reason': 'outside selected lane: ' + t['lane']}
                        for t in other_lane)
    candidates.sort(key=lambda t: (t['action'] != 'resume', t['priority'], t['id']))
    unfinished = [t for t in tasks if t['status'] != 'done']
    unrouted = sorted(t['id'] for t in unfinished if t['id'] not in rules)
    status_counts = {status: sum(t['status'] == status for t in tasks)
                     for status in ('ready', 'active', 'blocked', 'done')}
    coverage = {
        'total_tasks': len(tasks),
        'routed_tasks': sum(t['id'] in rules for t in tasks),
        'unfinished_tasks': len(unfinished),
        'routed_unfinished': len(unfinished) - len(unrouted),
        'unclassified_unfinished': unrouted,
        'status_counts': status_counts,
    }
    if unrouted:
        warnings.append('Unclassified unfinished tasks: ' + ', '.join(unrouted))
    return {'participant': participant, 'lane': lane, 'capabilities': sorted(capabilities),
            'recommended': candidates[0] if candidates else None,
            'alternatives': candidates[1:], 'excluded': excluded, 'warnings': warnings,
            'routing_coverage': coverage, 'selection_mode': selection,
            'ready_blockers': ready_explanations,
            'fallback_any_lane_requested': fallback_any_lane,
            'notice': 'Snapshot only. Refresh main and open PRs; publish and re-read a claim before edits. '
                      'Capabilities are caller assertions, not machine verification. No automatic claim or remote control.'}



def render(brief):
    lines = ['# ROVOR work brief', 'Source: ' + brief['source'], brief['notice'],
             'Participant: ' + brief['participant'], 'Lane: ' + brief['lane']]
    lines += ['WARN: ' + w for w in brief['warnings']]
    coverage = brief['routing_coverage']
    lines += ['Routing: %d/%d tasks classified; %d/%d unfinished classified' %
              (coverage['routed_tasks'], coverage['total_tasks'],
               coverage['routed_unfinished'], coverage['unfinished_tasks']),
              'Selection: ' + brief['selection_mode']]
    task = brief['recommended']
    if task:
        lines += ['', '## Next: ' + task['action'] + ' ' + task['id'],
                  'Branch: ' + task['branch'], 'Scope: ' + ', '.join(task['scopes']),
                  'Action: ' + task['next_action'], 'Acceptance: ' + task['acceptance']]
        lines += ['Read: ' + link for link in task.get('links', [])]
    else:
        lines += ['', 'No eligible implementation task. Read current PR evidence and propose one bounded',
                  'task with acceptance criteria and capability requirements; do not take another owner’s task.']
    if not task and brief['ready_blockers']:
        lines.append('')
        lines.append('## Ready-task blockers (no ownership changes)')
        for item in brief['ready_blockers'][:5]:
            parts = []
            if item['dependencies']:
                parts.append('dependencies: ' + ', '.join(
                    d['id'] + ' [' + d['status'] +
                    (', owner=' + d['owner'] if d.get('owner') else '') + ']'
                    for d in item['dependencies']))
            if item['reserved_scope_conflicts']:
                parts.append('reserved scopes: ' + ', '.join(sorted({
                    d['id'] + ' (' + d['wanted_scope'] + ')'
                    for d in item['reserved_scope_conflicts']})))
            if item['missing_capabilities']:
                parts.append('missing capabilities: ' + ', '.join(item['missing_capabilities']))
            if item['unclassified']:
                parts.append('unclassified route')
            lines.append(item['id'] + ': ' + '; '.join(parts))
    lines += ['', '## Other eligible tasks'] + [t['id'] for t in brief['alternatives']]
    lines += ['', '## Excluded'] + [t['id'] + ': ' + t['reason'] for t in brief['excluded']]
    lines += ['', 'Handoff: exact commit/PR, changed files, actual checks/platform/results, blockers,',
              'next action, next checkpoint, and claim status in main coordination/tasks.json.']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--ref', help='Already fetched ref; queue and routing resolve to the SAME commit')
    p.add_argument('--participant', required=True)
    p.add_argument('--lane', choices=['any'] + sorted(LANES), default='any')
    p.add_argument('--capability', action='append', choices=sorted(CAPABILITIES), default=[])
    p.add_argument('--json', action='store_true')
    p.add_argument('--fallback-any-lane', action='store_true',
                   help='If selected lane has no eligible work, consider other lanes without overriding claims')
    args = p.parse_args(argv)
    try:
        if args.ref:
            sha = project_loop.git(args.repo, 'rev-parse', '--verify', '--end-of-options', args.ref + '^{commit}')
            data = project_loop.load_state(args.repo, sha)
            policy = json.loads(project_loop.git(args.repo, 'show', sha + ':' + ROUTING))
            source = sha + ' (fetched snapshot; does not contact GitHub)'
        else:
            data = project_loop.load_state(args.repo)
            policy = json.loads((args.repo / ROUTING).read_text(encoding='utf-8'))
            source = 'local working files (freshness unverified)'
        brief = route(data, policy, args.participant, set(args.capability),
                      args.lane, fallback_any_lane=args.fallback_any_lane)
        brief['source'] = source
        print(json.dumps(brief, indent=2) if args.json else render(brief), end='\n' if args.json else '')
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
