"""Explicit owner review for releasing the OmniRoute failure circuit."""
import json
import os
from pathlib import Path
import stat
import sys
import time


def _latest_failures(conn, now):
    rows = conn.execute(
        "SELECT j.id,j.status,j.result,e.timestamp FROM events e JOIN jobs j "
        "ON e.job_id=j.id WHERE j.kind='research.omniroute' "
        "AND e.event='claimed' AND e.timestamp>=? "
        "ORDER BY e.timestamp DESC,e.id DESC LIMIT 3", (now - 86400,)).fetchall()
    failed = []
    for row in rows:
        try:
            result = json.loads(row['result'] or '{}')
        except (ValueError, TypeError):
            result = {}
        if (row['status'] != 'failed' and
                not (isinstance(result, dict) and result.get('draft_status') ==
                     'needs_review_no_auto_retry')):
            break
        failed.append(row)
    return failed


def _preflight_ok(result):
    return (isinstance(result, dict) and result.get('ok') is True and
            result.get('read_only') is True and
            result.get('free_routes_verified') is True and
            result.get('endpoint_key_available') is True and
            result.get('loopback_auth_verified') is True and
            result.get('model_requests') == 0)


def release(conn, state, *, now=None):
    """Record reviewed failure IDs; does not alter jobs or retry them."""
    now = time.time() if now is None else now
    is_tty = sys.stdin.isatty()
    uid = os.getuid()
    state = Path(state)
    db = state / 'jobs.sqlite3'
    if (not is_tty or state.is_symlink() or not state.is_dir() or
            not db.is_file() or db.is_symlink()):
        raise ValueError('owner-private interactive state required')
    if (state.stat().st_uid != uid or db.stat().st_uid != uid or
            stat.S_IMODE(state.stat().st_mode) & 0o077 or
            stat.S_IMODE(db.stat().st_mode) & 0o077):
        raise ValueError('owner-private interactive state required')
    if os.path.lexists(state / 'STOP'):
        raise ValueError('STOP blocks circuit recovery')
    import ghost_omniroute_job
    preflight = ghost_omniroute_job.background_preflight()
    if not _preflight_ok(preflight):
        raise ValueError('authenticated route preflight required')
    failed = _latest_failures(conn, now)
    ids = [row['id'] for row in failed]
    if len(ids) != 3:
        raise ValueError('three consecutive failed job IDs required')
    print('Review these failed jobs (no jobs will be replayed):')
    for row in failed:
        try:
            error_class = json.loads(row['result'] or '{}').get('error_class', 'unknown')
        except (ValueError, TypeError):
            error_class = 'unknown'
        print(f"{row['id']}  {error_class}")
    if input('Type the three IDs in displayed order, comma-separated: ').strip() != ','.join(ids):
        raise ValueError('review IDs did not match')
    if input('Type RELEASE CIRCUIT to record owner review: ').strip() != 'RELEASE CIRCUIT':
        raise ValueError('explicit owner release confirmation required')
    conn.execute('BEGIN IMMEDIATE')
    try:
        failed = _latest_failures(conn, now)
        if len(failed) != 3 or [row['id'] for row in failed] != ids:
            raise ValueError('failure history changed during review')
        receipt = {'reviewed_job_ids': ids, 'decision': 'reviewed_failure_no_replay',
                   'owner_uid': uid, 'preflight': {
                       'at': now, 'routes_verified': True,
                       'gateway_auth_verified': True, 'model_requests': 0}}
        conn.execute('INSERT INTO events(job_id,event,detail,timestamp) VALUES(?,?,?,?)',
                     (ids[0], 'owner_failure_circuit_release',
                      json.dumps(receipt, sort_keys=True), now))
        conn.execute('COMMIT')
        return receipt
    except Exception:
        conn.execute('ROLLBACK')
        raise


def release_is_valid(conn, failed_ids, *, state=None, now):
    """Accept only a private, later release receipt for these exact failures."""
    if not failed_ids:
        return False
    state = (Path(conn.execute('PRAGMA database_list').fetchone()[2]).parent
             if state is None else Path(state))
    db = state / 'jobs.sqlite3'
    if (state.is_symlink() or not state.is_dir() or db.is_symlink() or
            not db.is_file() or os.getuid() != state.stat().st_uid or
            db.stat().st_uid != state.stat().st_uid or
            stat.S_IMODE(state.stat().st_mode) & 0o077 or
            stat.S_IMODE(db.stat().st_mode) & 0o077):
        return False
    if os.path.lexists(state / 'STOP'):
        return False
    row = conn.execute(
        "SELECT detail,timestamp FROM events WHERE event='owner_failure_circuit_release' "
        "AND job_id=? ORDER BY timestamp DESC,id DESC LIMIT 1", (failed_ids[0],)).fetchone()
    if row is None or row['timestamp'] <= now - 86400:
        return False
    try:
        receipt = json.loads(row['detail'])
        info = state.stat()
        last_failure = conn.execute(
            "SELECT max(e.timestamp) FROM events e JOIN jobs j ON j.id=e.job_id "
            "WHERE e.event='claimed' AND j.kind='research.omniroute' AND j.id IN (%s)" %
            ','.join('?' for _ in failed_ids), failed_ids).fetchone()[0]
        return (receipt.get('reviewed_job_ids') == failed_ids and
                receipt.get('decision') == 'reviewed_failure_no_replay' and
                receipt.get('owner_uid') == info.st_uid and
                receipt.get('preflight', {}).get('routes_verified') is True and
                receipt.get('preflight', {}).get('gateway_auth_verified') is True and
                receipt.get('preflight', {}).get('model_requests') == 0 and
                row['timestamp'] >= receipt.get('preflight', {}).get('at', float('inf')) and
                last_failure is not None and row['timestamp'] > last_failure)
    except (ValueError, TypeError, AttributeError, OSError):
        return False


def main():
    import argparse
    import ghost_worker
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    state = args.state
    if not sys.stdin.isatty():
        raise SystemExit('Run from the owner Terminal session.')
    conn = ghost_worker.connect(state)
    try:
        failures = _latest_failures(conn, time.time())
        ids = [row['id'] for row in failures]
        if len(ids) != 3:
            raise SystemExit('Three consecutive failed jobs are not present.')
        receipt = release(conn, state)
        print(json.dumps({'released': True, 'reviewed_job_ids': receipt['reviewed_job_ids'],
                          'model_requests': 0}, sort_keys=True))
    except ValueError as exc:
        raise SystemExit(f'Circuit recovery blocked: {exc}') from None
    finally:
        conn.close()


if __name__ == '__main__':
    main()
