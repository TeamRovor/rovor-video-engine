#!/usr/bin/env python3
"""Local stdio MCP bridge from ChatGPT MP3 file params to the private render spool."""
from __future__ import annotations

import base64
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

import render_jobs

MAX_UPLOAD = render_jobs.MAX_BYTES
MAX_ARTIFACT = 64 * 1024 * 1024
ALLOWED_SUFFIXES = (".oaiusercontent.com", ".openai.com", ".chatgpt.com")
REDIRECTS = 4

FILE_SCHEMA = {
    "type": "object",
    "properties": {
        "download_url": {"type": "string"},
        "file_id": {"type": "string"},
        "mime_type": {"type": "string"},
        "file_name": {"type": "string"},
    },
    "required": ["download_url", "file_id"],
    "additionalProperties": False,
}


def default_root() -> Path:
    configured = os.environ.get("ROVOR_JOB_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / "Library" / "Application Support" / "Rovor" / "moho-render" / "jobs"


def default_adapter() -> Path:
    configured = os.environ.get("ROVOR_MOHO_ADAPTER")
    if configured:
        return Path(configured).expanduser()
    return default_root().parent / "adapter.json"


def inspect_setup(adapter: Optional[Path] = None) -> dict:
    adapter = adapter or default_adapter()
    ffprobe = shutil.which("ffprobe") is not None
    native_probe = shutil.which("swiftc") is not None and Path(__file__).with_name("media_probe.swift").is_file()
    media_probe = ffprobe or native_probe
    moho_path = Path(os.environ.get("MOHO_EXECUTABLE", "/Applications/Moho.app/Contents/MacOS/Moho")).expanduser()
    moho = moho_path.is_file() and os.access(moho_path, os.X_OK)
    adapter_valid = False
    if adapter.is_file() and not adapter.is_symlink() and not (adapter.stat().st_mode & 0o077):
        try:
            argv = json.loads(adapter.read_text(encoding="utf-8"))
            if isinstance(argv, list) and argv and all(isinstance(item, str) and item for item in argv):
                executable = Path(argv[0]).expanduser()
                adapter_valid = (executable.is_file() and os.access(executable, os.X_OK)) if executable.is_absolute() else shutil.which(argv[0]) is not None
        except (OSError, ValueError, TypeError):
            adapter_valid = False
    blockers = []
    if not media_probe:
        blockers.append("Media verification needs ffprobe or the bundled macOS AVFoundation probe")
    if not moho:
        blockers.append("Moho Pro 14 command-line renderer is not available at its configured path")
    if not adapter_valid:
        blockers.append("A private, valid administrator-owned adapter configuration is missing")
    return {"state": "ready_to_test" if not blockers else "blocked", "mediaProbeAvailable": media_probe,
            "mohoCliAvailable": moho, "adapterConfigValid": adapter_valid,
            "productionBridgeVerified": False, "blockers": blockers}


def _check_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("Invalid attachment URL")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (parsed.scheme != "https" or not host or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None
            or not any(host == suffix[1:] or host.endswith(suffix) for suffix in ALLOWED_SUFFIXES)):
        raise ValueError("Attachment URL is outside the approved ChatGPT file hosts")
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError("Could not resolve attachment host") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Attachment host did not resolve exclusively to public IP addresses")
    return url


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download_to_file(url: str, destination: Path) -> int:
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    current = url
    for redirect in range(REDIRECTS + 1):
        _check_url(current)
        request = Request(current, headers={"Accept": "audio/mpeg, application/octet-stream"})
        try:
            response = opener.open(request, timeout=45)
        except HTTPError as exc:
            if exc.code not in (301, 302, 303, 307, 308) or redirect == REDIRECTS:
                raise ValueError("ChatGPT attachment download failed") from exc
            target = exc.headers.get("Location")
            if not target:
                raise ValueError("Attachment redirect omitted its destination") from exc
            current = urljoin(current, target)
            continue
        except (URLError, TimeoutError, OSError) as exc:
            raise ValueError("ChatGPT attachment download failed") from exc
        with response, destination.open("xb") as out:
            header = response.headers.get("Content-Length")
            if header is not None and (not header.isdigit() or int(header) > MAX_UPLOAD):
                raise ValueError("MP3 exceeds the 25 MiB intake limit")
            total = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD:
                    raise ValueError("MP3 exceeds the 25 MiB intake limit")
                out.write(chunk)
            if total == 0:
                raise ValueError("Uploaded MP3 is empty")
            out.flush()
            os.fsync(out.fileno())
            os.chmod(destination, 0o600)
            return total
    raise ValueError("Too many attachment redirects")


def validate_file_arg(value: object) -> dict:
    if not isinstance(value, dict) or set(value) - set(FILE_SCHEMA["properties"]):
        raise ValueError("Expected one ChatGPT MP3 file argument")
    file_id = value.get("file_id")
    if not isinstance(file_id, str) or not re.fullmatch(r"file[-_][A-Za-z0-9_-]{8,}", file_id):
        raise ValueError("Missing or invalid ChatGPT file ID")
    name = value.get("file_name", "audio.mp3")
    if not isinstance(name, str) or Path(name).name != name or not name.lower().endswith(".mp3"):
        raise ValueError("Attach one .mp3 file")
    mime = value.get("mime_type")
    if mime is not None and (not isinstance(mime, str) or mime.split(";", 1)[0].strip().lower() not in ("audio/mpeg", "audio/mp3", "application/octet-stream")):
        raise ValueError("Attachment must be an MP3 audio file")
    _check_url(value.get("download_url"))
    return value


def _read_status(root: Path, job_id: str) -> dict:
    path = render_jobs.job(root, job_id) / "status.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _start_worker(root: Path, job_id: str, adapter: Path) -> None:
    source = Path(__file__).with_name("render_jobs.py")
    command = [sys.executable, str(source), "--root", str(root), "run", job_id]
    if adapter.is_file() and not adapter.is_symlink():
        mode = adapter.stat().st_mode & 0o777
        if mode & 0o077:
            raise ValueError("Adapter config must be private to its owner (mode 0600 or stricter)")
        command.extend(["--adapter", str(adapter.resolve())])
    elif adapter.exists():
        raise ValueError("Adapter config must be a regular nonsymlink file")
    job_path = render_jobs.job(root, job_id)
    with (job_path / "worker.log").open("ab") as log:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                         close_fds=True, start_new_session=True)


def start_render(file: object, root: Optional[Path] = None, adapter: Optional[Path] = None,
                 downloader=download_to_file) -> dict:
    root = root or default_root()
    adapter = adapter or default_adapter()
    setup = inspect_setup(adapter)
    if setup["state"] != "ready_to_test":
        return {"jobId": "", "state": "blocked", "durationSeconds": None, "reason": "; ".join(setup["blockers"]),
                "message": "No MP3 bytes were transferred or retained because the local render prerequisites are not ready."}
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    upload = validate_file_arg(file)
    temp_dir = root / ".incoming"
    temp_dir.mkdir(mode=0o700, exist_ok=True)
    os.chmod(temp_dir, 0o700)
    fd, name = tempfile.mkstemp(prefix="upload-", suffix=".mp3", dir=temp_dir)
    os.close(fd)
    path = Path(name)
    path.unlink()
    try:
        downloader(upload["download_url"], path)
        job_id = render_jobs.submit(root, path)
    finally:
        path.unlink(missing_ok=True)
    _start_worker(root, job_id, adapter)
    status = _read_status(root, job_id)
    request = json.loads((render_jobs.job(root, job_id) / "request.json").read_text(encoding="utf-8"))
    return {"jobId": job_id, "state": status["state"], "durationSeconds": request["duration"],
            "reason": status.get("reason", ""), "message": _state_message(status["state"], status.get("reason"))}


def _state_message(state: str, reason: Optional[str]) -> str:
    if state == "queued":
        return "MP3 staged in the private local queue; worker is starting."
    if state == "blocked":
        return "MP3 staged, but no approved Moho adapter is configured; no render was started."
    if state == "running":
        return "Moho render worker started; poll status with the returned job ID."
    if state == "review_required":
        return "Artifact passed current technical checks; production-quality gates still require review."
    if state == "failed":
        return "Render worker failed; inspect the machine-readable job status."
    return reason or state


def artifact_resource(root: Path, job_id: str) -> dict:
    job_path = render_jobs.job(root, job_id)
    status = _read_status(root, job_id)
    if status.get("state") != "review_required":
        raise ValueError("No verified render artifact is available")
    media = job_path / "render.mp4"
    if media.is_symlink() or not media.is_file() or media.stat().st_size > MAX_ARTIFACT:
        raise ValueError("Invalid or oversized render artifact")
    if render_jobs.digest(media) != status.get("artifact", {}).get("sha256"):
        raise ValueError("Render artifact checksum changed")
    uri = f"rovor-moho://jobs/{job_id}/render.mp4"
    return {"uri": uri, "name": "render.mp4", "mimeType": "video/mp4", "size": media.stat().st_size,
            "sha256": status["artifact"]["sha256"]}


def resource_bytes(root: Path, uri: str) -> dict:
    match = re.fullmatch(r"rovor-moho://jobs/([0-9a-f]{32})/render\.mp4", uri)
    if not match:
        raise ValueError("Unknown local render resource")
    info = artifact_resource(root, match.group(1))
    data = (render_jobs.job(root, match.group(1)) / "render.mp4").read_bytes()
    return {"contents": [{"uri": info["uri"], "mimeType": "video/mp4", "blob": base64.b64encode(data).decode("ascii")}]} 


def _tool_specs() -> list[dict]:
    return [
        {"name": "check_setup", "title": "Check local Moho setup",
         "description": "Read-only check for media verification, the Moho Pro 14 command-line renderer and a private adapter configuration. It does not open Moho or read a project.",
         "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
         "outputSchema": {"type": "object", "properties": {"state": {"type": "string"}, "mediaProbeAvailable": {"type": "boolean"}, "mohoCliAvailable": {"type": "boolean"}, "adapterConfigValid": {"type": "boolean"}, "productionBridgeVerified": {"type": "boolean"}, "blockers": {"type": "array", "items": {"type": "string"}}}, "required": ["state", "mediaProbeAvailable", "mohoCliAvailable", "adapterConfigValid", "productionBridgeVerified", "blockers"], "additionalProperties": False},
         "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
        {"name": "render_from_mp3", "title": "Render from MP3",
         "description": "Send one uploaded MP3 to this Mac's private Moho job queue and start the trusted host adapter if configured. Without the adapter this only stages the file and returns blocked; it never substitutes the Evan sprite engine.",
         "inputSchema": {"type": "object", "$defs": {"ChatGPTFile": FILE_SCHEMA}, "properties": {"file": {"$ref": "#/$defs/ChatGPTFile"}}, "required": ["file"], "additionalProperties": False},
         "outputSchema": {"type": "object", "properties": {"jobId": {"type": "string"}, "state": {"type": "string"}, "durationSeconds": {"type": ["number", "null"]}, "reason": {"type": "string"}, "message": {"type": "string"}}, "required": ["jobId", "state", "durationSeconds", "reason", "message"], "additionalProperties": False},
         "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True, "idempotentHint": False},
         "_meta": {"openai/fileParams": ["file"], "openai/toolInvocation/invoking": "Sending MP3 to Mac", "openai/toolInvocation/invoked": "Moho job staged"}},
        {"name": "get_render_status", "title": "Get Moho render status",
         "description": "Read the status for a local Moho render job by ID.",
         "inputSchema": {"type": "object", "properties": {"jobId": {"type": "string", "pattern": "^[0-9a-f]{32}$"}}, "required": ["jobId"], "additionalProperties": False},
         "outputSchema": {"type": "object", "properties": {"jobId": {"type": "string"}, "state": {"type": "string"}, "details": {"type": "object"}}, "required": ["jobId", "state", "details"], "additionalProperties": False},
         "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
        {"name": "get_render_artifact", "title": "Get Moho render artifact",
         "description": "Return a verified local MP4 as a resource link when the job passes its technical output checks.",
         "inputSchema": {"type": "object", "properties": {"jobId": {"type": "string", "pattern": "^[0-9a-f]{32}$"}}, "required": ["jobId"], "additionalProperties": False},
         "outputSchema": {"type": "object", "properties": {"jobId": {"type": "string"}, "name": {"type": "string"}, "mimeType": {"type": "string"}, "size": {"type": "integer"}, "sha256": {"type": "string"}, "uri": {"type": "string"}}, "required": ["jobId", "name", "mimeType", "size", "sha256", "uri"], "additionalProperties": False},
         "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    ]


def _result(value: dict) -> dict:
    return {"structuredContent": value, "content": [{"type": "text", "text": json.dumps(value, separators=(",", ":"))}]}


def handle(message: dict, root: Optional[Path] = None) -> Optional[dict]:
    method, ident = message.get("method"), message.get("id")
    params = message.get("params", {})
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": ident, "result": {"protocolVersion": params.get("protocolVersion", "2025-03-26"), "capabilities": {"tools": {}, "resources": {}}, "serverInfo": {"name": "rovor-moho-local", "version": "0.1.0"}, "instructions": "Accept only user-authorized MP3 attachments. A render starts only through the fixed administrator adapter. Report blocked status if no adapter is configured; never claim a render or Evan rig is ready based on the V3 sprite engine."}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": ident, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": ident, "result": {"tools": _tool_specs()}}
    if method == "resources/list":
        resources = []
        jobs_root = root or default_root()
        if jobs_root.is_dir():
            for directory in jobs_root.iterdir():
                if re.fullmatch(r"[0-9a-f]{32}", directory.name) and directory.is_dir() and not directory.is_symlink():
                    try:
                        item = artifact_resource(jobs_root, directory.name)
                        resources.append({k: item[k] for k in ("uri", "name", "mimeType", "size")})
                    except (OSError, ValueError, KeyError, TypeError):
                        pass
        return {"jsonrpc": "2.0", "id": ident, "result": {"resources": resources}}
    if method == "resources/read":
        try:
            return {"jsonrpc": "2.0", "id": ident, "result": resource_bytes(root or default_root(), params["uri"])}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32000, "message": str(exc)}}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments", {})
        try:
            jobs_root = root or default_root()
            if name == "check_setup":
                value = inspect_setup()
            elif name == "render_from_mp3":
                value = start_render(args.get("file"), jobs_root)
            elif name == "get_render_status":
                job_id = args.get("jobId", "")
                status = _read_status(jobs_root, job_id)
                value = {"jobId": job_id, "state": status.get("state", "unknown"), "details": status}
            elif name == "get_render_artifact":
                job_id = args.get("jobId", "")
                value = {"jobId": job_id, **artifact_resource(jobs_root, job_id)}
            else:
                raise ValueError("Unknown tool")
            result = _result(value)
            if name == "get_render_artifact":
                result["content"].append({"type": "resource_link", "name": value["name"], "uri": value["uri"], "mimeType": value["mimeType"], "size": value["size"]})
            return {"jsonrpc": "2.0", "id": ident, "result": {"content": result["content"], "structuredContent": result["structuredContent"]}}
        except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
            return {"jsonrpc": "2.0", "id": ident, "result": {"isError": True, "content": [{"type": "text", "text": type(exc).__name__ + ": " + str(exc)}]}}
    if ident is None:
        return None
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": "Method not found"}}


def main() -> int:
    for line in sys.stdin.buffer:
        try:
            message = json.loads(line)
            if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
                raise ValueError("Expected JSON-RPC 2.0 object")
            response = handle(message)
        except Exception as exc:
            ident = locals().get("message", {}).get("id") if isinstance(locals().get("message"), dict) else None
            response = {"jsonrpc": "2.0", "id": ident, "error": {"code": -32602, "message": type(exc).__name__ + ": " + str(exc)}} if ident is not None else None
        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
