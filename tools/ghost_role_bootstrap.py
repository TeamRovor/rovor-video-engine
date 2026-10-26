#!/usr/bin/env python3
"""ROVOR role learning proposals: offline, no model, no queue, no Mac actions."""
import argparse
import json
import re
from pathlib import Path

_ID = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_STATUS = {"queued", "running", "needs_review", "failed", "rejected", "approved"}
_PUBLIC = {"AGENTS.md", "WORK.md", "ROVOR-AI-PLAN.md"}


def validate(doc):
    if not isinstance(doc, dict) or doc.get("schema_version") != 1 or doc.get("release") != "role-bootstrap-v1":
        raise ValueError("Unsupported manifest")
    p = doc.get("policy", {})
    if not isinstance(p, dict) or p.get("mode") != "review_only" or any(
            p.get(k) is not False for k in ("external_effects", "paid_fallback", "native_app_control")):
        raise ValueError("Unsafe research policy")
    if type(p.get("max_output_chars")) is not int or not 100 <= p["max_output_chars"] <= 8000:
        raise ValueError("Invalid output bound")
    sources = doc.get("sources")
    if not isinstance(sources, list) or not sources or len(set(sources)) != len(sources) or not set(sources) <= _PUBLIC:
        raise ValueError("Untrusted source path")
    for key, minimum, maximum, required in (
            ("roles", 1, 12, {"id", "job", "mission"}),
            ("steps", 1, 8, {"id", "instruction"})):
        items = doc.get(key)
        if not isinstance(items, list) or not minimum <= len(items) <= maximum:
            raise ValueError("Unbounded catalog")
        seen = set()
        for item in items:
            if not isinstance(item, dict) or set(item) != required:
                raise ValueError("Invalid record")
            ident = item["id"]
            if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in seen:
                raise ValueError("Duplicate/invalid ID")
            seen.add(ident)
            for value in item.values():
                if not isinstance(value, str) or not 2 <= len(value) <= 500:
                    raise ValueError("Invalid record text")
    return True


def key(role_id, stage_id):
    if not _ID.fullmatch(role_id) or not _ID.fullmatch(stage_id):
        raise ValueError("Invalid key")
    return "rovor-role-" + role_id + "-" + stage_id + "-v1"


def next_step(doc, receipts, role_id, stop=False):
    """Approved receipts only advance. All previous attempts block replay."""
    validate(doc)
    if type(stop) is not bool or not isinstance(receipts, dict):
        raise ValueError("Invalid state")
    roles = {r["id"]: r for r in doc["roles"]}
    if role_id not in roles:
        raise ValueError("Unknown role")
    known = {key(r["id"], s["id"]) for r in doc["roles"] for s in doc["steps"]}
    if any(k not in known or v not in _STATUS for k, v in receipts.items()):
        raise ValueError("Invalid receipt")
    if stop:
        return {"status": "stopped", "role_id": role_id}
    for stage in doc["steps"]:
        stable = key(role_id, stage["id"])
        prior = receipts.get(stable)
        if prior == "approved":
            continue
        if prior:
            return {"status": "waiting_" + prior, "role_id": role_id, "dedupe_key": stable, "no_retry": True}
        return {"status": "proposed", "role_id": role_id, "dedupe_key": stable,
                "stage": stage["id"], "job": roles[role_id]["job"],
                "mission": roles[role_id]["mission"], "instruction": stage["instruction"],
                "sources": doc["sources"], "review_required": True,
                "output_mode": "review_only", "external_effects": False}
    return {"status": "complete_await_reviewed_release", "role_id": role_id}


def ready(doc, receipts, stop=False, limit=1):
    validate(doc)
    if type(limit) is not int or not 1 <= limit <= 5:
        raise ValueError("Unbounded release")
    if stop:
        return []
    proposals = []
    for role in doc["roles"]:
        item = next_step(doc, receipts, role["id"])
        if item["status"] == "proposed":
            proposals.append(item)
        if len(proposals) >= limit:
            break
    return proposals


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--role")
    p.add_argument("--manifest", type=Path,
                   default=Path(__file__).resolve().parents[1] / "coordination/ghost-role-bootstrap.json")
    a = p.parse_args()
    doc = json.loads(a.manifest.read_text(encoding="utf-8"))
    result = next_step(doc, {}, a.role) if a.role else ready(doc, {})
    print(json.dumps({"mode": "offline_no_enqueue_no_model", "result": result}, indent=2))


if __name__ == "__main__":
    main()
