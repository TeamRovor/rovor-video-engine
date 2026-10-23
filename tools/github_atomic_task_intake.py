#!/usr/bin/env python3
"""Publish ONE new ROVOR task and its route in ONE non-force GitHub commit.

Defaults to preview. This is coordination-only, never worker execution or a Mac
connection. Read a single pinned main snapshot and reuse existing task validators.
"""
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import task_routing_pair
import work_brief

REPO = 'TeamRovor/rovor-video-engine'
BRANCH = 'main'
BASE_URL = 'https://api.github.com/repos/' + REPO
MAX_FILE_BYTES = 5_000_000
MAX_RESPONSE_BYTES = 8_000_000
SHA = re.compile(r'^[0-9a-f]{40}$')


class IntakeError(ValueError):
    """Fail-closed, credential-free operator-facing error."""


class Conflict(IntakeError):
    """Head moved or branch protection refused the update; refresh and review."""


def _valid_sha(value):
    return isinstance(value, str) and bool(SHA.fullmatch(value))


class GitHubAPI:
    def __init__(self, token):
        if not isinstance(token, str) or not token.strip():
            raise IntakeError('Missing ROVOR_GITHUB_TOKEN for GitHub coordination access')
        self.token = token

    def request(self, method, path, payload=None):
        if not isinstance(path, str) or not path.startswith('/'):
            raise IntakeError('Invalid API resource')
        url = BASE_URL + path
        data = json.dumps(payload, separators=(',', ':')).encode('utf-8') if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            'Authorization': 'Bearer ' + self.token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'Rovor-atomic-intake-v1',
            'Content-Type': 'application/json',
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise IntakeError('GitHub API response exceeded fixed bound')
            result = json.loads(raw.decode('utf-8'))
            if not isinstance(result, dict):
                raise IntakeError('Invalid GitHub API response')
            return result
        except urllib.error.HTTPError as exc:
            # Never print response bodies, token headers, task contents or URLs.
            if exc.code in (409, 422):
                raise Conflict('GitHub rejected a non-fast-forward or invalid ref update') from None
            if exc.code in (401, 403):
                raise IntakeError('GitHub refused credentials or permissions (HTTP %d)' % exc.code) from None
            raise IntakeError('GitHub API rejected operation (HTTP %d)' % exc.code) from None
        except (urllib.error.URLError, TimeoutError):
            raise IntakeError('GitHub API transport failed; publication unverified') from None
        except (ValueError, UnicodeError):
            raise IntakeError('Invalid GitHub JSON response') from None


def _sha(response, *keys):
    value = response
    for key in keys:
        if not isinstance(value, dict):
            raise IntakeError('Missing GitHub revision evidence')
        value = value.get(key)
    if not _valid_sha(value):
        raise IntakeError('Invalid GitHub revision SHA')
    return value


def _read_file(api, path, head):
    # Pin both records to the SAME exact commit, never independent main reads.
    url = '/contents/' + path + '?ref=' + urllib.parse.quote(head, safe='')
    data = api.request('GET', url)
    if data.get('type') != 'file' or data.get('encoding') != 'base64' or not isinstance(data.get('content'), str):
        raise IntakeError('Expected one encoded versioned coordination file')
    if type(data.get('size')) is not int or not (0 <= data['size'] <= MAX_FILE_BYTES):
        raise IntakeError('Coordination file exceeds fixed limit')
    try:
        raw = base64.b64decode(data['content'].replace('\n', ''), validate=True)
        if len(raw) != data['size'] or len(raw) > MAX_FILE_BYTES:
            raise IntakeError('File content length did not match GitHub metadata')
        obj = json.loads(raw.decode('utf-8'))
        if not isinstance(obj, dict):
            raise IntakeError('Coordination content must be an object')
        return obj
    except (binascii.Error, UnicodeError, ValueError, TypeError):
        raise IntakeError('Invalid encoded versioned coordination file') from None


def _head_and_tree(api):
    ref = api.request('GET', '/git/ref/heads/' + BRANCH)
    head = _sha(ref, 'object', 'sha')
    commit = api.request('GET', '/git/commits/' + head)
    if _sha(commit, 'sha') != head:
        raise IntakeError('Commit identity disagrees with branch')
    tree = _sha(commit, 'tree', 'sha')
    return head, tree


def prepare(api, proposed, lane, requirements):
    head, tree = _head_and_tree(api)
    queue = _read_file(api, task_routing_pair.TASKS, head)
    routing = _read_file(api, task_routing_pair.ROUTING, head)
    try:
        updated_queue, updated_routes = task_routing_pair.prepare_pair(
            queue, routing, proposed, lane, requirements)
    except (ValueError, TypeError) as exc:
        raise IntakeError('Task/route validation refused: ' + str(exc)) from None
    return {
        'head': head, 'base_tree': tree,
        'task_id': proposed['id'], 'lane': lane,
        'queue': updated_queue, 'routes': updated_routes,
        'counts': (len(updated_queue['tasks']), len(updated_routes['tasks'])),
    }


def publish(api, plan):
    """One tree, one commit, one non-force ref move, or no published change.

    GitHub does not offer two-file atomic REST contents updates. In a tree
    commit, BOTH changes are present simultaneously; concurrent main advance
    makes this divergent parent fail the non-force fast-forward check.
    """
    entries = []
    for path, key in ((task_routing_pair.TASKS, 'queue'),
                      (task_routing_pair.ROUTING, 'routes')):
        entries.append({
            'path': path, 'mode': '100644', 'type': 'blob',
            'content': json.dumps(plan[key], ensure_ascii=False, indent=2) + '\n',
        })
    tree = api.request('POST', '/git/trees', {
        'base_tree': plan['base_tree'], 'tree': entries,
    })
    tree_sha = _sha(tree, 'sha')
    commit = api.request('POST', '/git/commits', {
        'message': 'coordination: atomically add %s and its route' % plan['task_id'],
        'tree': tree_sha, 'parents': [plan['head']],
    })
    commit_sha = _sha(commit, 'sha')
    # Cheap guard before writing. Even if head advances after this GET,
    # GitHub's force=false rejects a diverged parent without losing updates.
    current = _sha(api.request('GET', '/git/ref/heads/' + BRANCH), 'object', 'sha')
    if current != plan['head']:
        raise Conflict('Main changed since preview; refresh before retrying')
    result = api.request('PATCH', '/git/refs/heads/' + BRANCH, {
        'sha': commit_sha, 'force': False,
    })
    if _sha(result, 'object', 'sha') != commit_sha:
        raise IntakeError('Ref result does not confirm commit; verify on GitHub')
    return commit_sha


def _read_proposed(path):
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > 100_000:
        raise IntakeError('Refusing missing, redirected or oversized local proposal')
    try:
        obj = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(obj, dict):
            raise IntakeError('Task proposal must be one JSON object')
        return obj
    except (UnicodeError, ValueError):
        raise IntakeError('Invalid JSON task proposal') from None


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--task-json', required=True, type=Path)
    p.add_argument('--lane', required=True, choices=sorted(work_brief.LANES))
    p.add_argument('--require', action='append', choices=sorted(work_brief.CAPABILITIES),
                   default=[])
    p.add_argument('--apply', action='store_true', help='Publish one non-force GitHub commit; preview by default')
    args = p.parse_args(argv)
    try:
        task = _read_proposed(args.task_json)
        api = GitHubAPI(os.environ.get('ROVOR_GITHUB_TOKEN'))
        plan = prepare(api, task, args.lane, args.require)
        if args.apply:
            commit_sha = publish(api, plan)
            print(json.dumps({'status':'published', 'commit':commit_sha,
                              'task_id':plan['task_id'], 'counts':plan['counts']}))
        else:
            print(json.dumps({'status':'preview_only','base_commit':plan['head'],
                              'task_id':plan['task_id'], 'lane':plan['lane'],
                              'counts':plan['counts'], 'note':'No GitHub write'}))
        return 0
    except (IntakeError, OSError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
