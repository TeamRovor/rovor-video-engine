#!/usr/bin/env python3
"""Inspect real OmniRoute model routing on the Mac; no model calls or keys."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

SAFE = re.compile(r"^[a-z0-9][a-z0-9._:/-]{1,159}$")
ROVOR = re.compile(r"^rovor-[a-z0-9-]{3,90}$")
PACKETS = {
    "Walter": "walter-v2-recovery-proof",
    "Mike": "walter-v2-mike-worker-guard",
    "Jane": "walter-v2-jane-editor-handoff",
    "Jesse": "walter-v2-jesse-animation-qa",
    "Gale": "walter-v2-gale-render-qa",
    "Gus": "walter-v2-gus-business-ops",
    "Saul": "walter-v2-saul-review-ops",
    "Hank": "walter-v2-hank-evidence-audit",
}

class FleetError(ValueError):
    """Stable error codes, not raw provider output."""

def _reject(code):
    raise FleetError(code)

def read_cli(argv, *, run=subprocess.run):
    try:
        p = run(argv, capture_output=True, stdin=subprocess.DEVNULL,
                timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        _reject("cli_unavailable")
    if p.returncode or not isinstance(p.stdout, bytes) or len(p.stdout) > 262144:
        _reject("cli_failed_or_oversized")
    try:
        output = p.stdout.decode("utf-8")
    except UnicodeError:
        _reject("cli_encoding_invalid")
    for match in re.finditer(r"[\[{]", output):
        try:
            data, _ = json.JSONDecoder().raw_decode(output, match.start())
            if isinstance(data, (dict, list)):
                return data
        except ValueError:
            pass
    _reject("cli_json_unavailable")

def _connections(doc):
    if isinstance(doc, list):
        rows = doc
    elif isinstance(doc, dict):
        rows = next((doc[k] for k in ("connections", "providers", "items", "data")
                     if isinstance(doc.get(k), list)), None)
        if rows is None and isinstance(doc.get("data"), dict):
            inner = doc["data"]
            rows = next((inner[k] for k in ("connections", "providers", "items")
                         if isinstance(inner.get(k), list)), None)
    else:
        rows = None
    if not isinstance(rows, list) or len(rows) > 200 or any(not isinstance(x, dict) for x in rows):
        _reject("connection_shape_invalid")
    return rows

def worker_routes():
    try:
        import ghost_omniroute_job
        routes = ghost_omniroute_job.ROUTES
    except (ImportError, AttributeError):
        return None
    if not isinstance(routes, dict):
        return None
    return {role: routes.get(packet) for role, packet in PACKETS.items()}

def inspect(providers, combos, *, routes=None, expected=9):
    if type(expected) is not int or not 1 <= expected <= 64:
        _reject("invalid_expected_model_count")
    conn = _connections(providers)
    rows = combos.get("combos") if isinstance(combos, dict) else None
    if not isinstance(rows, list) or len(rows) > 200:
        _reject("combo_shape_invalid")
    configured = {}
    for entry in rows:
        if not isinstance(entry, dict):
            _reject("combo_shape_invalid")
        name = entry.get("name")
        if not isinstance(name, str) or not name.startswith("rovor-"):
            continue
        if not ROVOR.fullmatch(name) or name in configured:
            _reject("rovor_route_invalid_or_duplicated")
        raw_models = entry.get("models")
        if not isinstance(raw_models, list) or not 1 <= len(raw_models) <= 20:
            _reject("rovor_model_list_invalid")
        models = []
        for item in raw_models:
            if not isinstance(item, dict) or item.get("kind") != "model":
                _reject("rovor_model_entry_invalid")
            model, provider = item.get("model"), item.get("providerId")
            if (not isinstance(model, str) or not SAFE.fullmatch(model)
                    or not isinstance(provider, str) or not SAFE.fullmatch(provider)):
                _reject("rovor_model_entry_invalid")
            models.append(model.lower())
        if len(set(models)) != len(models):
            _reject("rovor_model_duplicated")
        configured[name] = {"models": models,
                            "priority": entry.get("strategy") == "priority",
                            "free_suffix_only": all(m.endswith(":free") for m in models)}
    unique = sorted({x for row in configured.values() for x in row["models"]})
    if routes is not None and not isinstance(routes, dict):
        _reject("worker_route_invalid")
    coverage = {}
    for role, packet in PACKETS.items():
        binding = routes.get(role) if routes else None
        if binding is None:
            coverage[role] = {"packet": packet, "status": "source_not_available"}
            continue
        if (not isinstance(binding, (tuple, list)) or len(binding) != 2
                or not isinstance(binding[0], str) or not ROVOR.fullmatch(binding[0])
                or not isinstance(binding[1], (tuple, list))
                or not binding[1]
                or any(not isinstance(s, str) or not SAFE.fullmatch(s) for s in binding[1])):
            _reject("worker_route_invalid")
        route, members = binding
        installed = configured.get(route)
        state = ("route_missing" if installed is None else
                 "members_changed" if installed["models"] != [m.lower() for m in members]
                 else "configured_not_inference_verified")
        coverage[role] = {"packet": packet, "route": route, "status": state}
    return {"kind": "omniroute_actual_model_coverage",
            "connection_entries": len(conn),
            "rovor_combo_entries": len(configured),
            "distinct_routed_models": len(unique),
            "routed_model_ids": unique,
            "nine_model_target": expected,
            "models_not_visible_in_rovor_routes": max(0, expected - len(unique)),
            "combos": dict(sorted(configured.items())),
            "worker_route_coverage": coverage,
            "model_requests": 0,
            "upstream_free_quota_verified": False,
            "working_models_verified": False,
            "unattended_job_completion_verified": False,
            "note": "Connections are not model IDs; model IDs are not successful inference. Free suffix is not billing proof."}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-models", type=int, default=9)
    parser.add_argument("--require-nine-routed", action="store_true")
    args = parser.parse_args(argv)
    local = Path.home() / ".local/bin/omniroute"
    executable = str(local) if local.is_file() and local.stat().st_mode & 0o111 else shutil.which("omniroute")
    if not executable:
        print(json.dumps({"status": "cli_unavailable", "model_requests": 0}))
        return 2
    try:
        report = inspect(read_cli([executable, "providers", "list", "--json"]),
                         read_cli([executable, "combo", "list", "--json"]),
                         routes=worker_routes(), expected=args.expected_models)
    except FleetError as e:
        print(json.dumps({"status": str(e), "model_requests": 0}))
        return 2
    print(json.dumps(report, sort_keys=True, indent=2))
    return 3 if args.require_nine_routed and report["models_not_visible_in_rovor_routes"] else 0

if __name__ == "__main__":
    sys.exit(main())
