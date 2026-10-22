#!/usr/bin/env bash
# One durable, explicitly authorized research job; never installs a service.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
state="$root/../jane-worker-state"
workspace="$root/../jane-worker-workspace"
umask 077
mkdir -p "$workspace"
python3 "$root/tools/interpreter_host_job.py" --check
python3 "$root/tools/ghost_worker.py" --state "$state" --workspace "$workspace" init
python3 "$root/tools/ghost_worker.py" --state "$state" --workspace "$workspace" enqueue \
  --kind research.finalcut --key jane-finalcut-first-queued
if python3 - "$state" <<'PY_STATUS'
import sqlite3, sys
from pathlib import Path
with sqlite3.connect(str(Path(sys.argv[1]) / 'jobs.sqlite3')) as conn:
    status = conn.execute("SELECT status FROM jobs WHERE dedupe_key=?", ('jane-finalcut-first-queued',)).fetchone()[0]
print('Jane queued job status:', status)
sys.exit(0 if status == 'queued' else 1)
PY_STATUS
then
python3 "$root/tools/ghost_worker_loop.py" --state "$state" --workspace "$workspace" run \
  --worker-id jane-research --approve-model-use --max-jobs 1 --max-seconds 360 --poll-seconds 2
fi
python3 "$root/tools/ghost_worker.py" --state "$state" --workspace "$workspace" status
