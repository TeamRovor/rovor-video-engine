#!/usr/bin/env python3
"""Fail-closed capacity-aware selection for existing OmniRoute Mac workers.

Pure decision logic: no network, no inference, no queue, no tokens, no sleep,
no scheduler, no credential access. The *existing* atomic SQLite worker must
reserve quota, claims and STOP under its lock before any model invocation.
The caller must pass current, trusted host/provider attestations, not guesses.
"""
import math
import re

MODEL_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{2,159}$")
TASK_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,99}$")
SKILL = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
MAX_EVIDENCE_AGE = 900
INPUT_HEADROOM = 0.80
OUTPUT_HEADROOM = 0.80
MAX_MODELS = 32
MAX_INFLIGHT_PER_MODEL = 8


class AdmissionError(ValueError):
    """Fixed error codes only; never provider-supplied error messages."""


def _fail(code):
    raise AdmissionError(code)


def _int(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def _number(value, minimum, maximum):
    return type(value) in (int, float) and math.isfinite(value) and minimum <= value <= maximum


def _skills(value):
    return (isinstance(value, (list, tuple)) and len(value) <= 16
            and all(type(s) is str and SKILL.fullmatch(s) for s in value)
            and len(set(value)) == len(value))


def _task(spec):
    if not isinstance(spec, dict):
        _fail("task_invalid")
    if (type(spec.get("id")) is not str or not TASK_ID.fullmatch(spec["id"])
            or spec.get("public_only") is not True
            or not _int(spec.get("minimum_tier"), 1, 3)
            or not _int(spec.get("estimated_input_tokens"), 1, 200000)
            or not _int(spec.get("requested_output_tokens"), 1, 32000)
            or not _skills(spec.get("required_skills"))
            or not spec["required_skills"]):
        _fail("task_invalid_or_not_public")
    return dict(spec)


def _slot(slot, now):
    if not isinstance(slot, dict):
        _fail("slot_invalid")
    ident = slot.get("model_id")
    if type(ident) is not str or not MODEL_ID.fullmatch(ident):
        _fail("model_identity_invalid")
    fields = (("tier", 1, 3), ("max_input_tokens", 256, 1000000),
              ("max_output_tokens", 128, 128000),
              ("max_inflight", 1, MAX_INFLIGHT_PER_MODEL),
              ("inflight", 0, MAX_INFLIGHT_PER_MODEL),
              ("remaining_requests", 0, 10000000),
              ("latency_ms", 1, 600000),
              ("claims_since_reset", 0, 10000000))
    if any(not _int(slot.get(k), low, high) for k, low, high in fields):
        _fail("slot_capacity_invalid")
    if slot["inflight"] > slot["max_inflight"]:
        _fail("slot_capacity_invalid")
    if not _skills(slot.get("skills")):
        _fail("slot_skills_invalid")
    if slot.get("health") not in ("ready", "degraded", "down"):
        _fail("slot_health_invalid")
    if not _number(slot.get("success_fraction"), 0, 1):
        _fail("slot_quality_invalid")
    if not _number(slot.get("verified_at"), 0, now + 30):
        _fail("slot_evidence_time_invalid")
    for k in ("quota_reset_at", "cooldown_until"):
        if slot.get(k) is not None and not _number(slot[k], 0, 1e15):
            _fail("slot_reset_invalid")
    if any(type(slot.get(k)) is not bool for k in
           ("account_free_verified", "privacy_approved", "terms_approved",
            "quota_verified", "approved_model_id", "completed_canary_verified")):
        _fail("slot_attestation_invalid")
    if not _number(slot.get("cost_per_request_usd"), 0, 1000000):
        _fail("slot_cost_invalid")
    return slot


def decide(task, slots, *, now, stop_requested=False, failure_circuit_open=False):
    """Pick the smallest capable, healthy and *currently verified* free model.

    Models at quota, cooling down or fully occupied are not implicitly retried.
    At their reset time they need new trusted quota evidence; the function
    never pretends that the allowance was actually restored. Full models
    become eligible only when the existing queue reports released capacity.
    Return is inert: it cannot authorize a real POST or quota reservation.
    """
    if (not _number(now, 0, 1e15)
            or type(stop_requested) is not bool
            or type(failure_circuit_open) is not bool):
        _fail("dispatch_clock_or_guards_invalid")
    work = _task(task)
    if not isinstance(slots, (list, tuple)) or len(slots) > MAX_MODELS:
        _fail("model_catalog_invalid")
    seen = set()
    inventory = []
    for original in slots:
        model = _slot(original, now)
        if model["model_id"] in seen:
            _fail("duplicate_model_resource")
        seen.add(model["model_id"])
        inventory.append(model)

    base = {
        "status": "blocked", "reason": "no_eligible_model",
        "chosen_model_id": None, "task_id": work["id"],
        "model_resource_count": len(inventory),
        "allowed_inference_posts": 0, "authorized_to_claim": False,
        "next_reevaluate_at": None, "requires_fresh_quota_snapshot": True,
        "current_model_health": {},
    }
    if stop_requested:
        return dict(base, reason="stop_requested")
    if failure_circuit_open:
        return dict(base, reason="global_failure_circuit_open")

    eligible = []
    adequate = 0
    waiting = []
    for model in inventory:
        ident = model["model_id"]
        if (model["tier"] < work["minimum_tier"]
                or not set(work["required_skills"]).issubset(model["skills"])
                or work["estimated_input_tokens"] > int(model["max_input_tokens"] * INPUT_HEADROOM)
                or work["requested_output_tokens"] > int(model["max_output_tokens"] * OUTPUT_HEADROOM)):
            base["current_model_health"][ident] = "task_exceeds_verified_capability"
            continue
        adequate += 1
        # Only host-attested resources may ever become candidates; zero suffix
        # and advertised catalog membership do not prove billing entitlement.
        if (model["approved_model_id"] is not True
                or model["account_free_verified"] is not True
                or model["privacy_approved"] is not True
                or model["terms_approved"] is not True
                or model["quota_verified"] is not True
                or model["completed_canary_verified"] is not True
                or model["cost_per_request_usd"] != 0
                or now - model["verified_at"] > MAX_EVIDENCE_AGE):
            base["current_model_health"][ident] = "not_verified_zero_cost_and_usable"
            continue
        if model["health"] != "ready":
            base["current_model_health"][ident] = "provider_not_ready"
            continue
        if model["remaining_requests"] == 0:
            base["current_model_health"][ident] = "provider_quota_exhausted"
            if model["quota_reset_at"] is not None and model["quota_reset_at"] > now:
                waiting.append(model["quota_reset_at"])
            continue
        if model["cooldown_until"] is not None and model["cooldown_until"] > now:
            base["current_model_health"][ident] = "cooldown"
            waiting.append(model["cooldown_until"])
            continue
        if model["inflight"] >= model["max_inflight"]:
            base["current_model_health"][ident] = "concurrency_full"
            continue
        base["current_model_health"][ident] = "candidate_verified_not_reserved"
        # Proportional tier fit comes first: don't waste scarce deep models
        # on basic work. Then prefer reliability, less congestion and latency.
        # This is a suggestion only, not an admission bypass.
        tier_surplus = model["tier"] - work["minimum_tier"]
        utilization = model["inflight"] / model["max_inflight"]
        score = (tier_surplus, -model["success_fraction"], utilization,
                 model["latency_ms"], model["claims_since_reset"], ident)
        eligible.append((score, ident))
    if eligible:
        chosen = min(eligible)[1]
        return dict(base, status="candidate_only", reason="smallest_verified_capable",
                    chosen_model_id=chosen, next_reevaluate_at=now,
                    allowed_inference_posts=0, authorized_to_claim=False)
    if adequate == 0:
        return dict(base, status="needs_task_split_or_more_capable_model",
                    reason="task_exceeds_all_model_capabilities")
    if waiting:
        return dict(base, status="wait_for_fresh_capacity",
                    reason="capacity_or_quota_temporarily_unavailable",
                    next_reevaluate_at=min(waiting))
    return dict(base, reason="no_currently_verified_and_available_model")
