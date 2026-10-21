#!/usr/bin/env python3
"""Read-only ROVOR Blender MCP configuration/loopback preflight.

No installation, arbitrary code execution, Blender writes, external network
access, permissions changes or server startup is performed. Port probing
only runs when --socket-check is requested; a TCP listener is NOT proof of
an authenticated/working Blender MCP handshake.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_COMMAND = "uvx"
EXPECTED_ARGS = ["--python", "3.11", "mcp-for-blender"]
EXPECTED_ENV = {
    "BLENDER_HOST": "127.0.0.1",
    "BLENDER_PORT": "9876",
    "BLENDER_MCP_SAFE_MODE": "1",
    "UV_PYTHON_PREFERENCE": "only-managed",
}


def validate(config_root: Path = ROOT) -> dict[str, object]:
    """Fail closed if the two documented local MCP configs diverge."""
    path = config_root / ".codex" / "config.toml"
    example = config_root / "integrations" / "blender-mcp" / "mcp.json.example"
    project = tomllib.loads(path.read_text(encoding="utf-8"))
    desktop = json.loads(example.read_text(encoding="utf-8"))
    codex = project.get("mcp_servers", {}).get("blender")
    standard = desktop.get("mcpServers", {}).get("blender")
    if not isinstance(codex, dict) or not isinstance(standard, dict):
        raise ValueError("Blender MCP server missing from project and/or example")
    for kind, cfg in (("Codex", codex), ("JSON example", standard)):
        if cfg.get("command") != EXPECTED_COMMAND:
            raise ValueError(f"{kind} must launch uvx, not arbitrary commands")
        if cfg.get("args") != EXPECTED_ARGS:
            raise ValueError(f"{kind} must use maintained mcp-for-blender Python 3.11")
        if cfg.get("env") != EXPECTED_ENV:
            raise ValueError(f"{kind} must use localhost and safe mode only")
        if set(cfg) != {"command", "args", "env"}:
            raise ValueError(f"{kind} contains unexpected executable options")
    return {
        "validated": True,
        "configured_package": "mcp-for-blender",
        "local_server": "127.0.0.1:9876",
        "safe_mode_configured": True,
        "blender_connected": False,
        "host_addon_installed": "unverified",
        "codex_client_available": "unverified",
    }


def probe_loopback(port: int = 9876, timeout: float = 0.75) -> dict[str, object]:
    """Check if something listens locally, never send code to it."""
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Port must be an integer between 1 and 65535")
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return {"tcp_listener": True, "blender_mcp_handshake": "unverified"}
    except OSError as exc:
        return {
            "tcp_listener": False,
            "blender_mcp_handshake": "unverified",
            "reason": type(exc).__name__,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--socket-check", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = validate(args.root)
        if args.socket_check:
            result["loopback"] = probe_loopback()
    except (ValueError, OSError, json.JSONDecodeError, tomllib.TOMLDecodeError) as exc:
        print(json.dumps({"validated": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
