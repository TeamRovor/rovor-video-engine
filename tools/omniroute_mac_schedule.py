#!/usr/bin/env python3
"""Activate only the existing approved-draft queue service after host checks.

No inference, second scheduler, dependency install, native app control, or
automatic approval. An explicit finite work-plan flag enables later submission
by the existing service. Uses an immutable source runtime.
"""
import argparse
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile

REVISION='0a2fcde9b88e68917103a8831ab17c273180b689'
LABEL='com.rovor.ghost-worker.readonly'
RECEIPT_JOB='202fdb8c-149a-401e-b1e2-8b7e001ab46b'
BACKGROUND_PROOF_KEY='rovor-background-auth-proof-v1'


def pause_existing_service(run=subprocess.run):
    target=f'gui/{os.getuid()}/{LABEL}'
    seen=run(['launchctl','print',target],capture_output=True,timeout=10)
    if seen.returncode:raise ValueError('Existing service not positively observed')
    if run(['launchctl','bootout',target],capture_output=True,timeout=10).returncode:
        raise ValueError('Existing service could not be paused')


def build_config(original, python, runtime, state, workspace, *, enable_work_plan=False):
    if original.get('Label') != LABEL:
        raise ValueError('Unexpected existing service label')
    result=dict(original)
    result.update(ProgramArguments=[str(python),str(runtime/'tools/ghost_worker_loop.py'),
        '--state',str(state),'--workspace',str(workspace),'run',
        '--worker-id','rovor-launchd-approved-drafts','--max-jobs','1',
        '--max-seconds','2','--poll-seconds','2','--approve-omniroute-model-use'],
        RunAtLoad=True,KeepAlive=False,StartInterval=300)
    if enable_work_plan:
        result['ProgramArguments'].append('--approve-omniroute-work-plan')
    return result


def atomic_plist(path, config):
    fd,name=tempfile.mkstemp(prefix='.rovor-stage-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            plistlib.dump(config,f);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def activate(path, config, stop, *, ensure_stop, run=subprocess.run):
    """Leave STOP and no loaded service if activation cannot be verified."""
    ensure_stop(stop)
    original=path.read_bytes()
    backup=path.with_name(path.name+'.before-omniroute')
    if backup.is_symlink():
        raise ValueError('Unsafe backup path')
    if not backup.exists():
        fd=os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(original)
    target=f'gui/{os.getuid()}/{LABEL}'
    ok=False
    changed=False
    try:
        atomic_plist(path,config);changed=True
        boot=run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(path)],capture_output=True,timeout=10)
        if boot.returncode:
            raise ValueError('Existing service bootstrap failed')
        seen=run(['launchctl','print',target],capture_output=True,timeout=10)
        if seen.returncode:
            raise ValueError('Loaded service not positively verified')
        # RunAtLoad occurs with STOP present; never remove it before verification.
        stop.unlink()
        ok=True
    finally:
        if not ok:
            ensure_stop(stop)
            if changed:
                run(['launchctl','bootout',target],capture_output=True,timeout=10)
                atomic_plist(path,plistlib.loads(original))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--enable-approved-draft-queue',action='store_true')
    parser.add_argument('--verify-background-access',action='store_true')
    parser.add_argument('--enable-work-plan',action='store_true',
                        help='Enable one finite released setup-acceptance job, without replay')
    args=parser.parse_args(argv)
    if not args.enable_approved_draft_queue:
        print(json.dumps({'status':'dry_run_no_activation','model_requests':0}))
        return 0
    if sys.platform!='darwin':raise ValueError('Requires existing Mac host')
    home=Path.home()
    runtime=home/'Documents/Rovor'/('worker-runtime-'+REVISION)
    python=home/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
    state=home/'Documents/Codex/2026-10-22/new-chat/jane-worker-state'
    workspace=home/'Documents/Rovor'
    path=home/'Library/LaunchAgents'/(LABEL+'.plist')
    stop=state/'STOP'
    for p in (runtime,state,workspace,path):
        if p.is_symlink() or any(x.is_symlink() for x in p.parents) or not p.exists():
            raise ValueError('Existing canonical runtime/state/plist required')
    if not python.is_file() or stat.S_IMODE(state.stat().st_mode)&0o077:
        raise ValueError('Pinned Python and private existing state required')
    for cmd in (['git','-C',str(runtime),'rev-parse','HEAD'],
                ['git','-C',str(runtime),'status','--porcelain']):
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=10,check=True)
        if (cmd[-1]=='HEAD' and r.stdout.strip()!=REVISION) or (cmd[-1]=='--porcelain' and r.stdout.strip()):
            raise ValueError('Pinned source identity/cleanliness mismatch')
    sys.path.insert(0,str(runtime/'tools'))
    import ghost_worker as worker
    import ghost_omniroute_job as omni
    import omniroute_workpack_runner as runner
    import omniroute_draft_review as review
    import omniroute_mac_once as once
    once.ensure_stop(stop)
    conn=worker.connect(state)
    try:
        if conn.execute("SELECT 1 FROM jobs WHERE status='running'").fetchone():
            raise ValueError('Existing job is running; STOP retained')
        domain=subprocess.run(['launchctl','print',f'gui/{os.getuid()}'],capture_output=True,text=True,timeout=10)
        if not once.service_absent_from_domain(domain):
            if not (args.verify_background_access or args.enable_work_plan):
                raise ValueError('Existing service must be positively confirmed unloaded')
            pause_existing_service()
            domain=subprocess.run(['launchctl','print',f'gui/{os.getuid()}'],capture_output=True,text=True,timeout=10)
            if not once.service_absent_from_domain(domain):
                raise ValueError('Existing service pause not verified')
        row=conn.execute('SELECT status,attempts,result FROM jobs WHERE id=?',(RECEIPT_JOB,)).fetchone()
        if not row or row['status']!='needs_review' or row['attempts']!=1:
            raise ValueError('Successful host job evidence missing')
        result=json.loads(row['result'])
        if result.get('draft_status')!='draft_completed_needs_review':
            raise ValueError('Successful draft evidence missing')
        folder=state/'omniroute-drafts'/RECEIPT_JOB
        if review.inspect(runtime,folder,'overnight-acceptance')['status']!='draft_ready_for_human_review':
            raise ValueError('Receipt integrity/source review failed')
        eligible=tuple(worker.ALLOWED|{worker.OMNI_KIND})
        marks=','.join('?' for _ in eligible)
        if conn.execute(f"SELECT 1 FROM jobs WHERE status='running' OR (status='queued' AND kind IN ({marks}))",eligible).fetchone():
            raise ValueError('Activation requires idle approved queue; existing jobs preserved')
        catalog=omni.read_combo_catalog()
        for packet in omni.ROUTES:omni.verify_route(packet,catalog)
        runner.access_key()
        if args.enable_work_plan:
            import ghost_omniroute_feed as feed
            for packet, key in feed.PLAN:
                runner.load_packet(runtime,packet)
            if conn.execute('SELECT 1 FROM jobs WHERE dedupe_key=?',(BACKGROUND_PROOF_KEY,)).fetchone() is None:
                raise ValueError('Background authentication proof required before enabling work plan')
            row=conn.execute('SELECT status,result FROM jobs WHERE dedupe_key=?',(BACKGROUND_PROOF_KEY,)).fetchone()
            proof_result=json.loads(row['result'] or '{}')
            if row['status']!='succeeded' or not all(proof_result.get(k) is True for k in
                    ('free_routes_verified','endpoint_key_available','loopback_auth_verified')):
                raise ValueError('Successful background authentication proof required')
        config=build_config(plistlib.loads(path.read_bytes()),python,runtime,state,workspace,
                            enable_work_plan=args.enable_work_plan)
        proof=subprocess.run(config['ProgramArguments'],capture_output=True,text=True,timeout=10)
        if proof.returncode:raise ValueError('STOP proof failed')
        paused=json.loads(proof.stdout)
        if paused.get('stop_reason')!='stop_requested' or paused.get('executed')!=0:
            raise ValueError('STOP did not block the worker')
        diagnostic=None
        if args.verify_background_access:
            if conn.execute('SELECT 1 FROM jobs WHERE dedupe_key=?',(BACKGROUND_PROOF_KEY,)).fetchone():
                raise ValueError('Background proof already submitted; inspect instead of replay')
            diagnostic=worker.enqueue(conn,'system.omniroute-preflight',{},BACKGROUND_PROOF_KEY)
        activate(path,config,stop,ensure_stop=once.ensure_stop)
        print(json.dumps({'status':'existing_queue_service_loaded','interval_seconds':300,
             'max_jobs_per_tick':1,'max_AI_attempts_per_24h':5,'model_requests_this_setup':0,
             'auto_enqueue':args.enable_work_plan,'work_plan':'finite_once' if args.enable_work_plan else None,
             'native_and_interpreter_enabled':False,
             'raw_AI_output_approved':False,'STOP_verified':True,
             'background_diagnostic_job_id':diagnostic,
             'note':'Only approved queued drafts; no claim of overnight endurance yet'}))
        return 0
    finally:conn.close()


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status':'activation_blocked','error_class':type(exc).__name__}))
        raise SystemExit(2)
