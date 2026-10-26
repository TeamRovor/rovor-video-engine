#!/usr/bin/env python3
"""Read-only employee telemetry. Never emit payloads, drafts, keys or private paths."""
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from omniroute_ops_snapshot import _consistent_worker_copy, _heartbeat, _group

ROLES=('walter','mike','jane','jesse','gale','gus','saul','hank')
SAFE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,199}$')

def safe(value):
    return value if isinstance(value,str) and SAFE.fullmatch(value) else None

def as_json(value):
    try:
        parsed=json.loads(value) if isinstance(value,str) and len(value)<=65536 else {}
        return parsed if isinstance(parsed,dict) else {}
    except (ValueError,TypeError):
        return {}

def project(rows,heartbeat,public_tasks,now):
    grouped={role:[] for role in ROLES};unassigned=0
    for item in rows:
        payload,result=as_json(item['payload']),as_json(item['result'])
        role=result.get('role');role=role.lower() if isinstance(role,str) else None
        task=payload.get('public_task');task_id=task.get('id') if isinstance(task,dict) else None
        if role not in ROLES:
            hint=payload.get('assignment') or payload.get('packet') or task_id
            found=[r for r in ROLES if isinstance(hint,str) and re.search(r'(^|[-_])'+r+r'([-_]|$)',hint)]
            role=found[0] if len(found)==1 else None
        if role not in ROLES:
            unassigned+=1;continue
        title=public_tasks.get(task_id) if isinstance(task_id,str) else None
        if not isinstance(title,str) or not 1<=len(title)<=250:title='Research assignment'
        status=item['status'];lease=item['lease_until']
        if status=='running':
            state='running' if heartbeat.get('recent') is True and type(lease) in (int,float) and lease>now else 'running_unverified'
        else:
            state=_group(status,item['result'])
        updated=item['updated_at'] if type(item['updated_at']) in (int,float) and 0<=item['updated_at']<=now+60 else None
        grouped[role].append({'state':state,'task':title,'updated_at':updated,
            'assigned_route':safe(result.get('route')),
            'configured_model':safe(result.get('selected_model_config_id')),
            'actual_model':None,'model_attribution':'upstream_model_receipt_unavailable',
            'current':status in ('running','queued')})
    employees=[]
    for role in ROLES:
        jobs=grouped[role]
        running=[j for j in jobs if j['state'] in ('running','running_unverified')]
        queued=[j for j in jobs if j['state']=='queued']
        latest=max(running or queued or jobs,key=lambda j:j['updated_at'] or 0,default=None)
        employees.append({'id':role,'name':role.title(),'queued_jobs':len(queued),'running_jobs':len(running),
            'status':latest['state'] if latest else 'no_attributed_job',
            'latest_job':latest,'host_heartbeat':heartbeat.get('recent') is True,
            'online_verified':False})
    return {'snapshot_at':now,'source':'existing_worker_sqlite_read_only','heartbeat':heartbeat,
            'employees':employees,'unassigned_jobs':unassigned,'dispatch_controls':False,
            'note':'Latest recorded work is not necessarily current execution. Configured route/model is not an actual upstream inference receipt.'}


def read_dispatch(state, now, heartbeat):
    """Read only bounded, recent scheduler counters, never private work."""
    if heartbeat.get('recent') is not True:
        return {'status':'unavailable_or_stale'}
    source=Path(state)/'continuous-status.json'
    try:
        if source.is_symlink() or not source.is_file() or source.stat().st_size>65536:
            return {'status':'unavailable_or_stale'}
        data=json.loads(source.read_text())
        if not isinstance(data,dict) or not isinstance(data.get('dispatch'),dict):
            return {'status':'unavailable_or_stale'}
        observed=data.get('observed_at')
        if type(observed) not in (int,float) or not 0<=observed<=now+60 or now-observed>1200:
            return {'status':'unavailable_or_stale'}
        d=data['dispatch']
        reasons={'paced_wait','rolling_quota','eligible','no_queued_work',
                 'existing_work_running','stop_requested',
                 'failure_circuit_requires_review',
                 'independent_pool_capacity_checked_per_claim'}
        result={'status':'recent_scheduler_report',
                'reason':d.get('reason') if d.get('reason') in reasons else 'unknown'}
        for key in ('claims_last_24h','max_claims_24h','queued','running'):
            value=d.get(key)
            result[key]=value if type(value) is int and 0<=value<=100000 else None
        next_at=d.get('next_eligible_at')
        result['next_eligible_at']=next_at if (
            type(next_at) in (int,float) and now-86400<=next_at<=now+172800) else None
        counts=d.get('job_counts')
        review=counts.get('needs_review') if isinstance(counts,dict) else None
        result['needs_review']=review if type(review) is int and 0<=review<=100000 else None
        executed=data.get('executed')
        result['last_tick_executed']=executed if type(executed) is int and 0<=executed<=9 else None
        return result
    except (OSError,UnicodeError,ValueError,TypeError):
        return {'status':'unavailable_or_stale'}

def snapshot(state,public_tasks,now=None):
    now=time.time() if now is None else now
    heartbeat=_heartbeat(state,now=now)
    dispatch=read_dispatch(state,now,heartbeat)
    try:
        with _consistent_worker_copy(state) as conn:
            conn.row_factory=sqlite3.Row
            rows=conn.execute("SELECT payload,result,status,lease_until,updated_at FROM jobs WHERE kind='research.omniroute' ORDER BY updated_at DESC LIMIT 5000").fetchall()
            result=project(rows,heartbeat,public_tasks,now)
            result['dispatch']=dispatch
            return result
    except (OSError,ValueError,sqlite3.Error):
        result=project([],heartbeat,{},now)
        result['dispatch']=dispatch
        result['source']='worker_state_unavailable'
        return result

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    try:
        tasks=json.loads((root/'coordination/tasks.json').read_text())['tasks']
        titles={t['id']:t['title'] for t in tasks if isinstance(t,dict) and isinstance(t.get('id'),str) and isinstance(t.get('title'),str)}
    except (OSError,KeyError,ValueError,TypeError):titles={}
    state=Path(os.environ.get('ROVOR_WORKER_STATE',str(Path.home()/'Documents/Codex/2026-10-22/new-chat/jane-worker-state')))
    print(json.dumps(snapshot(state,titles),separators=(',',':')))
