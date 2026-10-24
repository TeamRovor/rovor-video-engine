#!/usr/bin/env python3
"""One explicitly approved, non-retrying local OmniRoute free-combo completion probe.

Default: no model call. With BOTH operator approvals, performs exactly one
small public prompt against the previously verified ROVOR free-only route.
Does not claim SQLite jobs, alter LaunchAgents, clear STOP, change route
configuration, replay failed tasks, or store/print a model response.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from urllib import request, error

import ghost_omniroute_job as omni
import omniroute_workpack_runner as workpack
import omniroute_employee_status as status
from omniroute_reasoning_admission import AdmissionError, extract_review_text

PACKET = "runner-blocker"
MODEL = "rovor-fast-free-v1"
STATE = Path.home() / "Documents/Codex/2026-10-22/new-chat/jane-worker-state"
TOKEN_LIMIT = 512
MAX_BODY = 32768
PROMPT = "Reply with exactly READY. Do not include explanations, JSON or markdown."
SYSTEM = "You are an API completion health probe. Respond with READY only."


def _numeric_usage(obj):
    if not isinstance(obj, dict):
        return {}
    usage = obj.get("usage")
    if not isinstance(usage, dict):
        return {}
    out = {}
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        number = usage.get(field)
        if type(number) is int and 0 <= number <= 1000000:
            out[field] = number
    detail = usage.get("completion_tokens_details")
    if isinstance(detail, dict):
        reason = detail.get("reasoning_tokens")
        if type(reason) is int and 0 <= reason <= 1000000:
            out["reasoning_tokens"] = reason
    return out


def diagnose(*, approve_one_call=False, acknowledge_open_circuit=False,
             read_status=None, read_catalog=None, get_key=None, open_local=None):
    out = {"kind": "omniroute_single_free_route_probe",
           "status": "requires_explicit_approval",
           "request_count": 0, "maximum_requests": 1,
           "auto_retry": False, "employee_queue_modified": False,
           "historical_job_replayed": False, "private_response_returned": False,
           "free_combo_configuration_verified": False,
           "upstream_zero_charge_guaranteed": False,
           "model_output_verified": False}
    if read_status is None: read_status = status.inspect
    try:
        live = read_status(STATE)
    except (OSError, ValueError):
        out["status"] = "worker_status_unavailable"
        return out
    if live.get("stop_requested") is not False:
        out["status"] = "owner_stop_or_status_unknown"
        return out
    if live.get("database_status") != "snapshot_readable":
        out["status"] = "existing_database_status_unknown"
        return out
    circuit = live.get("inference_claim_guard_would_block")
    if circuit is not False and circuit is not True:
        out["status"] = "failure_circuit_state_unknown"
        return out
    out["claim_circuit_open"] = circuit
    if not approve_one_call:
        return out
    if circuit and not acknowledge_open_circuit:
        out["status"] = "manual_acknowledgment_required_for_open_circuit"
        return out
    if read_catalog is None: read_catalog = omni.read_combo_catalog
    try:
        catalog = read_catalog()
        actual = omni.verify_route(PACKET, catalog)
        if actual != MODEL:
            out["status"] = "free_combo_mismatch"
            return out
    except (OSError, ValueError, KeyError, TypeError):
        out["status"] = "free_combo_missing_or_changed"
        return out
    out["free_combo_configuration_verified"] = True
    if get_key is None: get_key = workpack.access_key
    if open_local is None: open_local = workpack.safe_local_open
    try:
        key = get_key()
        if type(key) is not str or not key or len(key)>512 or "\r" in key or "\n" in key:
            raise ValueError("invalid local endpoint token")
    except Exception:
        out["status"] = "local_gateway_key_unavailable"
        return out

    # One exact POST to an authenticated loopback. This tiny public prompt
    # neither references any user project nor includes local source text.
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role":"system","content":SYSTEM},
                     {"role":"user","content":PROMPT}],
        "max_tokens": TOKEN_LIMIT,
        "stream": False,
        "temperature": 0.0,
    }).encode("utf-8")
    req = request.Request(workpack.GATEWAY, data=body, method="POST",
                          headers={"Authorization":"Bearer "+key,
                                   "Content-Type":"application/json",
                                   "Accept":"application/json"})
    # Honor an operator STOP that appears after the initial status check
    # but before the one approved network request.
    if os.path.lexists(STATE / "STOP"):
        out["status"] = "owner_stop_requested_before_probe"
        return out
    out["request_count"] = 1
    try:
        with open_local(req, timeout=75) as response:
            if response.status != 200:
                out["status"] = "gateway_non_200"
                return out
            raw = response.read(MAX_BODY+1)
    except error.HTTPError as exc:
        out["status"] = ("http_429" if exc.code == 429 else
                         "http_auth_denied" if exc.code in (401, 403) else
                         "http_upstream_5xx" if 500 <= exc.code <= 599 else
                         "http_unexpected_status")
        return out
    except (OSError, error.URLError, TimeoutError):
        out["status"] = "gateway_transport_or_timeout"
        return out
    except Exception:
        out["status"] = "gateway_response_unavailable"
        return out
    if len(raw) > MAX_BODY:
        out["status"] = "response_too_large"
        return out
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        out["status"] = "response_not_json"
        return out
    if not isinstance(payload, dict):
        out["status"] = "response_not_completion"
        return out
    out["usage"] = _numeric_usage(payload)
    try:
        answer = extract_review_text(payload)
    except AdmissionError as exc:
        # These are fixed source-code error strings, not provider data.
        out["status"] = "admission_" + str(exc)
        return out
    except ValueError:
        out["status"] = "response_validation_failed"
        return out
    if answer.strip() != "READY":
        out["status"] = "completed_visible_but_unexpected_answer"
        out["visible_answer_chars"] = len(answer)
        return out
    out["status"] = "completed_visible_ready"
    out["model_output_verified"] = True
    out["visible_answer_chars"] = len(answer)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approve-one-free-model-request",action="store_true",
                        help="Allow exactly one short public-prompt request; never retry")
    parser.add_argument("--acknowledge-open-circuit",action="store_true",
                        help="Allow one supervised probe despite halted employee queue")
    args=parser.parse_args()
    print(json.dumps(diagnose(
        approve_one_call=args.approve_one_free_model_request,
        acknowledge_open_circuit=args.acknowledge_open_circuit),
        sort_keys=True,indent=2))


if __name__=="__main__":
    main()
