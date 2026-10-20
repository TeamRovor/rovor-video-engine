#!/usr/bin/env python3
"""Dependency-free local Codex MCP adapter for the Evan video engine.

This is a separate MCP server, not a Moho plug-in. It does not access the network.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime

from local_tools import dependency_errors, load_config

ENGINE = Path(__file__).resolve().parent
OUTPUTS = ENGINE.parent / "evan-videos"
SERVER_NAME = "rovor-evan-v3"


def tools():
    return [
        {
            "name": "evan_engine_status",
            "description": "Check whether local Evan animation engine dependencies are installed and identify any missing tools.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "evan_render_mp3",
            "description": "Start generating a Rovor Digital animated Evan MP4 from an absolute local MP3 file path; returns a render folder for polling. Works without internet if local tools are present. 60-second audio limit.",
            "inputSchema": {
                "type": "object",
                "properties": {"mp3_path": {"type": "string", "description": "Absolute path to an existing local MP3 file"}},
                "required": ["mp3_path"],
            },
        },
        {
            "name": "evan_render_status",
            "description": "Check progress and locate the MP4 from a previously started Evan render.",
            "inputSchema": {
                "type": "object",
                "properties": {"render_folder": {"type": "string", "description": "Render folder returned by evan_render_mp3"}},
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
            handle = kernel.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False
            code = ctypes.c_uint32()
            active = kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
            kernel.CloseHandle(ctypes.c_void_p(handle))
            return bool(active and code.value == 259)  # STILL_ACTIVE
        except (OSError, ValueError, TypeError):
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def call_tool(name, args):
    if name == "evan_engine_status":
        return dependency_status()
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
        OUTPUTS.mkdir(parents=True, exist_ok=True)
        folder = OUTPUTS / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        logfile = folder / "render.log"
        with logfile.open("w") as output:
            launch = {
                "stdout": output,
                "stderr": subprocess.STDOUT,
                "stdin": subprocess.DEVNULL,
            }
            if os.name == "nt":
                launch["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            else:
                launch["start_new_session"] = True
            process = subprocess.Popen(
                [sys.executable, str(ENGINE / "animate_evan.py"), str(mp3), "--output", str(folder)],
                **launch,
            )
        (folder / "mcp_job.json").write_text(json.dumps({"pid": process.pid, "mp3": str(mp3)}))
        return {"started": True, "pid": process.pid, "render_folder": str(folder),
                "status_tool": "evan_render_status", "log": str(logfile)}
    if name == "evan_render_status":
        folder = Path(str(args.get("render_folder", ""))).expanduser().resolve()
        if not folder.is_dir() or folder.parent != OUTPUTS.resolve():
            raise ValueError("That render folder is not one of this engine's jobs.")
        video = folder / "evan.mp4"
        jobpath = folder / "mcp_job.json"
        job = json.loads(jobpath.read_text()) if jobpath.exists() else {}
        logfile = folder / "render.log"
        log = logfile.read_text(errors="replace")[-1800:] if logfile.exists() else ""
        ready = video.exists() and video.stat().st_size > 0
        running = False if ready else is_running(job.get("pid"))
        return {"completed": ready, "running": running,
                "failed": not ready and not running,
                "video": str(video) if ready else None, "log_tail": log,
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
                      "serverInfo": {"name": SERVER_NAME, "version": "3.2.0"}}
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
