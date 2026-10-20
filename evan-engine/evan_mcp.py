#!/usr/bin/env python3
"""Dependency-free local Codex MCP adapter for the Evan video engine.

This is a separate MCP server, not a Moho plug-in. It does not access the network.
"""
import json
import errno
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

from local_tools import dependency_errors, load_config
from workspace_status import workspace_status

ENGINE = Path(__file__).resolve().parent
OUTPUTS = ENGINE.parent / "evan-videos"
SERVER_NAME = "rovor-evan-v3"


def write_json_atomic(path, value):
    staging = path.with_name(path.name + ".writing")
    staging.write_text(json.dumps(value), encoding="utf-8")
    staging.replace(path)


def tools():
    return [
        {
            "name": "evan_workspace_status",
            "description": "Read this checkout's branch, commit, pending pulls, local-change state and shared task claims from fetched origin/main. Optional fetch refreshes origin refs; never pulls, resets, installs or renders.",
            "inputSchema": {"type": "object", "properties": {
                "fetch": {"type": "boolean", "description": "Refresh origin refs without changing working files; false by default"}
            }},
        },
        {
            "name": "evan_engine_status",
            "description": "Check whether local Evan animation engine dependencies are installed and identify any missing tools.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "evan_render_mp3",
            "description": "Start generating a Rovor Digital animated Evan MP4 from a local MP3; optional SRT captions, scene plan, and character style are supported. Returns a render folder for polling. Works offline with local tools. 60-second audio limit.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "mp3_path": {"type": "string", "description": "Absolute path to an existing local MP3 file"},
                    "captions_path": {"type": "string", "description": "Optional absolute path to an SRT subtitle file"},
                    "plan_path": {"type": "string", "description": "Optional absolute path to a JSON scene plan"},
                    "character": {"type": "string", "enum": ["reference", "vector"], "description": "Character artwork mode; defaults to reference"},
                },
                "required": ["mp3_path"],
            },
        },
        {
            "name": "evan_render_status",
            "description": "Check progress, locate the MP4, and read stage timing diagnostics for a completed Evan render.",
            "inputSchema": {
                "type": "object",
                "properties": {"render_folder": {"type": "string", "description": "Render folder returned by evan_render_mp3"}},
                "required": ["render_folder"],
            },
        },
        {
            "name": "evan_continue_render",
            "description": "Continue a stopped Rovor Digital video render from its saved local stages, optionally using an edited SRT captions file.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "render_folder": {"type": "string", "description": "Render folder returned by evan_render_mp3"},
                    "captions_path": {"type": "string", "description": "Optional absolute path to an edited SRT file"},
                },
                "required": ["render_folder"],
            },
        },
    ]


def dependency_status():
    try:
        config, config_path = load_config()
        missing = dependency_errors(config)
    except ValueError as error:
        return {"ready": False, "missing": ["config"], "error": str(error),
                "engine": str(ENGINE), "output_folder": str(OUTPUTS)}
    return {"ready": not missing, "missing": missing,
            "engine": str(ENGINE), "output_folder": str(OUTPUTS),
            "config": str(config_path),
            "note": "This MCP controls Evan Engine V3, not Moho."}


def is_running(pid):
    if not pid:
        return False
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
            kernel.OpenProcess.restype = ctypes.c_void_p
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle.restype = ctypes.c_bool
            kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
            kernel.GetExitCodeProcess.restype = ctypes.c_bool
            handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            code = ctypes.c_uint32()
            active = kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
            kernel.CloseHandle(ctypes.c_void_p(handle))
            return bool(active and code.value == 259)  # STILL_ACTIVE
        except (OSError, ValueError, TypeError):
            return False
    try:
        waited, _ = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            return False
        return True
    except ChildProcessError:
        pass
    except OSError as error:
        if error.errno == errno.ESRCH:
            return False
        if error.errno not in (errno.ECHILD, errno.EINTR):
            return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def local_file(value, suffix, description):
    if not value:
        return None
    path = Path(str(value)).expanduser()
    if not path.is_absolute() or not path.is_file() or path.suffix.lower() != suffix:
        raise ValueError("Provide an absolute path to an existing " + description + ".")
    return path.resolve()


def start_render(folder, mp3, config_path, resume=False, captions_path=None,
                 plan_path=None, character="reference"):
    command = [sys.executable, str(ENGINE / "animate_evan.py"), str(mp3),
               "--output", str(folder), "--config", str(config_path),
               "--character", character]
    if resume:
        command.append("--resume")
    if captions_path is not None:
        command.extend(["--captions", str(captions_path)])
    if plan_path is not None:
        command.extend(["--plan", str(plan_path)])
    logfile = (folder / ("resume-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".log")
               if resume else folder / "render.log")
    with logfile.open("w", encoding="utf-8") as output:
        launch = {
            "stdout": output,
            "stderr": subprocess.STDOUT,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            launch["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        else:
            launch["start_new_session"] = True
        process = subprocess.Popen(command, **launch)
    write_json_atomic(folder / "mcp_job.json",
                      {"pid": process.pid, "mp3": str(mp3), "config_path": str(config_path),
                       "log_path": str(logfile)})
    return process, logfile


def read_log_tail(path):
    """Read a bounded log tail so frequent status polling stays cheap."""
    try:
        with path.open("rb") as source:
            source.seek(0, os.SEEK_END)
            source.seek(max(0, source.tell() - 8192))
            tail = source.read()
    except OSError:
        return ""
    return tail.decode("utf-8", errors="replace")[-1800:]


def call_tool(name, args):
    if name == "evan_workspace_status":
        fetch = args.get("fetch", False)
        if not isinstance(fetch, bool):
            raise ValueError("fetch must be true or false.")
        return workspace_status(ENGINE.parent, fetch=fetch)
    if name == "evan_engine_status":
        return dict(dependency_status(), workspace=workspace_status(ENGINE.parent))
    if name == "evan_render_mp3":
        status = dependency_status()
        if not status["ready"]:
            raise ValueError("Missing dependencies: " + ", ".join(status["missing"]))
        supplied = str(args.get("mp3_path", "")).strip()
        mp3 = Path(supplied).expanduser()
        if not mp3.is_absolute():
            raise ValueError("Provide an absolute path to an existing .mp3 file.")
        mp3 = mp3.resolve()
        if not mp3.is_file() or mp3.suffix.lower() != ".mp3":
            raise ValueError("Provide an existing absolute .mp3 file path.")
        captions_path = local_file(args.get("captions_path"), ".srt", ".srt captions file")
        plan_path = local_file(args.get("plan_path"), ".json", ".json scene plan")
        if plan_path is not None:
            try:
                plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError("The scene plan must be readable UTF-8 JSON.") from error
            if not isinstance(plan_data, list):
                raise ValueError("The scene plan JSON must contain an array of scenes.")
        character = args.get("character", "reference")
        if character not in ("reference", "vector"):
            raise ValueError("Character mode must be reference or vector.")
        OUTPUTS.mkdir(parents=True, exist_ok=True)
        folder = OUTPUTS / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        process, logfile = start_render(folder, mp3, status["config"],
                                        captions_path=captions_path, plan_path=plan_path,
                                        character=character)
        return {"started": True, "pid": process.pid, "render_folder": str(folder),
                "captions_file": str(folder / "captions.srt"),
                "status_tool": "evan_render_status", "log": str(logfile)}
    if name == "evan_continue_render":
        folder = Path(str(args.get("render_folder", ""))).expanduser().resolve()
        if not folder.is_dir() or folder.parent != OUTPUTS.resolve():
            raise ValueError("That render folder is not one of this engine's jobs.")
        request_path = folder / "render_request.json"
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("That render folder has no readable render request to resume.") from error
        if not isinstance(request, dict) or not request.get("mp3"):
            raise ValueError("The saved render request is incomplete.")
        try:
            job = json.loads((folder / "mcp_job.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            job = {}
        if not isinstance(job, dict):
            job = {}
        if is_running(job.get("pid")):
            raise ValueError("That render is already running.")
        config_path = request.get("config_path")
        try:
            config, resolved_config = load_config(config_path)
        except ValueError as error:
            raise ValueError("The saved local tool configuration is unavailable: " + str(error)) from error
        missing = dependency_errors(config)
        if missing:
            raise ValueError("Missing local tools for this render: " + ", ".join(missing))
        captions_path = local_file(args.get("captions_path"), ".srt", ".srt captions file")
        mp3 = Path(request["mp3"]).expanduser()
        if not mp3.is_file():
            raise ValueError("The source MP3 for this render is no longer available.")
        plan_path = request.get("plan")
        plan_path = Path(plan_path).expanduser() if plan_path else None
        if plan_path is not None and not plan_path.is_file():
            raise ValueError("The scene-plan file saved for this render is no longer available.")
        character = request.get("character", "reference")
        if character not in ("reference", "vector"):
            raise ValueError("The saved character mode is invalid.")
        process, logfile = start_render(folder, mp3, resolved_config, resume=True,
                                        captions_path=captions_path, plan_path=plan_path,
                                        character=character)
        return {"started": True, "pid": process.pid, "render_folder": str(folder),
                "captions_file": str(folder / "captions.srt"),
                "status_tool": "evan_render_status", "log": str(logfile)}
    if name == "evan_render_status":
        folder = Path(str(args.get("render_folder", ""))).expanduser().resolve()
        if not folder.is_dir() or folder.parent != OUTPUTS.resolve():
            raise ValueError("That render folder is not one of this engine's jobs.")
        video = folder / "evan.mp4"
        jobpath = folder / "mcp_job.json"
        try:
            job = json.loads(jobpath.read_text(encoding="utf-8")) if jobpath.exists() else {}
        except (OSError, json.JSONDecodeError):
            job = {}
        if not isinstance(job, dict):
            job = {}
        logfile = folder / "render.log"
        saved_log = job.get("log_path")
        if isinstance(saved_log, str) and saved_log:
            try:
                candidate_log = Path(saved_log).expanduser().resolve()
                candidate_log.relative_to(folder)
                logfile = candidate_log
            except (OSError, RuntimeError, ValueError):
                pass
        if not logfile.is_file():
            logfile = folder / "render.log"
        log = read_log_tail(logfile)
        ready = video.exists() and video.stat().st_size > 0
        running = is_running(job.get("pid"))
        report_path = folder / "render_result.json"
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = None
        report_matches = False
        if ready and isinstance(report, dict):
            video_bytes = report.get("video_bytes")
            report_matches = (report.get("status") == "completed" and
                              report.get("video_file") == video.name and
                              isinstance(video_bytes, int) and not isinstance(video_bytes, bool) and
                              video_bytes == video.stat().st_size)
        completed = (ready and not running and report_matches and
                     ("Created: " + str(video)) in log)
        return {"completed": completed, "running": running,
                "failed": not completed and not running,
                "video": str(video) if ready else None, "log_tail": log,
                "captions_file": str(folder / "captions.srt"),
                "render_report": report if completed else None,
                "render_folder": str(folder)}
    raise ValueError("Unknown tool: " + str(name))


def respond(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def dispatch(req):
    method = req.get("method")
    if "id" not in req:  # notifications do not receive a reply
        return
    request_id = req["id"]
    try:
        if method == "initialize":
            version = req.get("params", {}).get("protocolVersion", "2025-06-18")
            result = {"protocolVersion": version, "capabilities": {"tools": {}},
                      "serverInfo": {"name": SERVER_NAME, "version": "3.4.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": tools()}
        elif method == "tools/call":
            params = req.get("params") or {}
            try:
                data = call_tool(params.get("name"), params.get("arguments") or {})
                result = {"content": [{"type": "text", "text": json.dumps(data)}]}
            except Exception as exc:
                result = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
        else:
            respond({"jsonrpc": "2.0", "id": request_id,
                     "error": {"code": -32601, "message": "Method not found"}})
            return
        respond({"jsonrpc": "2.0", "id": request_id, "result": result})
    except Exception as exc:
        respond({"jsonrpc": "2.0", "id": request_id,
                 "error": {"code": -32603, "message": str(exc)}})


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            dispatch(json.loads(line))
        except Exception as exc:
            print("MCP input error: " + str(exc), file=sys.stderr)
