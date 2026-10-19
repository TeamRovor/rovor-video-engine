#!/usr/bin/env python3
"""Restricted Rovor Mac runner -> Moho MCP read-only bridge.
Accepts only new JSON files under rovor-production/moho-queue/read-*.json
with empty-argument document_getInfo or document_getLayers calls.
No arbitrary command execution and no Moho project editing.
"""
import json
import os
import pathlib
import re
import select
import subprocess
import sys
import time
import urllib.request

REPO = "TeamRovor/rovor-video-engine"
ISSUE = 6
ALLOWED = {"document_getInfo", "document_getLayers"}
QUEUE_PATH = re.compile(r"^rovor-production/moho-queue/read-[A-Za-z0-9_-]+[.]json$")
NODE = "/usr/local/bin/node"
BRIDGE = pathlib.Path.home() / "Documents/Moho-Astra/MohoMCP-Enhanced/bridge/dist/index.js"

def load_plan():
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        event = json.load(f)
    commit = event.get("head_commit") or {}
    touched = list(commit.get("added") or []) + list(commit.get("modified") or [])
    paths = sorted({p for p in touched if QUEUE_PATH.fullmatch(p)})
    if len(paths) != 1:
        raise RuntimeError("Expected one changed whitelisted read request; got " + repr(paths))
    p = pathlib.Path(paths[0])
    plan = json.loads(p.read_text(encoding="utf-8"))
    if set(plan) != {"task_id", "commands"}:
        raise RuntimeError("Unexpected request fields")
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,72}", plan["task_id"]):
        raise RuntimeError("Bad task ID")
    commands = plan["commands"]
    if not isinstance(commands, list) or not 1 <= len(commands) <= 2:
        raise RuntimeError("Expected 1-2 read commands")
    for command in commands:
        if not isinstance(command, dict) or set(command) != {"name", "arguments"}:
            raise RuntimeError("Malformed read command")
        if command["name"] not in ALLOWED or command["arguments"] != {}:
            raise RuntimeError("Non-read command or unexpected arguments rejected")
    return plan

def rpc_write(proc, ident, method, params=None):
    payload = {"jsonrpc": "2.0", "id": ident, "method": method}
    if params is not None:
        payload["params"] = params
    proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
    proc.stdin.flush()

def rpc_reply(proc, ident, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        readable, _, _ = select.select([proc.stdout], [], [], max(0.0, deadline - time.monotonic()))
        if not readable:
            continue
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("Moho bridge closed output")
        try:
            obj = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue
        if obj.get("id") == ident:
            return obj
    raise TimeoutError("MCP tool response timed out")

def wake_viewport():
    # No mouse/keyboard input, animation edits, or project writes.
    try:
        p = subprocess.run(
            ["/usr/bin/osascript", "-e", 'tell application "Moho" to activate'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
        return p.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def append_issue(body):
    token = os.environ["GH_TOKEN"]
    url = "https://api.github.com/repos/" + REPO + "/issues/" + str(ISSUE) + "/comments"
    req = urllib.request.Request(
        url, data=json.dumps({"body": body[:6500]}).encode("utf-8"),
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        if resp.status != 201:
            raise RuntimeError("GitHub issue comment rejected: HTTP " + str(resp.status))

def run_commands(plan):
    if not BRIDGE.is_file() or not pathlib.Path(NODE).is_file():
        raise RuntimeError("Moho MCP bridge executable missing")
    process = subprocess.Popen(
        [NODE, str(BRIDGE)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, bufsize=0
    )
    results = []
    try:
        rpc_write(process, 1, "initialize",
                  {"protocolVersion": "2025-03-26",
                   "capabilities": {},
                   "clientInfo": {"name": "rovor-github-read-queue", "version": "1"}})
        init = rpc_reply(process, 1, 8)
        if init.get("error"):
            raise RuntimeError("MCP init failed: " + repr(init["error"])[:220])
        process.stdin.write(b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
        process.stdin.flush()
        for idx, cmd in enumerate(plan["commands"], 2):
            name = cmd["name"]
            rpc_write(process, idx, "tools/call", {"name": name, "arguments": {}})
            time.sleep(0.45)
            woke = wake_viewport()
            result = rpc_reply(process, idx, 12)
            if result.get("error"):
                raise RuntimeError(name + " RPC error: " + repr(result["error"])[:250])
            payload = result.get("result") or {}
            texts = [str(c.get("text", "")) for c in payload.get("content", [])
                     if isinstance(c, dict) and c.get("type") == "text"]
            if payload.get("isError"):
                raise RuntimeError(name + " failure: " + " ".join(texts)[:250])
            value = " ".join(texts)
            if not value and payload.get("structuredContent"):
                value = json.dumps(payload["structuredContent"])
            if not value:
                raise RuntimeError(name + " returned empty result")
            results.append((name, woke, value[:1600]))
        return results
    finally:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()

def main():
    task = "unknown"
    report = []
    failure = None
    try:
        plan = load_plan()
        task = plan["task_id"]
        report.extend([
            "### Live Moho read queue result: " + task,
            "Read-only; foreground activation may bring Moho to the front.",
            "No animation keyframes or project files were changed."
        ])
        for name, woke, value in run_commands(plan):
            report.append("PASS " + name + " (foreground activation: " +
                          ("yes" if woke else "not available") + ")\n" + value)
    except Exception as exc:
        failure = type(exc).__name__ + ": " + str(exc)[:400]
        report.append("FAIL " + task + "\n" + failure)
    message = "\n\n".join(report)
    print(message, flush=True)
    append_issue(message)
    if failure:
        sys.exit(1)

if __name__ == "__main__":
    main()
