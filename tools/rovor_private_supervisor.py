#!/usr/bin/env python3
"""Opt-in macOS user LaunchAgent for the existing PRIVATE ROVOR poller.

A launchd user job executes ONE bounded foreground/private-queue poll per tick.
No self-hosted Actions runner, new job queue, external shell, FCP, model call,
automatic installation, client-media access or arbitrary command execution.

This module does not install/activate itself. A real Mac user must separately
stage (--approve-stage) and activate (--approve-activate). The private control
token stays in macOS Keychain, NEVER in a plist, GitHub, CLI args or logs.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys

import ghost_private_control as control
import ghost_private_control_loop as poller

LABEL = "com.rovordigital.private-control-supervisor"
KEYCHAIN_SERVICE = "rovordigital.private-control.github-token"
APP_FOLDER = "ROVOR-Private-Supervisor"
CONFIG_FILE = "config.json"
RUNTIME_DIR = "runtime"
RUNTIME_FILES = ("rovor_private_supervisor.py", "ghost_private_control.py",
                 "ghost_private_control_loop.py", "ghost_worker.py")
MAX_RUNTIME_FILE = 512 * 1024
PLIST_FILE = LABEL + ".plist"
INTERVAL = 300
MAX_TICK_SECONDS = 120


class Refused(ValueError):
    pass


def paths(home):
    root = home / "Documents" / "Rovor"
    service = home / "Library" / "Application Support" / APP_FOLDER
    agents = home / "Library" / "LaunchAgents"
    return root, service, agents / PLIST_FILE


def _private_folder(path, create=False):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise Refused("Unsafe supervisor folder")
    if create and not path.exists():
        path.mkdir(mode=0o700, parents=False)
    if not path.is_dir():
        raise Refused("Supervisor folder not present")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise Refused("Supervisor folder not private")


def _safe_file(path, limit=8192):
    if path.is_symlink() or not path.is_file():
        raise Refused("Missing or redirected local file")
    if path.stat().st_size > limit:
        raise Refused("Oversized local file")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise Refused("Private file permissions too broad")
    return path.read_bytes()


def _json_private(config_path):
    # File safety failures must not be reclassified as JSON parse failures.
    # Refused subclasses ValueError and would otherwise be swallowed here.
    raw = _safe_file(config_path)
    try:
        config = json.loads(raw)
    except (UnicodeError, ValueError):
        raise Refused("Invalid local supervisor config") from None
    if (not isinstance(config, dict)
            or set(config) != {"schema", "private_repo", "receipt_issue",
                               "python_executable", "script_path", "runtime_sha256"}
            or type(config.get("schema")) is not int
            or config["schema"] != 2
            or type(config.get("receipt_issue")) is not int
            or not 1 <= config["receipt_issue"] <= 100000000):
        raise Refused("Invalid local supervisor config")
    try:
        control.repo_name(config["private_repo"])
    except (ValueError, TypeError):
        raise Refused("Unsafe private repository name") from None
    digests = config.get("runtime_sha256")
    if (not isinstance(digests, dict) or set(digests) != set(RUNTIME_FILES)
            or any(not isinstance(digest,str) or len(digest)!=64
                   or any(c not in "0123456789abcdef" for c in digest)
                   for digest in digests.values())):
        raise Refused("Missing trusted runtime snapshot digests")
    expected_script = str(config_path.parent / RUNTIME_DIR / RUNTIME_FILES[0])
    if config.get("script_path") != expected_script:
        raise Refused("Runtime script must be isolated private snapshot")
    for key in ("python_executable", "script_path"):
        value = config.get(key)
        if (not isinstance(value, str) or not value.startswith("/")
                or "\n" in value or "\r" in value
                or Path(value).is_symlink() or not Path(value).is_file()):
            raise Refused("Configured executable path unavailable")
    return config


def plist_contents(config,service):
    """Immutable argv: no token, no remote script, no shell, no arbitrary job."""
    return {
        "Label": LABEL,
        "ProgramArguments": [
            config["python_executable"], config["script_path"], "--tick"
        ],
        "RunAtLoad": True,
        "StartInterval": INTERVAL,
        "ProcessType": "Background",
        "StandardOutPath": str(service / "supervisor.stdout.log"),
        "StandardErrorPath": str(service / "supervisor.stderr.log"),
    }


def _new_file(path,blob,mode):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, mode)
    with os.fdopen(fd, "wb") as f:
        f.write(blob)
        f.flush()
        os.fsync(f.fileno())


def stage(home, private_repo, issue, *, script=None, python=None):
    """Local-only staging; does NOT load launchd or access credentials."""
    if sys.platform != "darwin":
        raise Refused("Mac user session required")
    try:
        repo = control.repo_name(private_repo)
    except (control.Refused, ValueError, TypeError):
        raise Refused("Expected separate TeamRovor private control repository") from None
    if type(issue) is not int or not 1 <= issue <= 100000000:
        raise Refused("Invalid fixed private receipt issue")
    root,service,plist = paths(home)
    if root.is_symlink() or not root.is_dir():
        raise Refused("Expected ROVOR Documents root missing")
    library=home / "Library"
    support=library / "Application Support"
    agents=plist.parent
    for parent in (library,support,agents):
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise Refused("Unsafe LaunchAgent parent")
    if not library.is_dir() or not support.is_dir():
        raise Refused("Expected existing macOS user Library")
    # Create user LaunchAgents folder only on explicit stage.
    if not agents.exists():
        agents.mkdir(mode=0o700)
    if plist.exists() or plist.is_symlink():
        raise Refused("Existing LaunchAgent must be reviewed, never overwritten")
    if service.exists() or service.is_symlink():
        raise Refused("Supervisor service config already staged; refusing replay")
    script=Path(script or __file__).absolute()
    python_input=Path(python or sys.executable).absolute()
    if script.is_symlink() or not script.is_file():
        raise Refused("Missing or redirected local source")
    # Python installed by Homebrew/pyenv commonly uses a symlink. Resolve
    # that locally *before* pinning the exact reviewed ProgramArguments.
    try:
        python=python_input.resolve(strict=True)
    except (OSError,RuntimeError):
        raise Refused("Local Python executable missing") from None
    if not python.is_file():
        raise Refused("Local Python executable missing")
    if script.name != RUNTIME_FILES[0]:
        raise Refused("Expected exact reviewed supervisor module")
    # Freeze one private local runtime. An ordinary Git checkout update must
    # never silently change unattended code with access to Mac Keychain.
    inputs={}
    for name in RUNTIME_FILES:
        source=script.parent/name
        if source.is_symlink() or not source.is_file():
            raise Refused("Missing or redirected runtime dependency")
        with source.open("rb") as stream:
            blob=stream.read(MAX_RUNTIME_FILE+1)
        if len(blob)>MAX_RUNTIME_FILE:
            raise Refused("Runtime source file too large")
        inputs[name]=blob
    snapshot=service/RUNTIME_DIR
    config = {
        "schema": 2,
        "private_repo": repo,
        "receipt_issue": issue,
        "python_executable": str(python),
        "script_path": str(snapshot/RUNTIME_FILES[0]),
        "runtime_sha256": {name:hashlib.sha256(blob).hexdigest()
                           for name,blob in inputs.items()},
    }
    service.mkdir(mode=0o700)
    _private_folder(service)
    snapshot.mkdir(mode=0o700)
    _private_folder(snapshot)
    for name,blob in inputs.items():
        _new_file(snapshot/name,blob,0o600)
    data=(json.dumps(config,indent=2,sort_keys=True)+"\n").encode()
    _new_file(service / CONFIG_FILE, data, 0o600)
    payload=plistlib.dumps(plist_contents(config,service),sort_keys=True)
    _new_file(plist,payload,0o600)
    return {"status":"staged_not_running",
            "launchagent_created":True,
            "private_control_connection_verified":False,
            "token_written_to_plist":False,
            "mac_app_control_verified":False}


def _check_stage(home):
    root,service,plist=paths(home)
    if not root.is_dir() or root.is_symlink():
        raise Refused("Expected ROVOR root unavailable")
    for parent in (home / "Library", home / "Library" / "Application Support",
                   plist.parent):
        if parent.is_symlink() or not parent.is_dir():
            raise Refused("Unsafe local LaunchAgent parent")
    _private_folder(service)
    config=_json_private(service / CONFIG_FILE)
    snapshot=service/RUNTIME_DIR
    _private_folder(snapshot)
    for name in RUNTIME_FILES:
        blob=_safe_file(snapshot/name,MAX_RUNTIME_FILE)
        if hashlib.sha256(blob).hexdigest() != config["runtime_sha256"][name]:
            raise Refused("Private runtime snapshot differs from reviewed code")
    expected=plist_contents(config,service)
    # Keep permission/symlink errors distinct from corrupt plist syntax.
    raw_plist=_safe_file(plist,16000)
    try:
        loaded=plistlib.loads(raw_plist)
    except (ValueError, TypeError, plistlib.InvalidFileException):
        raise Refused("Malformed local LaunchAgent") from None
    if loaded!=expected:
        raise Refused("LaunchAgent content differs from reviewed configuration")
    return service,plist,config


def keychain_token(run=subprocess.run):
    """No environment fallback: background login jobs must use Keychain."""
    if sys.platform!="darwin":
        raise Refused("Keychain requires macOS")
    try:
        out=run(["/usr/bin/security","find-generic-password","-s",
                 KEYCHAIN_SERVICE,"-w"],capture_output=True,text=True,
                timeout=10,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise Refused("Keychain unavailable") from None
    token=out.stdout.strip() if out.returncode==0 else ""
    if (not token or len(token)>512 or
            any(c in token for c in ("\n","\r","\x00"," "))):
        raise Refused("No valid private control credential in Keychain")
    return token


def tick(home, *, run=subprocess.run, poll=poller.poll, key_lookup=None):
    if sys.platform!="darwin":
        raise Refused("Mac local execution required")
    _service, _plist, config = _check_stage(home)
    if key_lookup is not None:
        token=key_lookup()
    else:
        token=keychain_token(run=run)
    if not token:
        raise Refused("Private credential missing")
    # The existing private bridge validates repo privacy, request types, STOP,
    # deduplication and signed-in operator's fixed receipt issue.
    report=poll(config["private_repo"],token,home,config["receipt_issue"],
                max_jobs=1,max_seconds=MAX_TICK_SECONDS,poll_seconds=60,
                allow_inventory=False)
    return {
        "status":"private_queue_tick_completed",
        "queue_polls":report.get("queue_polls",0),
        "jobs_checked":report.get("jobs_checked",0),
        "jobs_succeeded":report.get("jobs_succeeded",0),
        "stop_reason":report.get("stop_reason","unknown"),
        "native_gui_control_verified":False,
        "ai_model_called":False,
        "unattended_execution_verified":False,
    }


def launchctl(home,verb,*,run=subprocess.run):
    if sys.platform!="darwin":
        raise Refused("Mac GUI launchd session required")
    if verb not in ("activate", "deactivate"):
        raise Refused("Unsupported LaunchAgent operation")
    domain="gui/"+str(os.getuid())
    if verb=="activate":
        # Starting work requires a complete, untampered frozen runtime.
        _service,plist,_config=_check_stage(home)
        command=["/bin/launchctl", "bootstrap", domain, str(plist)]
    else:
        # Emergency shutdown must work even when the config, snapshot or
        # on-disk plist was damaged after launchd loaded the approved service.
        # Use the single hard-coded user service target, never remote input.
        command=["/bin/launchctl", "bootout", domain+"/"+LABEL]
    try:
        proc=run(command,capture_output=True,text=True,timeout=15,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise Refused("launchctl action unavailable") from None
    if proc.returncode:
        raise Refused("launchctl action not confirmed")
    return {
        "status": "activation_dispatched_not_verified" if verb=="activate"
                  else "deactivation_dispatched_not_verified",
        "launchctl_accepted":True,
        "mac_queue_connection_verified":False,
        "native_gui_control_verified":False,
    }


def status(home,*,run=subprocess.run):
    root,service,plist=paths(home)
    staged=service.is_dir() and plist.is_file()
    stage_valid=False
    if staged:
        try:
            _check_stage(home)
            stage_valid=True
        except Refused:
            pass
    # The service may remain loaded even when its installed files are damaged
    # or removed. Query only the fixed user-session label independently of
    # stage integrity; a failed launchctl query is NOT proof it is stopped.
    loaded=False
    observation="not_checked_non_mac"
    if sys.platform=="darwin":
        observation="unavailable"
        try:
            cmd=["/bin/launchctl","print",
                 "gui/"+str(os.getuid())+"/"+LABEL]
            check=run(cmd,capture_output=True,text=True,timeout=8,check=False)
            if check.returncode==0:
                loaded=True
                observation="loaded"
            else:
                observation="not_confirmed"
        except (OSError,subprocess.TimeoutExpired):
            pass
    return {"status":"read_only_supervisor_status",
            "staged":staged,"stage_valid":stage_valid,
            "launchd_loaded":loaded,"launchd_observation":observation,
            "private_queue_job_ever_executed_verified":False,
            "mac_gui_control_verified":False,
            "token_inspected":False}


def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    action=a.add_mutually_exclusive_group(required=True)
    action.add_argument("--status",action="store_true")
    action.add_argument("--stage",action="store_true")
    action.add_argument("--activate",action="store_true")
    action.add_argument("--deactivate",action="store_true")
    action.add_argument("--tick",action="store_true")
    a.add_argument("--repo",help="Approved separate private TeamRovor control repo")
    a.add_argument("--receipt-issue",type=int)
    a.add_argument("--approve-stage",action="store_true")
    a.add_argument("--approve-activate",action="store_true")
    args=a.parse_args(argv)
    try:
        home=Path.home()
        if args.status:
            result=status(home)
        elif args.stage:
            if not args.approve_stage or not args.repo or not args.receipt_issue:
                raise Refused("Explicit stage approval, repo and issue required")
            result=stage(home,args.repo,args.receipt_issue)
        elif args.activate:
            if not args.approve_activate:
                raise Refused("Explicit activation approval required")
            result=launchctl(home,"activate")
        elif args.deactivate:
            result=launchctl(home,"deactivate")
        else:
            result=tick(home)
        print(json.dumps(result,sort_keys=True))
        return 0
    except (Refused,ValueError,OSError,TypeError) as exc:
        # Never show macOS Keychain details, private API URLs or filesystem data.
        print(json.dumps({"status":"refused","reason_class":type(exc).__name__,
                          "native_gui_control_verified":False}),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
