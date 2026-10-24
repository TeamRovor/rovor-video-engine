#!/usr/bin/env python3
"""Check exact single-model OmniRoute combos for an atomic fleet reservation.

No CLI/subprocess, model call or mutation here. The existing worker must
re-read the installed catalog at the moment of dispatch and verify again.
Multi-model priority/fallback combos CANNOT prove chosen-model routing.
"""
import re

NAME = re.compile(r"^[a-z][a-z0-9_-]{2,79}$")
MODEL = re.compile(r"^[a-z0-9][a-z0-9._:/-]{2,159}$")
PROVIDER = re.compile(r"^[a-z0-9_-]{2,50}$")


def verify_binding(model_id, approved_routes, catalog):
    if (type(model_id) is not str or not MODEL.fullmatch(model_id)
            or not model_id.endswith(":free")):
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
    return configured["combo"]


def verify_before_completion(selected, installed_catalog):
    if (not isinstance(selected, dict)
            or set(selected) != {"model_id", "pool_id", "combo", "provider_id"}
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
            or x.get("model") != selected["model_id"]
            or not str(x.get("model", "")).endswith(":free")):
        raise ValueError("selected_model_changed_before_completion")
    return selected["combo"]
