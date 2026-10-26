#!/usr/bin/env python3
"""Check exact single-model OmniRoute combos for an atomic fleet reservation.

No CLI/subprocess, model call or mutation here. The existing worker must
re-read the installed catalog at the moment of dispatch and verify again.
Multi-model priority/fallback combos CANNOT prove chosen-model routing.
"""
import re
import time
import math

NAME = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{2,159}$")
PROVIDER = re.compile(r"^[a-z0-9_-]{2,50}$")



def zero_cost_witness(slot, model_id, provider_id, pool_id, *, now=None):
    """Accept non-:free model IDs only with fresh *trusted-host* entitlement.

    This does not authenticate a supplied dict. The caller is the trusted
    Mac evidence callback, after quota checks inside SQLite BEGIN IMMEDIATE.
    A model-catalog entry, API key, or manually edited JSON is NEVER proof.
    No billing secrets or model response data are copied into the witness.
    """
    now = time.time() if now is None else now
    if (type(now) not in (int, float) or not math.isfinite(now)
            or not 0 <= now < 1e15
            or type(model_id) is not str or not MODEL.fullmatch(model_id)
            or type(provider_id) is not str or not PROVIDER.fullmatch(provider_id)
            or not model_id.startswith(provider_id + '/')
            or type(pool_id) is not str or not NAME.fullmatch(pool_id)
            or not isinstance(slot, dict)
            or slot.get('model_id') != model_id
            or slot.get('quota_pool_id') != pool_id):
        raise ValueError('direct_model_entitlement_identity_unverified')
    required = ('account_free_verified', 'quota_verified',
                'approved_model_id', 'completed_canary_verified',
                'privacy_approved', 'terms_approved',
                'commercial_use_permitted', 'no_billable_fallback_verified')
    if (any(slot.get(field) is not True for field in required)
            or type(slot.get('cost_per_request_usd')) not in (int, float)
            or not math.isfinite(slot['cost_per_request_usd'])
            or slot['cost_per_request_usd'] != 0):
        raise ValueError('direct_model_zero_cost_or_terms_unverified')
    for key in ('verified_at', 'pool_verified_at'):
        value = slot.get(key)
        if (type(value) not in (int, float) or not math.isfinite(value)
                or value < 0 or value > now + 30 or now - value > 900):
            raise ValueError('direct_model_account_evidence_stale')
    return {key: slot[key] for key in
            ('model_id', 'quota_pool_id', 'verified_at', 'pool_verified_at',
             'cost_per_request_usd', *required)}


def verify_binding(model_id, approved_routes, catalog, *,
                   verified_slot=None, pool_id=None, now=None):
    if (type(model_id) is not str or not MODEL.fullmatch(model_id)
            ):
        raise ValueError("selected_model_not_exact_approved_free_route")
    if (not isinstance(approved_routes, dict)
            or len(approved_routes) > 32
            or not isinstance(catalog, (list, tuple))):
        raise ValueError("route_catalog_not_verified")
    configured = approved_routes.get(model_id)
    if (not isinstance(configured, dict)
            or set(configured) != {"combo", "provider_id"}
            or type(configured["combo"]) is not str
            or not NAME.fullmatch(configured["combo"])
            or type(configured["provider_id"]) is not str
            or not PROVIDER.fullmatch(configured["provider_id"])):
        raise ValueError("selected_model_binding_unapproved")
    matching = [c for c in catalog if isinstance(c, dict)
                and c.get("name") == configured["combo"]]
    if len(matching) != 1:
        raise ValueError("selected_single_model_combo_missing_or_duplicated")
    c = matching[0]
    if (c.get("strategy") != "priority" or c.get("isHidden") is not False
            or not isinstance(c.get("models"), list)
            or len(c["models"]) != 1):
        raise ValueError("selected_route_has_unapproved_fallback")
    x = c["models"][0]
    if (not isinstance(x, dict) or x.get("kind") != "model"
            or x.get("providerId") != configured["provider_id"]
            or x.get("model") != model_id):
        raise ValueError("selected_route_model_or_provider_drift")
    # Existing :free routes preserve the previously approved behavior.
    # Most independent providers do not suffix free-plan models with :free,
    # and a suffix by itself never substitutes for the capacity checks in
    # omniroute_model_reservation.reserve().
    if not model_id.endswith(':free'):
        zero_cost_witness(verified_slot, model_id, configured['provider_id'],
                          pool_id, now=now)
    return configured["combo"]


def verify_before_completion(selected, installed_catalog, *, now=None):
    if (not isinstance(selected, dict)
            or not {"model_id", "pool_id", "combo", "provider_id"}.issubset(selected)
            or set(selected) - {"model_id", "pool_id", "combo", "provider_id",
                                "zero_cost_witness"}
            or type(selected["combo"]) is not str
            or type(selected["provider_id"]) is not str
            or not PROVIDER.fullmatch(selected["provider_id"])):
        raise ValueError("no_verified_atomic_model_binding")
    # Re-read live Combo catalog and verify that a single-model route still
    # targets this exact model immediately before any network POST.
    matching = [c for c in installed_catalog if isinstance(c, dict)
                and c.get("name") == selected["combo"]]
    if len(matching) != 1:
        raise ValueError("selected_route_unavailable_on_host")
    c = matching[0]
    if (c.get("strategy") != "priority" or c.get("isHidden") is not False
            or not isinstance(c.get("models"), list)
            or len(c["models"]) != 1):
        raise ValueError("selected_route_changed_to_multi_model")
    x = c["models"][0]
    if (not isinstance(x, dict) or x.get("kind") != "model"
            or not isinstance(x.get("providerId"), str)
            or x["providerId"] != selected["provider_id"]
            or not PROVIDER.fullmatch(x["providerId"])
            or x.get("model") != selected["model_id"]):
        raise ValueError("selected_model_changed_before_completion")
    if not selected['model_id'].endswith(':free'):
        zero_cost_witness(selected.get('zero_cost_witness'),
                          selected['model_id'], selected['provider_id'],
                          selected['pool_id'], now=now)
    return selected["combo"]
