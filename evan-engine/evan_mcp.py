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
                "properties": {"mp3_path": {"type": "string", "description": "Absolute path to an existing MP3 on this Mac"}},
                "required": ["mp3_path"],
            },
        },
        {
            "name": "evan_render_status",
            "description": "Check progress and locate the MP4 from a previously started Evan render.",
            "inputSchema": {
                "type": "object",
                "properties": {"render_folder": {"type": "string", "description": "Absolute render folder returned by evan_render_mp3"}},
                "required": ["render_folder"],
            },
        },
    ]


def dependency_status():
    config = json.loads((ENGINE / "local_tools.json").read_text())
    missing = [key for key, value in config.items() if not Path(value).exists()]
    return {"ready": not missing, "missing": missing,
            "engine": str(ENGINE), "output_folder": str(OUTPUTS),
            "note": "This MCP controls Evan Engine V3, not Moho."}


def is_running(pid):
    if not pid:
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
        mp3 = Path(supplied).expanduser().resolve()
        if not mp3.is_file() or mp3.suffix.lower() != ".mp3":
            raise ValueError("Provide an existing absolute .mp3 file path.")
        OUTPUTS.mkdir(parents=True, exist_ok=True)
        folder = OUTPUTS / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        folder.mkdir()
        logfile = folder / "render.log"
        with logfile.open("w") as output:
            process = subprocess.Popen(
                [sys.executable, str(ENGINE / "animate_evan.py"), str(mp3), "--output", str(folder)],
                stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
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
        return {"completed": ready, "running": False if ready else is_running(job.get("pid")),
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
                      "serverInfo": {"name": SERVER_NAME, "version": "3.0"}}
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
