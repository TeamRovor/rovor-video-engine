#!/usr/bin/env python3
"""Build an opt-in, bounded macOS LaunchAgent configuration for ROVOR.

Does not install, bootstrap, enable, or start a service. No user credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import sys

LABEL = "com.rovor.ghost-worker.readonly"
MIN_INTERVAL = 300
MAX_INTERVAL = 3600
MAX_JOBS = 100
MAX_SECONDS = 240


def _real_directory(value: Path, label: str) -> Path:
    raw = Path(value).expanduser()
    if raw.is_symlink() or not raw.is_dir():
        raise ValueError(f"{label} must be an existing, non-symlink directory")
    return raw.resolve(strict=True)


def validate_paths(state: Path, workspace: Path, script: Path, python: Path) -> tuple[Path, Path, Path, Path]:
    state = _real_directory(state, "state")
    workspace = _real_directory(workspace, "workspace")
    if state == workspace or state in workspace.parents or workspace in state.parents:
        raise ValueError("state and workspace must be separate non-nested directories")
    if state.stat().st_mode & 0o077:
        raise ValueError("state directory must be private (chmod 700)")
    raw_script = Path(script).expanduser()
    if raw_script.is_symlink() or not raw_script.is_file():
        raise ValueError("worker loop script must be an existing non-symlink file")
    script = raw_script.resolve(strict=True)
    base = script.parent
    for name in ("ghost_worker.py",):
        p = base / name
        if p.is_symlink() or not p.is_file():
            raise ValueError("worker and loop must share the same tools directory")
    raw_python = Path(python).expanduser()
    if not raw_python.is_absolute() or not raw_python.is_file() or not os.access(raw_python, os.X_OK):
        raise ValueError("python must be an absolute existing executable file")
    python = raw_python.resolve(strict=True)
    return state, workspace, script, python


def build_plist(state: Path, workspace: Path, script: Path, python: Path,
                *, interval: int = 600, max_jobs: int = 25, max_seconds: int = 120) -> dict:
    """Return deterministic, no-shell plist payload. No application or shell invoked."""
    if type(interval) is not int or not MIN_INTERVAL <= interval <= MAX_INTERVAL:
        raise ValueError("interval must be an integer 300..3600 seconds")
    if type(max_jobs) is not int or not 1 <= max_jobs <= MAX_JOBS:
        raise ValueError("max_jobs must be an integer 1..100")
    if type(max_seconds) is not int or not 10 <= max_seconds <= min(MAX_SECONDS, interval - 60):
        raise ValueError("max_seconds must be 10..240 and at least 60 seconds below interval")
    state, workspace, script, python = validate_paths(state, workspace, script, python)
    return {
        "Label": LABEL,
        "ProgramArguments": [str(python), str(script), "--state", str(state),
                             "--workspace", str(workspace), "run",
                             "--worker-id", "rovor-launchd-readonly",
                             "--max-jobs", str(max_jobs),
                             "--max-seconds", str(max_seconds),
                             "--poll-seconds", "2"],
        "RunAtLoad": True,
        "StartInterval": interval,
        "KeepAlive": False,
        "StandardOutPath": str(state / "launchd.out.log"),
        "StandardErrorPath": str(state / "launchd.err.log"),
    }


def generate(state: Path, workspace: Path, script: Path, python: Path,
             *, interval: int = 600, max_jobs: int = 25, max_seconds: int = 120) -> dict:
    """Generate inside private state dir, never overwrite an existing different config."""
    cfg = build_plist(state, workspace, script, python, interval=interval,
                      max_jobs=max_jobs, max_seconds=max_seconds)
    payload = plistlib.dumps(cfg, fmt=plistlib.FMT_XML, sort_keys=True)
    state = _real_directory(state, "state")
    dest = state / (LABEL + ".plist")
    if dest.is_symlink():
        raise ValueError("existing launchd plist must not be a symlink")
    if dest.exists():
        if not dest.is_file() or dest.read_bytes() != payload:
            raise ValueError("existing plist differs: inspect/remove it explicitly before regeneration")
        created = False
    else:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(dest, flags, 0o600)
        except FileExistsError:
            raise ValueError("plist appeared concurrently; inspect and retry") from None
        try:
            with os.fdopen(fd, "wb") as fp:
                fp.write(payload)
                fp.flush()
                os.fsync(fp.fileno())
        except BaseException:
            dest.unlink(missing_ok=True)
            raise
        created = True
    return {"plist": str(dest), "sha256": hashlib.sha256(payload).hexdigest(),
            "created": created, "installed": False, "started": False,
            "scope": "read-only and opt-in"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--script", type=Path, default=Path(__file__).with_name("ghost_worker_loop.py"))
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--interval", type=int, default=600)
    parser.add_argument("--max-jobs", type=int, default=25)
    parser.add_argument("--max-seconds", type=int, default=120)
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("Host installation is supported only on macOS; use unit tests on other platforms")
    if sys.version_info < (3, 11):
        parser.error("Use a Python 3.11+ interpreter")
    print(json.dumps(generate(args.state, args.workspace, args.script, args.python,
                              interval=args.interval, max_jobs=args.max_jobs,
                              max_seconds=args.max_seconds), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
