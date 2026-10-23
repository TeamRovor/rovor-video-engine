#!/usr/bin/env python3
"""Bounded PRIVATE GitHub queue reader for the existing ghost worker bridge.

Foreground only. No service install, arbitrary shell, FCP/Moho/Blender GUI,
model calls, email, or publishing. The private repo is the request channel;
SQLite ghost_worker remains the sole execution-job engine.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import sys
import time

import ghost_private_control as control

MAX_QUEUE = 20
MAX_JOBS = 3
MAX_SECONDS = 3600
MIN_POLL_SECONDS = 60
MAX_POLL_SECONDS = 600
MAX_BYTES = 4096


def limits(*, max_jobs, max_seconds, poll_seconds):
    if type(max_jobs) is not int or not 1 <= max_jobs <= MAX_JOBS:
        raise control.Refused('max jobs outside safe limit')
    if (type(max_seconds) not in (int, float)
            or not 0 < max_seconds <= MAX_SECONDS):
        raise control.Refused('runtime outside safe limit')
    if (type(poll_seconds) not in (int, float)
            or not MIN_POLL_SECONDS <= poll_seconds <= MAX_POLL_SECONDS):
        raise control.Refused('poll interval outside safe limit')


def _private_json(content, max_size=MAX_BYTES):
    if (not isinstance(content, dict)
            or content.get('type') != 'file'
            or content.get('encoding') != 'base64'
            or type(content.get('size')) is not int
            or not 0 < content['size'] <= max_size
            or not isinstance(content.get('content'), str)):
        raise control.Refused('Private queue response must be a bounded file')
    try:
        raw = base64.b64decode(content['content'].replace('\n',''), validate=True)
        if len(raw) != content['size'] or len(raw) > max_size:
            raise control.Refused('Private queue size mismatch')
        return json.loads(raw)
    except (ValueError, TypeError, UnicodeError, base64.binascii.Error):
        raise control.Refused('Malformed private queue response') from None


def fetch_queue(repo, token, *, http=control._transport):
    repo=control.repo_name(repo)
    prefix='/repos/'+repo
    control.validate_private(http('GET',prefix,token),repo)
    info=_private_json(http('GET',prefix+'/contents/control/queue.json?ref=main',token))
    if (not isinstance(info, dict) or set(info) != {'schema','jobs'}
            or type(info['schema']) is not int or info['schema'] != 1
            or not isinstance(info['jobs'],list)
            or len(info['jobs']) > MAX_QUEUE):
        raise control.Refused('Unsupported private queue format')
    jobs=info['jobs']
    if any(not isinstance(j,str) or control.JOB.fullmatch(j) is None for j in jobs):
        raise control.Refused('Invalid private queue job identifier')
    if len(set(jobs)) != len(jobs):
        raise control.Refused('Duplicate private queue job identifier')
    return jobs


def stopped(home):
    workspace,state=control.local_paths(home,create=False)
    marker=state/'STOP'
    if marker.is_symlink() or (marker.exists() and not marker.is_file()):
        raise control.Refused('Invalid private queue STOP file')
    return marker.exists()


def poll(repo,token,home,issue_number,*,max_jobs=1,max_seconds=900,
         poll_seconds=90,allow_inventory=False,http=control._transport,
         monotonic=time.monotonic,sleeper=time.sleep):
    limits(max_jobs=max_jobs,max_seconds=max_seconds,poll_seconds=poll_seconds)
    control.repo_name(repo)
    if type(issue_number) is not int or not 1 <= issue_number <= 100000000:
        raise control.Refused('Private receipt issue number required')
    if not token:
        raise control.Refused('Private authentication missing')
    start=monotonic()
    seen=set()
    attempted=0
    completed=0
    polls=0
    while True:
        if stopped(home):
            reason='stop_requested'
            break
        if attempted >= max_jobs:
            reason='max_jobs'
            break
        if monotonic()-start >= max_seconds:
            reason='max_seconds'
            break
        queue=fetch_queue(repo,token,http=http)
        polls+=1
        for job_id in queue:
            if job_id in seen:
                continue
            if stopped(home):
                reason='stop_requested'
                break
            if attempted >= max_jobs or monotonic()-start >= max_seconds:
                break
            response=control.bridge(repo,job_id,home=home,token=token,
                                    issue_number=issue_number,execute=True,
                                    allow_inventory=allow_inventory,http=http)
            seen.add(job_id)
            if response['status']=='stopped':
                return {'status':'finished','stop_reason':'stop_requested',
                        'jobs_checked':attempted,'jobs_succeeded':completed,
                        'queue_polls':polls,'app_control_verified':False,
                        'unattended_service_installed':False}
            # Older queue entries with a durable posted receipt must not use
            # an approval slot and starve new work later in the same queue.
            # Count new work OR a previously failed receipt now published.
            if response.get('executed') or response.get('receipt_posted'):
                attempted+=1
                if response['status']=='succeeded':
                    completed+=1
        if stopped(home):
            reason='stop_requested'
            break
        if attempted >= max_jobs:
            reason='max_jobs'
            break
        elapsed=monotonic()-start
        if elapsed >= max_seconds:
            reason='max_seconds'
            break
        sleeper(min(poll_seconds,max_seconds-elapsed))
    return {'status':'finished','stop_reason':reason,'jobs_checked':attempted,
            'jobs_succeeded':completed,'queue_polls':polls,
            'app_control_verified':False,'unattended_service_installed':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',required=True)
    p.add_argument('--receipt-issue',type=int,required=True)
    p.add_argument('--max-jobs',type=int,default=1)
    p.add_argument('--max-seconds',type=float,default=900)
    p.add_argument('--poll-seconds',type=float,default=90)
    p.add_argument('--allow-inventory',action='store_true')
    args=p.parse_args(argv)
    try:
        result=poll(args.repo,os.environ.get('ROVOR_PRIVATE_GITHUB_TOKEN'),
                    Path.home(),args.receipt_issue,max_jobs=args.max_jobs,
                    max_seconds=args.max_seconds,poll_seconds=args.poll_seconds,
                    allow_inventory=args.allow_inventory)
        print(json.dumps(result,sort_keys=True))
        return 0 if result['stop_reason'] in ('max_jobs','max_seconds','stop_requested') else 2
    except (control.Refused,ValueError,OSError):
        print(json.dumps({'status':'blocked','private_control_verified':False}),file=sys.stderr)
        return 2


if __name__=='__main__':
    raise SystemExit(main())