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


def route(data, policy, participant, capabilities, lane='any'):
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
    available = {t['id'] for t in project_loop.suggestions(data)}
    candidates, excluded = [], []
    for task in tasks:
        if task['status'] == 'done':
            continue
        reason = None
        own = task.get('owner') == participant
        if task['status'] == 'blocked':
            reason = 'blocked (ownership retained): ' + task['blocker']
        elif task['status'] == 'active' and not own:
            reason = 'reserved by ' + task['owner']
        elif task['status'] == 'ready' and task['id'] not in available:
            reason = 'unfinished dependency or reserved scope'
        rule = rules.get(task['id'])
        if reason is None:
            if rule is None:
                reason = 'capabilities not classified; inspect task before adding a routing rule'
            elif lane != 'any' and rule['lane'] != lane:
                reason = 'outside selected lane: ' + rule['lane']
            else:
                missing = (set(rule['requires']) | {'github-read', 'github-write'}) - capabilities
                if missing:
                    reason = 'missing confirmed capabilities: ' + ', '.join(sorted(missing))
        if reason:
            excluded.append({'id': task['id'], 'reason': reason})
        else:
            candidates.append({**task, 'action': 'resume' if own else 'claim', 'lane': rule['lane']})
    candidates.sort(key=lambda t: (t['action'] != 'resume', t['priority'], t['id']))
    return {'participant': participant, 'lane': lane, 'capabilities': sorted(capabilities),
            'recommended': candidates[0] if candidates else None,
            'alternatives': candidates[1:], 'excluded': excluded, 'warnings': warnings,
            'notice': 'Snapshot only. Refresh main and open PRs; publish and re-read a claim before edits. '
                      'Capabilities are caller assertions, not machine verification. No automatic claim or remote control.'}


def render(brief):
    lines = ['# ROVOR work brief', 'Source: ' + brief['source'], brief['notice'],
             'Participant: ' + brief['participant'], 'Lane: ' + brief['lane']]
    lines += ['WARN: ' + w for w in brief['warnings']]
    task = brief['recommended']
    if task:
        lines += ['', '## Next: ' + task['action'] + ' ' + task['id'],
                  'Branch: ' + task['branch'], 'Scope: ' + ', '.join(task['scopes']),
                  'Action: ' + task['next_action'], 'Acceptance: ' + task['acceptance']]
        lines += ['Read: ' + link for link in task.get('links', [])]
    else:
        lines += ['', 'No eligible implementation task. Read current PR evidence and propose one bounded',
                  'task with acceptance criteria and capability requirements; do not take another owner’s task.']
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
        brief = route(data, policy, args.participant, set(args.capability), args.lane)
        brief['source'] = source
        print(json.dumps(brief, indent=2) if args.json else render(brief), end='\n' if args.json else '')
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
