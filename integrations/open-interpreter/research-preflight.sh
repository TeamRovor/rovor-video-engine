#!/usr/bin/env bash
# No model requests, installs, configuration changes or persistent report files.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root"
export PYTHONDONTWRITEBYTECODE=1

printf 'ROVOR research preflight (no inference)\nCommit: '
git rev-parse HEAD
if git diff --quiet && git diff --cached --quiet; then
  printf 'Tracked files: clean (untracked files not assessed)\n'
else
  printf 'Tracked files: modified; this is not an exact committed-source test\n'
fi
printf '\nTested source blob identities:\n'
git hash-object tools/interpreter_research_job.py tests/test_interpreter_research_job.py
printf '\nOffline regression checks:\n'
python3 -B -m unittest discover -s tests -p test_interpreter_research_job.py -v
printf '\nNo-model packet validation:\n'
python3 -B tools/interpreter_research_job.py --workspace "$root" \
  --packet integrations/open-interpreter/research-jobs/fcp-intro.example.json

printf '\nLocal host / CLI checks (version and help only):\n'
python3 -B - <<'PY'
from pathlib import Path
import os
import platform
import re
import shutil
import signal
import subprocess
import sys

blocked = platform.system() != "Darwin"
print("Platform:", platform.system(), platform.machine())
if blocked:
    print("BLOCKED: this is not the actual Mac host proof.")
config = Path(".openinterpreter/config.toml")
if not config.is_file():
    blocked = True
    print("BLOCKED: project Interpreter config is missing.")
else:
    print("Project config: present; effective settings and MCP permissions NOT verified.")
binary = shutil.which("interpreter")
if not binary:
    print("BLOCKED: interpreter executable is not on PATH.")
    sys.exit(2)
if os.name != "posix":
    print("BLOCKED: CLI probes require POSIX process cleanup.")
    sys.exit(2)
for args in (["--version"], ["exec", "--help"]):
    child = None
    try:
        child = subprocess.Popen([binary] + args, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        output, _ = child.communicate(timeout=10)
        if child.returncode:
            blocked = True
            print("BLOCKED:", " ".join(args), "exit", child.returncode,
                  "(raw diagnostics omitted; inspect locally).")
            continue
        if args == ["--version"]:
            version = re.search(rb"\b\d+\.\d+\.\d+\b", output)
            print("Interpreter version:", version.group().decode() if version else "unrecognized")
            if version is None:
                blocked = True
        else:
            flags = [b"--sandbox", b"--ask-for-approval", b"--ephemeral"]
            missing = [f.decode() for f in flags if f not in output]
            print("Exec help required flags:", "missing " + ", ".join(missing) if missing else "present")
            blocked = blocked or bool(missing)
    except subprocess.TimeoutExpired:
        blocked = True
        print("BLOCKED:", " ".join(args), "exceeded 10 seconds.")
    except OSError:
        blocked = True
        print("BLOCKED: unable to start the installed CLI.")
    finally:
        if child is not None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.communicate()
print("Model, provider budget, foreground /agent, /mcp and FCP connection: NOT verified.")
print("No inference or unattended worker was requested by this diagnostic.")
sys.exit(2 if blocked else 0)
PY
