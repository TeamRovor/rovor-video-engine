"""Finite, explicitly enabled work plan for the EXISTING SQLite worker.

No scheduler or inference here. Each released packet is submitted at most once,
including after a failure or source update. New work requires a reviewed release.
"""
import os
from pathlib import Path

import ghost_worker as worker
import omniroute_workpack_runner as workpack

PLAN = (('unattended-readiness', 'rovor-scheduled-unattended-readiness-v1'),)


def feed(conn, state, root):
    if os.path.lexists(Path(state) / 'STOP'):
        return {'status': 'stopped', 'submitted': 0}
    # Leave existing work in order; never reset its status or attempts.
    if conn.execute("SELECT 1 FROM jobs WHERE status='running' OR "
                    "(status='queued' AND kind=?)", (worker.OMNI_KIND,)).fetchone():
        return {'status': 'existing_work', 'submitted': 0}
    for packet, key in PLAN:
        if conn.execute('SELECT 1 FROM jobs WHERE dedupe_key=?', (key,)).fetchone():
            continue
        workpack.load_packet(Path(root), packet)
        if os.path.lexists(Path(state) / 'STOP'):
            return {'status': 'stopped', 'submitted': 0}
        job = worker.enqueue(conn, worker.OMNI_KIND, {'packet': packet}, key)
        return {'status': 'submitted', 'submitted': 1, 'job_id': job}
    return {'status': 'plan_exhausted_review_required', 'submitted': 0}
