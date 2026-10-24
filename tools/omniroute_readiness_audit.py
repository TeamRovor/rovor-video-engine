#!/usr/bin/env python3
"""ROVOR no-inference OmniRoute readiness diagnosis for an existing Mac worker.

Calls only local CLI inventory, local CLI configuration validation, combo
inventory and an authenticated GET /v1/models on 127.0.0.1. Never calls a
model completion, mutates routes, tests providers upstream, resets SQLite,
clears STOP, displays credentials, or claims jobs.

A local provider validation is NOT proof of provider billing, quota, or
upstream inference success. These distinctions remain explicit in output.
"""
import json
from pathlib import Path
import subprocess
from urllib import request

import ghost_omniroute_job as combos
import omniroute_provider_audit as inventory
import omniroute_workpack_runner as gateway
import omniroute_employee_status as worker


def audit(*, run=subprocess.run, read_catalog=None, key_getter=None,
          gateway_open=None, read_worker=None):
    result = {
        "kind": "omniroute_no_inference_readiness",
        "model_requests": 0,
        "upstream_provider_tests": 0,
        "route_edits": 0,
        "worker_state_changed": False,
        "credentials_disclosed": False,
        "provider_connections_working_verified": False,
        "billing_eligibility_verified": False,
        "usable_ai_completion_verified": False,
    }
    saved = inventory.audit(run=run)
    result["configured_connections_count"] = saved.get("configured_connections_count")
    result["provider_inventory_status"] = saved["omniroute_cli_inventory"]
    result["provider_inventory_blocker"] = saved.get("sanitized_blocker")
    result["provider_connection_counts"] = saved.get("provider_connection_counts")
    # The validate command is local-only. Its CLI exit code does not alone
    # prove every provider is usable or free. Raw stdout/stderr never escape.
    try:
        checked = run(["omniroute", "providers", "validate", "--json"],
                      capture_output=True, text=True, timeout=15, check=False)
        result["provider_configuration_cli"] = (
            "exited_zero_uninterpreted" if checked.returncode == 0
            else "nonzero_exit")
    except (OSError, subprocess.TimeoutExpired):
        result["provider_configuration_cli"] = "unavailable"

    if read_catalog is None:
        read_catalog = combos.read_combo_catalog
    by_route = {}
    try:
        catalog = read_catalog()
        for name in sorted(set(name for name, members in combos.ROUTES.values())):
            matching_packets = [
                packet for packet in combos.ROUTES
                if combos.ROUTES[packet][0] == name]
            try:
                combos.verify_route(matching_packets[0], catalog)
                by_route[name] = "configured_expected_free_suffix"
            except (ValueError, KeyError, TypeError):
                by_route[name] = "route_missing_or_changed"
        result["combo_catalog_status"] = "readable"
    except Exception:
        result["combo_catalog_status"] = "unavailable"
    result["approved_combo_configs"] = by_route
    result["route_free_of_charge_verified"] = False

    # Only a local GET; never POST a chat completion. No model names,
    # bearer credential or untrusted response body are returned.
    if key_getter is None:
        key_getter = gateway.access_key
    if gateway_open is None:
        gateway_open = gateway.safe_local_open
    try:
        key = key_getter()
        if not isinstance(key, str) or not key:
            raise ValueError("missing credential")
        req = request.Request(
            "http://127.0.0.1:20128/v1/models",
            headers={"Authorization": "Bearer " + key,
                     "Accept": "application/json"},
            method="GET")
        with gateway_open(req, timeout=8) as response:
            result["loopback_models_get"] = (
                "authenticated_http_200" if response.status == 200
                else "non_200")
    except Exception:
        result["loopback_models_get"] = "unavailable_or_refused"

    if read_worker is None:
        read_worker = worker.inspect
    try:
        state = read_worker(Path.home() /
            "Documents/Codex/2026-10-22/new-chat/jane-worker-state")
        result["existing_worker"] = {
            "launchagent_loaded": state.get("launchagent_loaded"),
            "stop_requested": state.get("stop_requested"),
            "database_status": state.get("database_status"),
            "ai_claims_last_24h": state.get("ai_claims_last_24h"),
            "inference_claim_guard_would_block":
                state.get("inference_claim_guard_would_block"),
            "review_ready_drafts":
                (state.get("omniroute_draft_counts") or {}).get("review_ready"),
        }
    except (OSError, ValueError):
        result["existing_worker"] = {"database_status": "unavailable"}
    return result


def main():
    print(json.dumps(audit(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
