#!/usr/bin/env python3
"""Read installed Mac evidence without inference, credentials, claims or service writes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import socket
import sqlite3
import subprocess
import tempfile
import time

import ghost_omniroute_job as gateway
import omniroute_dispatch_pacing as pacing
from omniroute_continuous import queue_health
from install_continuous_worker import configured_budget

PROVIDERS = ('gemini', 'mistral', 'nvidia', 'cohere', 'sambanova',
             'cloudflare-ai', 'groq', 'openrouter', 'huggingface')
LABELS = (pacing.LABEL, 'com.omniroute.autostart', 'com.rovor.hud-reporting',
          'com.rovor.keep-awake', 'com.rovor.mac-host-awake')
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,199}$')


def safe_id(value):
    return value if isinstance(value, str) and ID.fullmatch(value) else None


def timestamp(value):
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return (value if value.tzinfo else value.replace(tzinfo=timezone.utc)).timestamp()
        return float(value) if type(value) in (int, float) else None
    except (ValueError, OverflowError):
        return None


def freshness(value, now):
    at = timestamp(value)
    return ('unknown' if at is None or not 0 < at <= now + 30 else
            'recent' if now - at <= 900 else 'stale')


@contextmanager
def database_copy(path):
    # Copy DB + WAL only if neither changes; SQLite may create SHM only in scratch.
    path = Path(path)
    files = (path, path.with_name(path.name + '-wal'))
    with tempfile.TemporaryDirectory(prefix='rovor-mac-audit-') as folder:
        before = [pacing._signature(p) if os.path.lexists(p) else None for p in files]
        if before[0] is None:
            raise ValueError('database_unavailable')
        for p, signature in zip(files, before):
            if signature is not None:
                shutil.copyfile(p, Path(folder) / p.name)
        if before != [pacing._signature(p) if os.path.lexists(p) else None for p in files]:
            raise ValueError('database_changed_during_observation')
        conn = sqlite3.connect(str(Path(folder) / path.name))
        conn.row_factory = sqlite3.Row
        try:
            if conn.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise ValueError('database_integrity_unverified')
            conn.execute('PRAGMA query_only=ON')
            yield conn
        finally:
            conn.close()


def provider_evidence(conn, now):
    accounts = conn.execute('''SELECT id,provider,is_active,test_status,last_tested,
        CASE WHEN length(api_key)>0 OR length(access_token)>0 THEN 1 ELSE 0 END AS credential_present
        FROM provider_connections ORDER BY provider,id''').fetchall()
    catalog = [json.loads(r['data']) for r in conn.execute('SELECT data FROM combos')]
    result = []
    for provider in PROVIDERS:
        matching = [r for r in accounts if r['provider'] == provider]
        slots = []
        for index, account in enumerate(matching, 1):
            routes = []
            for combo in catalog:
                for model in combo.get('models', []):
                    if model.get('providerId') == provider:
                        binding = model.get('connectionId')
                        if binding is None or binding == account['id']:
                            routes.append({'combo': safe_id(combo.get('name')),
                                'model': safe_id(model.get('model')),
                                'account_binding': 'explicit' if binding else 'unspecified',
                                'single_model': len(combo['models']) == 1})
            usage = [dict(r) for r in conn.execute('''SELECT model,COUNT(*) AS attempts,
                SUM(success) AS successful_requests,SUM(tokens_input) AS input_tokens,
                SUM(tokens_output) AS output_tokens,MAX(timestamp) AS last_attempt_at,
                MAX(CASE WHEN success=1 THEN timestamp END) AS last_success_at
                FROM usage_history WHERE provider=? AND connection_id=? GROUP BY model''',
                (provider, account['id']))]
            for item in usage:
                item['model'] = safe_id(item['model'])
                item['success_freshness'] = freshness(item['last_success_at'], now)
            last_success = max((u['last_success_at'] for u in usage if u['last_success_at']), default=None)
            slots.append({'account_slot': index, 'configured': True,
                'enabled': bool(account['is_active']),
                'credential_present': bool(account['credential_present']),
                'stored_auth_test': account['test_status'] if account['test_status'] in
                    ('active', 'error', 'invalid', 'unknown') else 'unknown',
                'stored_auth_test_at': account['last_tested'],
                'stored_auth_test_freshness': freshness(account['last_tested'], now),
                'reachable_now': 'not_verified', 'inference_verified_now': 'not_verified',
                'last_account_attributed_success_at': last_success,
                'dispatch_eligible': False, 'admission': 'not_verified',
                'zero_cost_entitlement': 'not_verified', 'commercial_use': 'not_verified',
                'quota': {'status': 'not_available_from_this_reader',
                          'used_percent': None, 'remaining': None, 'reset_at': None},
                'routes': routes, 'recorded_usage': usage,
                'usage_scope': 'local_gateway_history_exact_connection_all_time'})
        result.append({'provider': provider, 'configured_accounts': len(matching), 'accounts': slots})
    checks = []
    seen = set()
    for packet, (route, _) in gateway.ROUTES.items():
        if route in seen:
            continue
        seen.add(route)
        try:
            gateway.verify_route(packet, catalog)
            status = 'exact_pinned_route_matches'
        except (ValueError, KeyError, TypeError):
            status = 'route_drift_requires_review'
        checks.append({'route': route, 'status': status,
                       'inference_or_entitlement_verified': False})
    return result, checks


def service_evidence(home, run=subprocess.run):
    result = []
    for label in LABELS:
        item = {'label': label, 'configured': False, 'running': 'not_verified'}
        plist = home / 'Library/LaunchAgents' / (label + '.plist')
        if plist.is_file() and not plist.is_symlink():
            config = plistlib.loads(plist.read_bytes())
            item.update(configured=config.get('Label') == label,
                run_at_load=config.get('RunAtLoad') is True,
                restart_on_exit=config.get('KeepAlive') is True,
                start_interval_seconds=config.get('StartInterval'))
        try:
            p = run(['launchctl', 'print', f'gui/{os.getuid()}/{label}'],
                    capture_output=True, text=True, timeout=5)
            if p.returncode == 0:
                state = re.search(r'^\s*state = (running|waiting|exited|not running)\s*$', p.stdout, re.M)
                item['launchd_state'] = state.group(1) if state else 'unknown'
                item['running'] = state.group(1) == 'running' if state else 'not_verified'
        except (OSError, subprocess.TimeoutExpired):
            pass
        result.append(item)
    return result


def audit(home=None, now=None):
    home, now = Path.home() if home is None else Path(home), time.time() if now is None else now
    report = {'schema_version': 1, 'source': 'installed_mac_read_only_recovery_audit',
              'observed_at': now, 'model_requests': 0, 'installed_state_modified': False,
              'credentials_disclosed': False, 'activation_ready': False}
    try:
        with database_copy(home / '.omniroute/storage.sqlite') as conn:
            report['providers'], report['legacy_route_preflight'] = provider_evidence(conn, now)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        report['provider_evidence'] = 'unavailable_or_schema_changed'
        report['providers'] = [{'provider': p, 'configured_accounts': None, 'accounts': []} for p in PROVIDERS]
    report['services'] = service_evidence(home)
    plist = home / 'Library/LaunchAgents' / (pacing.LABEL + '.plist')
    try:
        config = plistlib.loads(plist.read_bytes())
        args = config['ProgramArguments']
        state = Path(args[args.index('--state') + 1])
        cap, interval = configured_budget(args)
        report['installed_runtime'] = args[1]
        report['installed_policy'] = {'max_claims_24h': cap, 'min_interval_seconds': interval}
        report['stop_present'] = os.path.lexists(state / 'STOP')
        with pacing.snapshot(state) as conn:
            report['job_counts'] = dict(conn.execute('SELECT status,count(*) FROM jobs GROUP BY status'))
            report['dispatch_assessment'] = queue_health(conn, state, now=now,
                max_claims=cap, interval=interval)
            failures = conn.execute('''SELECT j.id,j.status,j.result FROM jobs j JOIN events e ON e.job_id=j.id
                WHERE j.kind=? AND e.event='claimed' ORDER BY e.timestamp DESC,e.id DESC LIMIT 3''',
                ('research.omniroute',)).fetchall()
            report['last_three_claims'] = [{'status': r['status'],
                'draft_status': safe_id(json.loads(r['result'] or '{}').get('draft_status'))} for r in failures]
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        report['worker_evidence'] = 'unavailable_or_schema_changed'
    try:
        with socket.create_connection(('127.0.0.1', 20128), timeout=2):
            report['gateway_tcp'] = 'reachable_auth_not_checked'
    except OSError:
        report['gateway_tcp'] = 'unavailable_in_this_execution_context'
    return report


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(audit(), indent=2, sort_keys=True))
