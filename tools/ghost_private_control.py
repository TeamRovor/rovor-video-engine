#!/usr/bin/env python3
"""Private GitHub -> existing SQLite ghost_worker, *one exact job only*.

This is an opt-in foreground bridge, NOT a daemon, terminal, browser/GUI,
model call, application-control connector, or unattended ghost employee.
No arbitrary code from GitHub is ever executed.  v1 accepts only system.ping
and (with explicit local approval) inventory of a new isolated sandbox.

The private control repo does NOT run a self-hosted GitHub Actions runner.
Request token has only scoped metadata/contents-read/issues-write rights;
execution happens locally and is bounded by the existing ghost_worker.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import closing
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request

import ghost_worker

API = 'https://api.github.com'
ROOT_REPO = 'TeamRovor/'
PUBLIC_REPO = 'TeamRovor/rovor-video-engine'
REPO = re.compile(r'^TeamRovor/[a-zA-Z0-9][a-zA-Z0-9._-]{2,99}$')
JOB = re.compile(r'^[a-z0-9][a-z0-9-]{5,63}$')
MAX_REMOTE_SIZE = 2048
SANDBOX = 'Mac-Control-Sandbox'
STATE = 'Mac-Control-State'
MARKER = 'receipt-posted.json'


class Refused(ValueError):
    """Fail closed; CLI intentionally never prints sensitive exception detail."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _transport(method, path, token, body=None):
    """HTTPS-only authenticated GitHub JSON request with redirects forbidden."""
    if (not isinstance(path, str) or not path.startswith('/repos/')
            or any(c in path for c in ('\r', '\n', '\x00'))):
        raise Refused('invalid API path')
    if not token or '\r' in token or '\n' in token:
        raise Refused('missing or malformed token')
    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    data = None
    if body is not None:
        if method != 'POST':
            raise Refused('body requires POST')
        data = json.dumps(body, separators=(',', ':')).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(request, timeout=20) as response:
            raw = response.read(32769)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        # Never print endpoint, token, private repo errors, native response body.
        raise Refused('GitHub request failed (' + type(exc).__name__ + ')') from None
    if len(raw) > 32768:
        raise Refused('Oversized GitHub response')
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise Refused('Malformed GitHub JSON') from None


def repo_name(name):
    if not isinstance(name, str) or not REPO.fullmatch(name) or name == PUBLIC_REPO:
        raise Refused('Expected a distinct TeamRovor private control repository')
    return name


def job_name(value):
    if not isinstance(value, str) or not JOB.fullmatch(value):
        raise Refused('Invalid bounded job ID')
    return value


def validate_private(metadata, expected):
    if (not isinstance(metadata, dict)
            or metadata.get('full_name') != expected
            or metadata.get('private') is not True
            or metadata.get('archived') is True
            or metadata.get('disabled') is True):
        raise Refused('Remote control repository not confirmed private and active')


def validate_packet(data, job_id, allow_inventory=False):
    if not isinstance(data, dict) or set(data) != {'schema', 'id', 'kind', 'payload'}:
        raise Refused('Unrecognized remote task structure')
    if type(data['schema']) is not int or data['schema'] != 1 or data['id'] != job_id:
        raise Refused('Task version/identity mismatch')
    kind, payload = data['kind'], data['payload']
    if not isinstance(payload, dict):
        raise Refused('Task payload must be an object')
    if kind == 'system.ping' and not payload:
        return kind, {}
    if kind == 'files.inventory' and allow_inventory and payload == {'subpath': '.'}:
        return kind, {'subpath': '.'}
    raise Refused('Task capability not locally approved or unsupported')


def fetch_private_job(repo, job_id, token, *, allow_inventory=False, http=_transport):
    """Read one exact main-branch job; never list or consume arbitrary tasks."""
    repo = repo_name(repo)
    job_id = job_name(job_id)
    prefix = '/repos/' + repo
    validate_private(http('GET', prefix, token), repo)
    content = http('GET', prefix + '/contents/control/jobs/' + job_id + '.json?ref=main', token)
    if (not isinstance(content, dict) or content.get('type') != 'file'
            or content.get('encoding') != 'base64'
            or type(content.get('size')) is not int
            or not 0 < content['size'] <= MAX_REMOTE_SIZE):
        raise Refused('Missing or oversized private control packet')
    try:
        decoded = base64.b64decode(content['content'].replace('\n', ''), validate=True)
        if len(decoded) != content['size'] or len(decoded) > MAX_REMOTE_SIZE:
            raise Refused('Packet size mismatch')
        packet = json.loads(decoded)
    except (ValueError, TypeError, KeyError, UnicodeError, base64.binascii.Error) as exc:
        raise Refused('Invalid private control packet') from None
    kind, payload = validate_packet(packet, job_id, allow_inventory)
    return {'id':job_id,'kind':kind,'payload':payload}


def _check_dir(folder, *, required):
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise Refused('Unsafe local control folder')
    if required and not folder.is_dir():
        raise Refused('Expected existing Rovor Documents workspace')


def local_paths(home, *, create):
    """Confine all local jobs to a new sandbox, never user's media/worktrees."""
    home = Path(home)
    root = home / 'Documents' / 'Rovor'
    _check_dir(home / 'Documents', required=True)
    _check_dir(root, required=True)
    workspace, state = root / SANDBOX, root / STATE
    for part in (workspace, state):
        _check_dir(part, required=False)
    if create:
        for part in (workspace, state):
            part.mkdir(mode=0o700, exist_ok=True)
            _check_dir(part, required=True)
            part.chmod(0o700)
    return workspace, state


def _mark_reported(job_state, issue_number, packet_id):
    marker = job_state / MARKER
    if marker.is_symlink() or marker.exists():
        raise Refused('Receipt marker already exists or redirected')
    payload = json.dumps({'id':packet_id, 'issue':issue_number}, sort_keys=True)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW
    fd = os.open(marker, flags, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(payload + '\n')


def _report_needed(job_state, issue_number, packet_id):
    p = job_state / MARKER
    if p.is_symlink() or (p.exists() and not p.is_file()):
        raise Refused('Unsafe private receipt marker')
    if not p.exists():
        return True
    if p.stat().st_size > 256:
        raise Refused('Invalid receipt marker')
    try:
        marker = json.loads(p.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Invalid receipt marker') from None
    if marker != {'id':packet_id, 'issue':issue_number}:
        raise Refused('Receipt destination mismatch')
    return False


def _run_local(packet, home, *, issue_number, repo, token,
               http=_transport, execution=ghost_worker.run_once):
    """One DB per exact remote ID: cannot dispatch unrelated queued jobs."""
    workspace, state = local_paths(home, create=True)
    per_job = state / packet['id']
    _check_dir(per_job, required=False)
    per_job.mkdir(mode=0o700, exist_ok=True)
    _check_dir(per_job, required=True)
    per_job.chmod(0o700)
    # Preserve existing STOP semantics: do not queue or execute new work.
    for marker in (state / 'STOP', per_job / 'STOP'):
        if marker.is_symlink() or (marker.exists() and not marker.is_file()):
            raise Refused('Unsafe STOP marker')
        if marker.exists():
            return {'status':'stopped','executed':False,'receipt_posted':False}
    with closing(ghost_worker.connect(per_job)) as conn:
        dedupe='private-control:' + packet['id']
        uuid=ghost_worker.enqueue(conn, packet['kind'], packet['payload'], dedupe)
        existing=conn.execute('SELECT status,attempts,result FROM jobs WHERE id=?',(uuid,)).fetchone()
        if existing['status'] == 'queued':
            receipt=execution(conn, workspace, owner='rovor-private-control')
            if receipt is None or receipt.get('id') != uuid:
                raise Refused('Worker did not execute exact reserved task')
        result=conn.execute('SELECT status,attempts FROM jobs WHERE id=?',(uuid,)).fetchone()
        status = result['status']
        attempts = result['attempts']
    # A stale in-progress job must never be automatically replayed by this
    # adapter, regardless of the underlying read-only-worker lease policy.
    public_status = 'needs_review' if status == 'running' else status
    response = {'schema':1, 'id':packet['id'], 'kind':packet['kind'],
                'status':public_status, 'attempts':attempts,
                'native_app_control_verified':False,
                'open_interpreter_control_verified':False,
                'local_only_readonly':True}
    if _report_needed(per_job, issue_number, packet['id']):
        # Issue number is chosen ONLY by the Mac operator, never from remote job.
        # Do not publish private filesystem paths, file inventories or tokens.
        http('POST', '/repos/' + repo + '/issues/' + str(issue_number) + '/comments',
             token, {'body':'ROVOR_PRIVATE_CONTROL_RECEIPT ' +
                            json.dumps(response, sort_keys=True, separators=(',', ':'))})
        _mark_reported(per_job, issue_number, packet['id'])
        return {'status':public_status,'executed':attempts > 0,
                'receipt_posted':True,'job_id':packet['id']}
    return {'status':public_status,'executed':False,
            'receipt_posted':False,'job_id':packet['id']}


def bridge(repo, job_id, *, home, token, issue_number=None,
           execute=False, allow_inventory=False, http=_transport):
    repo = repo_name(repo)
    job_id = job_name(job_id)
    if not token:
        raise Refused('Missing private control authentication')
    if execute and (type(issue_number) is not int or not 1 <= issue_number <= 100000000):
        raise Refused('A fixed private receipt issue number is required')
    packet=fetch_private_job(repo, job_id, token,
                             allow_inventory=allow_inventory,http=http)
    if not execute:
        return {'status':'valid_private_job_dry_run','id':job_id,
                'kind':packet['kind'],'executed':False,'receipt_posted':False}
    return _run_local(packet, home, issue_number=issue_number,
                      repo=repo, token=token, http=http)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True,help='Exact private TeamRovor control repository')
    parser.add_argument('--job-id',required=True,help='Exact job request ID')
    parser.add_argument('--execute',action='store_true',help='Run at most one safe local job')
    parser.add_argument('--allow-inventory',action='store_true',
                        help='Approve inventory only of Mac-Control-Sandbox')
    parser.add_argument('--receipt-issue',type=int,
                        help='Fixed issue number in the same private repository')
    args=parser.parse_args(argv)
    try:
        result=bridge(args.repo,args.job_id,home=Path.home(),
                      token=os.environ.get('ROVOR_PRIVATE_GITHUB_TOKEN'),
                      issue_number=args.receipt_issue,execute=args.execute,
                      allow_inventory=args.allow_inventory)
        print(json.dumps(result, sort_keys=True))
        return 0 if result['status'] in ('valid_private_job_dry_run','succeeded') else 2
    except (Refused, ValueError, OSError, sqlite3.Error):
        # Never emit private URLs, repo errors, local paths, or credentials.
        print(json.dumps({'status':'blocked','execution_verified':False}),file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())