#!/usr/bin/env python3
"""Read-only, public-safe operations evidence for ROVOR's TWO existing clouds.

No model inference, credential upload, STOP/approval mutation, local Mac checks,
provider discovery, log bodies, job identifiers, or task queue writes.
Use only pinned existing owner-private endpoints. GitHub Actions log/artifact
content contains statuses and aggregates, never credentials or private drafts.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HUD_ORIGIN = "https://rovor-hud-telemetry.rovordigital.workers.dev"
SITE_ORIGIN = "https://rovor-private-hud.mm98z652cq.chatgpt.site"
PROVIDERS = frozenset({
    "groq", "gemini", "cloudflare-ai", "mistral", "nvidia",
    "openrouter", "sambanova", "cohere", "huggingface",
})
ROUTES = (
    "/api/hud/status?period=24h",
    "/api/hud/gemini/models",
    "/api/hud/gemini/usage",
    "/api/chat/models",
    "/api/hud/chat/models",
)
GHOST_ROUTE = "/api/ghost/service"
SERVICE_DENIED = {"401": "service_credential_missing_or_mismatched",
                  "403": "site_access_policy_denied",
                  "404": "site_service_route_unavailable"}

# Fixed, public-safe status codes only. The private Site may return additional
# free-form data, which must never be copied into Actions logs or artifacts.
PROVIDER_ADMISSIONS = frozenset({
    "eligible", "disabled_pending_verification", "not_configured",
    "missing_secret", "unpinned_model", "provider_model_id_mismatch",
    "eligibility_unverified", "eligibility_expired", "canary_unverified",
    "invalid_limits", "invalid_routing_priority", "missing_account",
    "paid_route_denied", "unpinned_upstream",
})
CATALOG_FRESH_MS = 75 * 60 * 1000


def provider_readiness(providers: list, now_ms: int | None = None) -> list[dict]:
    """Redacted private-Site admission summary, NEVER an authorization oracle."""
    if now_ms is None:
        now_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    if not isinstance(providers, list) or len(providers) != len(PROVIDERS):
        return []
    by_name = {
        entry.get("provider"): entry for entry in providers
        if isinstance(entry, dict) and entry.get("provider") in PROVIDERS
    }
    if len(by_name) != len(PROVIDERS):
        return []
    rows = []
    for name in sorted(PROVIDERS):
        item = by_name[name]
        check = item.get("last_check")
        catalog = "not_confirmed"
        if isinstance(check, dict) and check.get("provider") == name and (
            check.get("status") == "catalog_received"
        ):
            observed = check.get("observed_at")
            if type(observed) is int and now_ms - CATALOG_FRESH_MS <= observed <= now_ms + 60000:
                catalog = "fresh_authenticated"
            else:
                catalog = "stale"
        model = item.get("configured_model")
        # Only report whether the *declared* model looks pinned, not whether
        # the upstream actually resolved this model or charges zero dollars.
        model_pinned = bool(
            isinstance(model, str)
            and re.fullmatch(r"[a-zA-Z0-9@][a-zA-Z0-9_./:@-]{0,199}", model)
            and not re.search(r"(^|[/:-])(auto|latest)([/:-]|$)", model, re.I)
        )
        raw_admission = item.get("admission")
        admission = raw_admission if raw_admission in PROVIDER_ADMISSIONS else "unclassified"
        rows.append({
            "provider": name,
            "credentials": "configured" if item.get("credentials_configured") is True else "unverified",
            "catalog": catalog,
            "model": "declared_pinned" if model_pinned else "not_pinned",
            "admission": admission,
            "online": "verified" if item.get("online_verified") is True
                      and admission == "eligible" else "not_verified",
        })
    return rows



class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def credential(value: str, minimum: int = 32) -> bool:
    return isinstance(value, str) and len(value) >= minimum and len(value) <= 1024 and all(
        "!" <= character <= "~" for character in value
    )


def deployment_secrets(env: dict) -> dict:
    google = env.get("ROVOR_GEMINI_API_KEY") or env.get("GEMINI_API_KEY") or ""
    # Reuse the existing private Cloudflare Worker secret when its NAME has
    # been read through the authenticated Cloudflare API. No secret values move.
    existing_cloud_google = env.get("ROVOR_CLOUDFLARE_GEMINI_SECRET_PRESENT") == "true"
    hud_writer = env.get("ROVOR_HUD_WRITER_TOKEN", "")
    hud_reader = env.get("ROVOR_HUD_READER_TOKEN", "")
    d1 = env.get("ROVOR_HUD_D1_ID", "")
    cf_account = env.get("CLOUDFLARE_ACCOUNT_ID", "")
    origin = env.get("ROVOR_HUD_DEPLOY_ORIGIN", "")
    return {
        "cloudflare_api_token": bool(env.get("CLOUDFLARE_API_TOKEN")),
        "cloudflare_account_id": bool(re.fullmatch(r"[a-fA-F0-9]{32}", cf_account)),
        "existing_d1_id": bool(re.fullmatch(r"[a-fA-F0-9]{8}-(?:[a-fA-F0-9]{4}-){3}[a-fA-F0-9]{12}", d1)),
        "private_hud_reader": credential(hud_reader),
        "private_hud_writer": credential(hud_writer) and hud_reader != hud_writer,
        "original_hud_origin": origin.rstrip("/") == HUD_ORIGIN,
        "google_free_project_key": credential(google, 24) or existing_cloud_google,
        "private_site_service_token": credential(env.get("ROVOR_GHOST_SERVICE_TOKEN", "")),
    }


def can_deploy(flags: dict, mode: str, confirmed: bool) -> bool:
    required = ["cloudflare_api_token", "cloudflare_account_id", "existing_d1_id",
                "private_hud_reader", "private_hud_writer", "original_hud_origin"]
    if mode == "deploy_and_test_gemini":
        required.append("google_free_project_key")
        if not confirmed:
            return False
    return all(flags.get(k) is True for k in required)


def safe_request(origin: str, route: str, token: str | None = None,
                 method: str = "GET", document: dict | None = None, opener=None):
    """Fixed destinations only; no redirect following, no raw error strings."""
    if (origin == HUD_ORIGIN and route not in ROUTES + ("/api/hud/status",)) or (
        origin == SITE_ORIGIN and route != GHOST_ROUTE
    ) or origin not in (HUD_ORIGIN, SITE_ORIGIN):
        raise ValueError("unapproved_status_target")
    if method not in ("GET", "POST") or (method == "POST" and route != GHOST_ROUTE):
        raise ValueError("unapproved_status_operation")
    if token is not None and not credential(token):
        return 0, None, "credential_not_configured"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    payload = None
    if document is not None:
        inventory = (
            isinstance(document, dict)
            and set(document) == {"operation", "provider"}
            and document.get("operation") == "inventory"
            and document.get("provider") in PROVIDERS
        )
        if method != "POST" or not (document == {"operation": "status"} or inventory):
            raise ValueError("unapproved_status_body")
        # The only added operation is the private, fixed-provider catalog GET
        # proxied by the existing Site. No model inference, shift, or write
        # operation can be selected by an Actions input.
        payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(origin + route, method=method, headers=headers, data=payload)
    client = opener or urllib.request.build_opener(NoRedirect())
    try:
        with client.open(req, timeout=11) as response:
            code = response.status
            raw = response.read(90001)
            if len(raw) > 90000:
                return code, None, "response_too_large"
            if code != 200:
                return code, None, "http_" + str(code)
            return 200, json.loads(raw.decode("utf-8")), None
    except urllib.error.HTTPError as error:
        return error.code, None, "http_" + str(error.code)
    except (ValueError, UnicodeError):
        return 0, None, "response_contract_unavailable"
    except Exception:
        return 0, None, "network_unavailable"


def summarize_hud(reader: str, opener=None) -> dict:
    answer = {"private": "unverified", "status": "not_checked",
              "gemini_cloud": "not_checked", "gemini_free_text_models_listed": None,
              "gemini_completed_today": None, "gemini_models_with_replies_today": None,
              "cloudflare_ai": "not_checked", "omniroute_mac_optional": "not_checked",
              "mac_telemetry_optional": "unknown"}
    code, _, err = safe_request(HUD_ORIGIN, "/api/hud/status", opener=opener)
    if code == 200:
        answer["private"] = "FAIL_public_telemetry_exposed"
        return answer  # Never fetch private state if anonymous access is exposed.
    if code != 401:
        answer["private"] = "unverified_" + (err or "unknown")
        return answer
    answer["private"] = "verified_401"
    if not credential(reader):
        answer["status"] = "blocked_reader_secret_missing"
        return answer
    code, info, err = safe_request(HUD_ORIGIN, ROUTES[0], reader, opener=opener)
    if code == 200 and isinstance(info, dict) and info.get("source") == "cloud_hud_telemetry":
        answer["status"] = "reachable"
        answer["mac_telemetry_optional"] = info.get("connection") if info.get("connection") in (
            "fresh", "stale", "never_received") else "unknown"
        snap = info.get("snapshot")
        if isinstance(snap, dict):
            names = [x.get("provider") for x in snap.get("connections", []) if isinstance(x, dict)]
            answer["last_reported_provider_connections"] = len(names)
            answer["nine_provider_inventory_in_report"] = len(names) == 9 and len(set(names)) == 9
    else:
        answer["status"] = "unavailable_" + (err or "invalid_source")
    code, m, err = safe_request(HUD_ORIGIN, ROUTES[1], reader, opener=opener)
    if code == 200 and isinstance(m, dict) and m.get("source") == "google_gemini_cloud_direct":
        all_models = m.get("models")
        # Listing is evidence that models were enumerated with the key,
        # not proof a generation request works or has remaining free quota.
        known = {"gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
                 "gemini-3.1-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"}
        direct = [x for x in all_models if x != "gemini-auto-free"] if isinstance(all_models,list) else []
        ready = (m.get("online") is True and m.get("mac_required") is False and
                 isinstance(all_models,list) and all_models[0:1] == ["gemini-auto-free"] and
                 bool(direct) and len(direct) == len(set(direct)) and set(direct) <= known)
        answer["gemini_cloud"] = "key_listed_free_text_models" if ready else "not_configured"
        answer["gemini_free_text_models_listed"] = len(direct) if ready else None
    else:
        answer["gemini_cloud"] = "unavailable_" + (err or "invalid_source")
    code, u, err = safe_request(HUD_ORIGIN, ROUTES[2], reader, opener=opener)
    if code == 200 and isinstance(u, dict) and u.get("source") == "cloud_gemini_direct":
        n = u.get("completed")
        answer["gemini_completed_today"] = n if type(n) is int and 0 <= n < 1000000 else None
        rows = u.get("models")
        if isinstance(rows,list) and len(rows) <= 12:
            answer["gemini_models_with_replies_today"] = sum(
                type(item.get("completed")) is int and 0 < item["completed"] < 1000000
                for item in rows if isinstance(item,dict))
    code, c, err = safe_request(HUD_ORIGIN, ROUTES[3], reader, opener=opener)
    if code == 200 and isinstance(c, dict) and isinstance(c.get("models"), list):
        answer["cloudflare_ai"] = "models_advertised" if c["models"] else "no_models_advertised"
    else:
        answer["cloudflare_ai"] = "unavailable_" + (err or "invalid_source")
    code, o, err = safe_request(HUD_ORIGIN, ROUTES[4], reader, opener=opener)
    if code == 200 and isinstance(o, dict):
        answer["omniroute_mac_optional"] = "online" if o.get("online") is True else "offline_or_stale"
    else:
        answer["omniroute_mac_optional"] = "unavailable_" + (err or "invalid_source")
    return answer


def summarize_workforce(token: str, opener=None) -> dict:
    result = {"service": "not_checked", "nine_provider_records": False,
              "configured_provider_count": None, "verified_online_providers": None,
              "owner_stop": "unknown", "eligible_providers": None,
              "queue_pending": None, "pending_reviews": None,
              "last_scheduled_shift": "unknown", "native_schedule_verified": False,
              "actual_recent_model_attempts": None, "provider_readiness": [],
              "reported_employee_roles": None, "recent_review_ready_attempts": None}
    if not credential(token):
        result["service"] = "blocked_service_secret_missing"
        return result
    code, data, error = safe_request(SITE_ORIGIN, GHOST_ROUTE, token, method="POST",
                                     document={"operation": "status"}, opener=opener)
    if code != 200 or not isinstance(data, dict) or data.get("execution_source") != "cloud_provider":
        result["service"] = SERVICE_DENIED.get(str(code), "unavailable_" + (error or "invalid_source"))
        return result
    result["service"] = "reachable"
    providers = data.get("providers")
    if isinstance(providers, list):
        names = [p.get("provider") for p in providers if isinstance(p, dict)]
        expected = len(names) == len(PROVIDERS) and set(names) == PROVIDERS
        result["nine_provider_records"] = expected
        if expected:
            result["configured_provider_count"] = sum(p.get("credentials_configured") is True for p in providers)
            result["verified_online_providers"] = sum(p.get("online_verified") is True for p in providers)
            result["eligible_providers"] = sum(p.get("admission") == "eligible" for p in providers)
            result["provider_readiness"] = provider_readiness(providers)
    result["owner_stop"] = "dispatch_enabled" if data.get("enabled") is True else (
        "dispatch_paused" if data.get("enabled") is False else "unknown")
    pending = data.get("queue_pending")
    if type(pending) is int and 0 <= pending <= 1000000:
        result["queue_pending"] = pending
    reviews = data.get("review_queue")
    if isinstance(reviews, dict):
        n = reviews.get("pending_count")
        if type(n) is int and 0 <= n <= 1000000:
            result["pending_reviews"] = n
    scheduled = data.get("scheduled_shifts")
    if isinstance(scheduled, dict):
        rows = scheduled.get("runs")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            state = rows[0].get("status")
            if state in {"stopped", "idle", "dispatched", "failed", "running"}:
                result["last_scheduled_shift"] = state
    result["native_schedule_verified"] = data.get("native_clock_verified") is True
    employees = data.get("employees")
    if isinstance(employees, list):
        names = {e.get("name") for e in employees if isinstance(e, dict) and
                 e.get("name") in {"Walter","Mike","Jane","Jesse","Gale","Gus","Saul","Hank"}}
        result["reported_employee_roles"] = len(names)
    attempts = data.get("attempts")
    if isinstance(attempts, list):
        result["actual_recent_model_attempts"] = sum(
            a.get("status") in ("needs_review", "succeeded", "failed", "completed")
            for a in attempts if isinstance(a, dict)
        )
        result["recent_review_ready_attempts"] = sum(
            a.get("status") == "needs_review" and a.get("human_review") == "not_recorded"
            for a in attempts if isinstance(a, dict)
        )
    return result


def build_report(env: dict, opener=None) -> dict:
    mode = env.get("ROVOR_CONTROL_MODE", "audit_only")
    if mode not in ("audit_only", "deploy_existing_hud", "deploy_and_test_gemini"):
        raise ValueError("unknown_mode")
    confirmed = env.get("ROVOR_OWNER_CONFIRMS_FREE_TIER", "false") == "true"
    flags = deployment_secrets(env)
    return {
        "schema_version": 1,
        "report_type": "ROVOR_cloud_only_operations_readback",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": mode,
        "mac_required": False,
        "credentials_present": flags,
        "deploy_ready": can_deploy(flags, mode, confirmed),
        "missing_deployment_prerequisites": sorted(k for k, v in flags.items() if not v and (
            k not in ("private_site_service_token", "google_free_project_key") or
            (k == "google_free_project_key" and mode == "deploy_and_test_gemini")
        )),
        "owner_confirmed_free_tier": confirmed,
        "hud": summarize_hud(env.get("ROVOR_HUD_READER_TOKEN", ""), opener=opener),
        "workforce": summarize_workforce(env.get("ROVOR_GHOST_SERVICE_TOKEN", ""), opener=opener),
    }


def summary(report: dict) -> str:
    flags, hud, workers = report["credentials_present"], report["hud"], report["workforce"]
    missing = report["missing_deployment_prerequisites"]
    lines = [
        "## ROVOR cloud-only control center",
        "",
        "This **report** is read-only. Deployment, one Gemini canary, and one guarded shift are separate explicit owner choices; configuration ≠ admission ≠ inference ≠ approved work.",
        "",
        "| Check | Verified observation |",
        "|---|---|",
        f"| Mac as dependency | **No** |",
        f"| Existing HUD private auth | {hud['private']} |",
        f"| Existing Cloudflare HUD | {hud['status']} |",
        f"| Google Gemini cloud chat | {hud['gemini_cloud']} |",
        f"| Google Free-tier text models listed by key (not inference proof) | {hud['gemini_free_text_models_listed'] if hud['gemini_free_text_models_listed'] is not None else 'unknown'} |",
        f"| Gemini models with D1-confirmed replies today | {hud['gemini_models_with_replies_today'] if hud['gemini_models_with_replies_today'] is not None else 'unknown'} |",
        f"| Gemini completed responses today (cloud D1 only) | {hud['gemini_completed_today'] if hud['gemini_completed_today'] is not None else 'unknown'} |",
        f"| Cloudflare AI | {hud['cloudflare_ai']} |",
        f"| Mac OmniRoute (optional only) | {hud['omniroute_mac_optional']} |",
        f"| Mac usage reporter (optional only) | {hud['mac_telemetry_optional']} |",
        f"| Private Site workforce service | {workers['service']} |",
        f"| Nine provider records in cloud | {workers['nine_provider_records']} |",
        f"| Provider credentials configured | {workers['configured_provider_count'] if workers['configured_provider_count'] is not None else 'unknown'} / 9 |",
        f"| Verified online providers | {workers['verified_online_providers'] if workers['verified_online_providers'] is not None else 'unknown'} / 9 |",
        f"| Currently eligible cloud providers | {workers['eligible_providers'] if workers['eligible_providers'] is not None else 'unknown'} / 9 |",
        f"| STOP / execution | {workers['owner_stop']} |",
        f"| Queue pending | {workers['queue_pending'] if workers['queue_pending'] is not None else 'unknown'} |",
        f"| Pending PASS/FAIL reviews | {workers['pending_reviews'] if workers['pending_reviews'] is not None else 'unknown'} |",
        f"| Last scheduled shift | {workers['last_scheduled_shift']} |",
        f"| Native schedule independently verified | {workers['native_schedule_verified']} |",
        f"| Employee roles observed (not online proof) | {workers['reported_employee_roles'] if workers['reported_employee_roles'] is not None else 'unknown'} / 8 |",
        f"| Recent unreviewed draft attempts (bounded sample) | {workers['recent_review_ready_attempts'] if workers['recent_review_ready_attempts'] is not None else 'unknown'} |",
        f"| Recent recorded attempts (bounded sample) | {workers['actual_recent_model_attempts'] if workers['actual_recent_model_attempts'] is not None else 'unknown'} |",
        "",
        "### Deployment readiness",
        f"- Mode requested: **{report['mode']}**.",
        f"- Required preflight: **{'READY' if report['deploy_ready'] else 'BLOCKED'}**.",
    ]
    if missing:
        lines.append("- Missing/invalid deployment configuration: " + ", ".join(missing) + ".")
    if workers.get("provider_readiness"):
        lines.extend([
            "",
            "### Nine-provider admission detail — original private Site only",
            "",
            "Catalog freshness, declared model IDs, and saved API keys are **not** cost, quota, canary or live inference proof.",
            "",
            "| Provider | Credentials | Catalog | Declared model | Admission gate | Online receipt |",
            "|---|---|---|---|---|---|",
        ])
        for route in workers["provider_readiness"]:
            lines.append(
                f"| {route['provider']} | {route['credentials']} | {route['catalog']} | "
                f"{route['model']} | {route['admission']} | {route['online']} |"
            )
    if report["mode"] == "deploy_and_test_gemini" and not report["owner_confirmed_free_tier"]:
        lines.append("- Owner confirmation required: this Google API key is for the Free-tier project.")
    if not flags["google_free_project_key"]:
        lines.append("- Google cloud key is absent from this GitHub Actions environment. Configure ROVOR_GEMINI_API_KEY in rovor-hud-production (value never in GitHub source or chat).")
    if not flags["private_site_service_token"]:
        lines.append("- Existing private Site service secret is absent from Actions; cloud workforce status is not verifiable from this workflow.")
    lines += [
        "",
        "**Not established:** remaining real provider quotas, $0 billing entitlements, genuine 24/7 inference, model capability quality, or human approval merely from this report.",
        "Cloud workforce uses the **existing private Site**; this action must never overwrite its database, registrations, reviews or STOP.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report(dict(os.environ))
    output = os.getenv("ROVOR_REPORT_OUTPUT", "")
    if output:
        Path(output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    github_output = os.getenv("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as out:
            out.write("deploy_ready=" + str(report["deploy_ready"]).lower() + "\n")
            site = report["workforce"]
            out.write("site_accessible=" + str(site["service"] == "reachable").lower() + "\n")
            # An owner-requested cloud shift must never fire when STOP is active
            # or the provider fleet has no current verified eligibility.
            shift_ready = (site["service"] == "reachable" and site["owner_stop"] == "dispatch_enabled"
                           and isinstance(site["eligible_providers"], int) and site["eligible_providers"] > 0)
            out.write("shift_ready=" + str(shift_ready).lower() + "\n")
            out.write("gemini_cloud_online=" + str(report["hud"]["gemini_cloud"] == "key_listed_free_text_models").lower() + "\n")
    markdown = summary(report)
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as out:
            out.write(markdown)
    # Never print the full response from either authenticated cloud.
    print(json.dumps({
        "state": "read_only_complete",
        "mode": report["mode"],
        "deploy_ready": report["deploy_ready"],
        "hud_status": report["hud"]["status"],
        "gemini_cloud": report["hud"]["gemini_cloud"],
        "cloud_workforce": report["workforce"]["service"],
        "nine_provider_records": report["workforce"]["nine_provider_records"],
        "mac_required": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ValueError as error:
        print("ROVOR control report refused: " + (
            str(error) if str(error) in ("unknown_mode", "unapproved_status_target") else "invalid_input"
        ), file=sys.stderr)
        sys.exit(2)
