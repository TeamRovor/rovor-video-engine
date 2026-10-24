#!/usr/bin/env python3
"""Offline permit preflight for ROVOR's EXISTING OmniRoute research worker.

This module never opens a network connection, reads credentials, enqueues work,
reserves quota, calls a model, or controls a Mac. It composes the existing
reasoning-admission guard with a strict snapshot of the installed combo,
provider/account attestations, and the authoritative SQLite ledger.

IMPORTANT: attestations and ledger facts MUST come from trusted, fresh host
reads. A caller-supplied JSON dictionary is not cryptographic proof of billing
or provider entitlement. This is a fail-closed validation layer, not an
authorization to spend, a replacement queue, or a concurrency lock.
"""
from datetime import datetime, timezone
import re

from omniroute_reasoning_admission import prepare_request

MAX_EVIDENCE_AGE_SECONDS = 900
MAX_CLOCK_SKEW_SECONDS = 30
MAX_ROLLING_CLAIMS = 5
KEY = re.compile(r"^[a-z0-9][a-z0-9_-]{2,90}$")


class PermitError(ValueError):
    """Fixed error codes only; never include provider, prompt, or private text."""


def _reject(code):
    raise PermitError(code)


def _utc_time(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        _reject("clock_unverified")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        _reject("clock_unverified")


def _evidence_time(value):
    if type(value) is not str or not 15 <= len(value) <= 64:
        _reject("evidence_timestamp_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _reject("evidence_timestamp_invalid")
    if parsed.tzinfo is None:
        _reject("evidence_timestamp_invalid")
    return parsed.astimezone(timezone.utc)


def _verified_combo(route, members, catalog):
    """Bind the expected allowlisted fallback order to one installed combo."""
    if (type(route) is not str or not route.startswith("rovor-")
            or not isinstance(members, (tuple, list))
            or not 1 <= len(members) <= 5
            or any(type(x) is not str for x in members)
            or len(set(members)) != len(members)):
        _reject("invalid_route_identity")
    if not isinstance(catalog, list):
        _reject("combo_catalog_unverified")
    matches = [c for c in catalog if isinstance(c, dict) and c.get("name") == route]
    if len(matches) != 1:
        _reject("combo_missing_or_ambiguous")
    combo = matches[0]
    if combo.get("strategy") != "priority" or combo.get("isHidden") is not False:
        _reject("combo_policy_changed")
    entries = combo.get("models")
    if not isinstance(entries, list) or len(entries) != len(members):
        _reject("combo_members_changed")
    actual = []
    for entry in entries:
        if (not isinstance(entry, dict) or entry.get("kind") != "model"
                or entry.get("providerId") != "openrouter"
                or type(entry.get("model")) is not str
                or not entry["model"].endswith(":free")):
            _reject("combo_nonfree_fallback")
        actual.append(entry["model"])
    if tuple(actual) != tuple(members):
        _reject("combo_members_changed")


def _fresh_capabilities(members, attestations, now):
    """Verify exact fresh $0 account eligibility, quotas and reasoning support.

    Only a trusted host caller may supply these attestations. Suffix ':free'
    alone does not prove billing eligibility; unknown price/fees fail closed.
    """
    if (not isinstance(attestations, dict)
            or set(attestations) != set(members)):
        _reject("provider_evidence_incomplete")
    capabilities = {}
    for model in members:
        row = attestations[model]
        if not isinstance(row, dict) or row.get("model_id") != model:
            _reject("provider_model_mismatch")
        if (row.get("account_free_entitlement_verified") is not True
                or row.get("provider_quota_verified") is not True
                or row.get("public_research_privacy_approved") is not True):
            _reject("provider_eligibility_unverified")
        for key in ("cost_per_request_usd", "cost_per_million_input_usd",
                    "cost_per_million_output_usd", "other_fees_usd"):
            cost = row.get(key)
            if type(cost) not in (int, float) or cost != 0:
                _reject("zero_cost_unverified")
        quota = row.get("remaining_requests")
        if type(quota) is not int or quota < 1:
            _reject("provider_quota_exhausted")
        seen = _evidence_time(row.get("verified_at"))
        age = (now - seen).total_seconds()
        if age < -MAX_CLOCK_SKEW_SECONDS or age > MAX_EVIDENCE_AGE_SECONDS:
            _reject("provider_evidence_stale_or_future")
        reasoning = row.get("reasoning")
        if not isinstance(reasoning, dict):
            _reject("reasoning_capabilities_unverified")
        # The downstream reasoning admission guard checks mandatory and none.
        capabilities[model] = {"id": model, "reasoning": dict(reasoning)}
    return capabilities


def build_candidate_request(route, members, catalog, attestations, messages, *,
                            now, stop_present=True, owner_opt_in=False,
                            public_sources_verified=False,
                            authoritative_ledger=False, dedupe_key=None,
                            seen_dedupe=None, rolling_claims=None,
                            other_job_running=True):
    """Return an inert request candidate, never dispatch or reserve anything.

    The existing SQLite worker MUST atomically recheck STOP, dedupe and quota
    when it claims the job; a preflight snapshot alone is race-prone.
    Existing model-use approval and human review still apply independently.
    """
    if stop_present is not False:
        _reject("stop_or_unknown")
    if owner_opt_in is not True:
        _reject("model_use_not_authorized")
    if public_sources_verified is not True:
        _reject("private_or_unverified_source")
    if (authoritative_ledger is not True or other_job_running is not False
            or type(rolling_claims) is not int
            or not 0 <= rolling_claims < MAX_ROLLING_CLAIMS
            or not isinstance(seen_dedupe, (set, frozenset))
            or any(type(item) is not str for item in seen_dedupe)
            or type(dedupe_key) is not str or not KEY.fullmatch(dedupe_key)):
        _reject("ledger_or_budget_unverified")
    if dedupe_key in seen_dedupe:
        _reject("previous_attempt_no_replay")
    instant = _utc_time(now)
    _verified_combo(route, members, catalog)
    capabilities = _fresh_capabilities(members, attestations, instant)
    request = prepare_request(route, members, capabilities, messages,
                              route_verified_free=True)
    return {
        "status": "eligible_candidate_only",
        "request": request,
        "checked_model_count": len(members),
        "automatic_dispatch_authorized": False,
        "requires_atomic_sqlite_claim": True,
        "requires_private_receipt_review": True,
    }
