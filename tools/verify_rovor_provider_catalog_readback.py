#!/usr/bin/env python3
"""Prove that nine authenticated provider catalog checks reach the existing Site D1.

This is an opt-in audit, NOT a provider inference/canary, free-billing check,
queue replenishment, or STOP override. It sends only fixed provider identifiers
to the existing owner-private Site service and emits public-safe diagnostics.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import rovor_cloud_control_report as control

SITE = control.SITE_ORIGIN
ROUTE = control.GHOST_ROUTE
PROVIDERS = tuple(sorted(control.PROVIDERS))


def audit_catalog_persistence(token: str, request=control.safe_request) -> dict:
    rows = []
    if not control.credential(token):
        return {"state": "service_secret_missing", "catalog_received": 0,
                "persisted": 0, "providers": rows}
    # Check the private service boundary before issuing nine catalog reads.
    # A redirect to login or a 401 is a Site transport/auth problem, not a
    # provider failure or an empty catalog. No provider calls are made then.
    code, preflight, _error = request(
        SITE, ROUTE, token, method="POST", document={"operation": "status"}
    )
    safe_code = code if type(code) is int and 0 <= code <= 599 else 0
    if safe_code != 200 or not isinstance(preflight, dict) or (
        preflight.get("execution_source") != "cloud_provider"
        or not isinstance(preflight.get("providers"), list)
        or len(preflight["providers"]) != len(PROVIDERS)
        or {p.get("provider") for p in preflight["providers"] if isinstance(p, dict)}
        != set(PROVIDERS)
    ):
        if safe_code in (401, 403):
            state = "site_service_auth_denied"
        elif 300 <= safe_code < 400:
            state = "site_service_login_redirect"
        elif safe_code == 0:
            state = "site_service_transport_unavailable"
        elif safe_code == 200:
            state = "site_service_contract_invalid"
        else:
            state = "site_service_http_unavailable"
        return {"state": state, "site_http_code": safe_code,
                "catalog_received": 0, "persisted": 0,
                "providers": rows, "inference_verified": False,
                "free_billing_verified": False}
    sent = {}
    for provider in PROVIDERS:
        # The service internally sends GET /models, not POST /chat/completions.
        code, payload, _error = request(
            SITE, ROUTE, token, method="POST",
            document={"operation": "inventory", "provider": provider}
        )
        if code == 200 and isinstance(payload, dict) and payload.get("provider") == provider:
            catalog_ok = (
                payload.get("status") == "catalog_received"
                and type(payload.get("observed_at")) is int
                and payload["observed_at"] > 0
                and isinstance(payload.get("models"), list)
                and len(payload["models"]) <= 20
            )
            sent[provider] = {
                "catalog": "received" if catalog_ok else "not_verified",
                "status": "catalog_received" if catalog_ok else None,
                "observed_at": payload.get("observed_at") if catalog_ok else None,
            }
        else:
            sent[provider] = {"catalog": "unavailable", "status": None, "observed_at": None}

    code, status, _error = request(
        SITE, ROUTE, token, method="POST", document={"operation": "status"}
    )
    valid_status = (
        code == 200 and isinstance(status, dict)
        and status.get("execution_source") == "cloud_provider"
        and isinstance(status.get("providers"), list)
        and len(status["providers"]) == len(PROVIDERS)
        and {item.get("provider") for item in status["providers"] if isinstance(item, dict)}
        == set(PROVIDERS)
    )
    stored = {
        item["provider"]: item for item in status["providers"]
    } if valid_status else {}
    for provider in PROVIDERS:
        result = sent[provider]
        row = stored.get(provider, {})
        last_check = row.get("last_check") if isinstance(row, dict) else None
        recorded = (
            result["catalog"] == "received"
            and isinstance(last_check, dict)
            and last_check.get("provider") == provider
            and last_check.get("status") == result["status"]
            and type(last_check.get("observed_at")) is int
            and last_check["observed_at"] == result["observed_at"]
        )
        rows.append({
            "provider": provider,
            "catalog": result["catalog"],
            "persisted": recorded,
            "admission": "eligible" if isinstance(row, dict) and row.get("admission") == "eligible"
                         else "not_verified",
        })
    catalog_received = sum(r["catalog"] == "received" for r in rows)
    persisted = sum(r["persisted"] for r in rows)
    return {
        "state": "catalog_persistence_verified" if catalog_received == 9 and persisted == 9
                 else ("status_unavailable" if not valid_status else "catalog_or_persistence_incomplete"),
        "catalog_received": catalog_received,
        "persisted": persisted,
        "site_http_code": code if type(code) is int and 0 <= code <= 599 else 0,
        "providers": rows,
        "inference_verified": False,
        "free_billing_verified": False,
    }


def markdown(report: dict) -> str:
    lines = [
        "### Nine-provider catalog and D1 readback",
        "",
        "Authenticated, opt-in fixed-endpoint catalog reads only. **No inference, "
        "billing entitlement, free quota, canary, or online status is proved.**",
        "",
        f"Catalogs received: **{report['catalog_received']} / 9**. "
        f"Checks stored and read back: **{report['persisted']} / 9**.",
        f"Private Site service: **{report['state']}**"
        + (f" (HTTP {report['site_http_code']})" if 'site_http_code' in report else ""),
        "",
        "| Provider | Catalog | Private D1 readback | Eligible inference |",
        "|---|---|---|---|",
    ]
    for row in report["providers"]:
        lines.append(
            f"| {row['provider']} | {row['catalog']} | "
            f"{'confirmed' if row['persisted'] else 'not confirmed'} | {row['admission']} |"
        )
    lines.extend([
        "",
        "If catalogs are received but D1 readback fails, verify the **currently "
        "deployed existing Site source, D1 binding, and catalog-check migration**. "
        "Do not refresh eligibility timestamps, claim online status, or switch to paid routes.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    report = audit_catalog_persistence(os.environ.get("ROVOR_GHOST_SERVICE_TOKEN", ""))
    output = os.environ.get("ROVOR_CATALOG_REPORT_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
            stream.write(markdown(report))
    print(json.dumps({key: report.get(key) for key in (
        "state", "site_http_code", "catalog_received", "persisted")},
        sort_keys=True))
    return 0 if report["state"] == "catalog_persistence_verified" else 1


if __name__ == "__main__":
    sys.exit(main())
