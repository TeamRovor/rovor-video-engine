#!/usr/bin/env python3
"""Stdlib-only structural validator for ROVOR portable work packet v1."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EFFECTS = {"read_public_source", "write_repository_branch", "run_hosted_tests",
           "modify_local_project", "contact_external", "spend_money", "publish", "deploy"}
CAPABILITIES = {"client_intake", "sourced_sales", "ci_triage", "software_delivery",
                "video_production", "research"}
SOURCE_STATES = {"verified", "unverified", "unavailable"}
TECHNICAL = {"not_run", "running", "passed", "failed", "unknown", "blocked"}
ACCEPTANCE = {"not_run", "running", "pass", "fail", "unknown", "blocked"}
APPROVAL = {"draft", "pending_review", "approved", "rejected", "published", "delivered"}
FORBIDDEN_KEYS = {"cmd", "shell", "script", "argv", "exec_payload", "executable_payload"}
SHA = re.compile(r"^[a-fA-F0-9]{64}$")
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{1,119}$")
PACKET_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,79}$")


def issue(out, code, path, message):
    out.append({"code": code, "path": path, "message": message})


def forbidden(value, path="$"):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in FORBIDDEN_KEYS:
                found.append((path + "." + key, key))
            found.extend(forbidden(child, path + "." + str(key)))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(forbidden(child, path + "[" + str(i) + "]"))
    return found


def nonblank(value):
    return isinstance(value, str) and bool(value.strip())


def valid_hash(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def validate_packet(packet):
    out = []
    if not isinstance(packet, dict):
        return [{"code":"invalid_packet","path":"$","message":"Packet must be an object"}]
    for path, key in forbidden(packet):
        issue(out, "forbidden_payload", path, "Opaque executable payload fields are not permitted")
    required = {"schema_version","packet_id","capability","intent","source_refs","constraints",
                "acceptance","executor","authorization","technical_status","artifact_receipt","approval"}
    if set(packet) != required:
        issue(out, "top_level_keys", "$", "Packet must contain exactly the schema-v1 fields")
    if packet.get("schema_version") != 1:
        issue(out, "schema_version", "$.schema_version", "Only version 1 is supported")
    pid = packet.get("packet_id")
    if not isinstance(pid, str) or not PACKET_ID.fullmatch(pid):
        issue(out, "packet_id", "$.packet_id", "Invalid stable packet ID")
    if not isinstance(packet.get("capability"), str) or packet.get("capability") not in CAPABILITIES:
        issue(out, "capability", "$.capability", "Unsupported capability")
    if not nonblank(packet.get("intent")) or len(packet.get("intent","")) > 500:
        issue(out, "intent", "$.intent", "Intent must be a bounded non-empty string")

    sources = packet.get("source_refs")
    source_ids = set()
    if not isinstance(sources, list) or not sources:
        issue(out, "source_refs", "$.source_refs", "At least one source reference is required")
        sources = []
    for i, src in enumerate(sources):
        p = "$.source_refs[" + str(i) + "]"
        if not isinstance(src, dict):
            issue(out, "source_shape", p, "Source reference must be an object")
            continue
        if set(src) != {"id","uri","status","sha256"}:
            issue(out, "source_keys", p, "Source keys must be id, uri, status and sha256")
        sid = src.get("id")
        if not isinstance(sid, str) or not ID.fullmatch(sid):
            issue(out, "source_id", p, "Invalid source ID")
        elif sid in source_ids:
            issue(out, "duplicate_source", p, "Source IDs must be unique")
        else:
            source_ids.add(sid)
        if not nonblank(src.get("uri")) or len(src.get("uri","")) > 2048:
            issue(out, "source_uri", p, "Source URI must be a bounded non-empty string")
        state, digest = src.get("status"), src.get("sha256")
        if not isinstance(state, str) or state not in SOURCE_STATES:
            issue(out, "source_status", p, "Invalid source verification status")
        if digest is not None and not valid_hash(digest):
            issue(out, "source_hash", p, "SHA-256 must be 64 hex characters or null")
        if state == "verified" and not valid_hash(digest):
            issue(out, "verified_source_without_hash", p, "Verified sources require a SHA-256 hash")

    cons = packet.get("constraints")
    allowed, prohibited = set(), set()
    if not isinstance(cons, dict) or set(cons) != {"data_classification","allowed_effects","prohibited_effects"}:
        issue(out, "constraints_shape", "$.constraints", "Explicit classification and allowed/prohibited effects are required")
        cons = {}
    if cons.get("data_classification") not in {"public_only","synthetic","confidential","restricted"}:
        issue(out, "data_classification", "$.constraints", "Invalid data classification")
    for field, target in (("allowed_effects", allowed), ("prohibited_effects", prohibited)):
        vals = cons.get(field)
        if not isinstance(vals, list) or any(not isinstance(v,str) or v not in EFFECTS for v in vals):
            issue(out, "effects_shape", "$.constraints."+field, "Effects must be a list of known names")
        elif len(vals) != len(set(vals)):
            issue(out, "duplicate_effect", "$.constraints."+field, "Effect names must be unique")
        else:
            target.update(vals)
    if allowed & prohibited:
        issue(out, "effect_conflict", "$.constraints", "An effect cannot be both allowed and prohibited")

    receipt = packet.get("artifact_receipt")
    artifacts, artifact_ids, verified_artifacts = [], set(), set()
    artifact_states = {"not_created","reserved","produced","verified","failed","unknown"}
    if not isinstance(receipt, dict) or set(receipt) != {"state","artifacts"}:
        issue(out, "receipt_shape", "$.artifact_receipt", "Receipt requires state and artifacts")
        receipt = {}
    if not isinstance(receipt.get("state"), str) or receipt.get("state") not in artifact_states:
        issue(out, "receipt_state", "$.artifact_receipt", "Invalid artifact receipt state")
    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, list):
        issue(out, "artifact_list", "$.artifact_receipt.artifacts", "Artifacts must be a list")
        artifacts = []
    for i, a in enumerate(artifacts):
        p = "$.artifact_receipt.artifacts[" + str(i) + "]"
        if not isinstance(a, dict):
            issue(out, "artifact_shape", p, "Artifact must be an object")
            continue
        if set(a) != {"id","uri","status","sha256"}:
            issue(out, "artifact_keys", p, "Artifact keys must be id, uri, status and sha256")
        aid, uri, state, digest = a.get("id"), a.get("uri"), a.get("status"), a.get("sha256")
        if not isinstance(aid,str) or not ID.fullmatch(aid):
            issue(out, "artifact_id", p, "Invalid artifact ID")
        elif aid in artifact_ids:
            issue(out, "duplicate_artifact", p, "Artifact IDs must be unique")
        else:
            artifact_ids.add(aid)
        if not nonblank(uri):
            issue(out, "artifact_uri", p, "Artifact URI is required")
        if not isinstance(state,str) or state not in SOURCE_STATES:
            issue(out, "artifact_status", p, "Invalid artifact verification state")
        if digest is not None and not valid_hash(digest):
            issue(out, "artifact_hash", p, "SHA-256 must be 64 hex characters or null")
        if state == "verified":
            if not valid_hash(digest):
                issue(out, "verified_artifact_without_hash", p, "Verified artifact requires a hash")
            else:
                verified_artifacts.add(aid)
    if receipt.get("state") == "verified" and not verified_artifacts:
        issue(out, "receipt_without_verified_artifact", "$.artifact_receipt", "Verified receipt requires a verified hashed artifact")
    if receipt.get("state") == "not_created" and artifacts:
        issue(out, "unexpected_artifacts", "$.artifact_receipt", "Not-created receipt cannot list artifacts")

    criteria = packet.get("acceptance")
    if not isinstance(criteria,list) or not criteria:
        issue(out, "acceptance_shape", "$.acceptance", "At least one acceptance criterion is required")
        criteria = []
    criterion_ids = set()
    for i, c in enumerate(criteria):
        p = "$.acceptance[" + str(i) + "]"
        if not isinstance(c,dict):
            issue(out, "criterion_shape", p, "Criterion must be an object")
            continue
        if set(c) != {"id","statement","status","evidence_refs"}:
            issue(out, "criterion_keys", p, "Criterion keys must be id, statement, status and evidence_refs")
        cid, statement, state, refs = c.get("id"), c.get("statement"), c.get("status"), c.get("evidence_refs")
        if not isinstance(cid,str) or not re.fullmatch(r"^[a-z0-9][a-z0-9_-]{1,79}$",cid):
            issue(out, "criterion_id", p, "Invalid criterion ID")
        elif cid in criterion_ids:
            issue(out, "duplicate_criterion", p, "Criterion IDs must be unique")
        else:
            criterion_ids.add(cid)
        if not nonblank(statement) or len(statement) > 1000:
            issue(out, "criterion_statement", p, "Criterion statement must be bounded")
        if not isinstance(state,str) or state not in ACCEPTANCE:
            issue(out, "criterion_status", p, "Invalid acceptance status")
        if not isinstance(refs,list) or any(not isinstance(x,str) for x in refs):
            issue(out, "criterion_refs", p, "Evidence refs must be a list of IDs")
        elif len(refs) != len(set(refs)):
            issue(out, "duplicate_criterion_ref", p, "Evidence refs must be unique")
        elif any(x not in source_ids | artifact_ids for x in refs):
            issue(out, "unknown_evidence_ref", p, "Evidence refs must name a declared source or artifact")
        if state == "pass" and not refs:
            issue(out, "pass_without_evidence", p, "Passing criterion requires evidence")

    executor = packet.get("executor")
    if not isinstance(executor,dict) or set(executor) != {"kind","requires","mode"}:
        issue(out, "executor_shape", "$.executor", "Executor requires kind, requires and mode")
        executor = {}
    kinds = {"human","hosted_ci","local_runtime","remote_service"}
    modes = {"bounded_read_only","draft_only","authorized_write","visual_review"}
    requires = {"repository_read","repository_write","hosted_ci","local_runtime","original_assets","human_approval","browser"}
    if not isinstance(executor.get("kind"),str) or executor.get("kind") not in kinds:
        issue(out, "executor_kind", "$.executor.kind", "Invalid executor kind")
    reqs = executor.get("requires")
    if not isinstance(reqs,list) or any(not isinstance(x,str) or x not in requires for x in reqs):
        issue(out, "executor_requires", "$.executor.requires", "Requirements must be known capabilities")
    elif len(reqs) != len(set(reqs)):
        issue(out, "duplicate_requirement", "$.executor.requires", "Requirements must be unique")
    if not isinstance(executor.get("mode"),str) or executor.get("mode") not in modes:
        issue(out, "executor_mode", "$.executor.mode", "Invalid bounded mode")

    auth = packet.get("authorization")
    if not isinstance(auth,dict) or set(auth) != {"state","effects","source_refs"}:
        issue(out, "authorization_shape", "$.authorization", "Authorization requires state, effects and source refs")
        auth = {}
    state, effects, refs = auth.get("state"), auth.get("effects"), auth.get("source_refs")
    if not isinstance(state,str) or state not in {"not_requested","pending","granted","denied"}:
        issue(out, "authorization_state", "$.authorization", "Invalid authorization state")
    if not isinstance(effects,list) or any(not isinstance(x,str) or x not in EFFECTS for x in effects):
        issue(out, "authorization_effects", "$.authorization", "Effects must be known names")
    elif len(effects) != len(set(effects)):
        issue(out, "duplicate_authorization_effect", "$.authorization", "Effects must be unique")
    elif any(x not in allowed or x in prohibited for x in effects):
        issue(out, "unauthorized_effect", "$.authorization.effects", "Effect exceeds the explicitly allowed set")
    if not isinstance(refs,list) or any(not isinstance(x,str) or x not in source_ids for x in refs):
        issue(out, "authorization_refs", "$.authorization", "Authorization references must name declared sources")
    elif len(refs) != len(set(refs)):
        issue(out, "duplicate_authorization_ref", "$.authorization", "Authorization refs must be unique")
    if state == "granted" and (not effects or not refs):
        issue(out, "grant_without_evidence", "$.authorization", "Granted effects need effect names and source references")

    technical = packet.get("technical_status")
    if not isinstance(technical,str) or technical not in TECHNICAL:
        issue(out, "technical_status", "$.technical_status", "Invalid technical status")
    if technical == "passed" and (not criteria or any(
        not isinstance(c,dict) or c.get("status") != "pass" or not c.get("evidence_refs")
        for c in criteria)):
        issue(out, "pass_without_acceptance", "$.technical_status", "Technical pass requires all criteria to pass with evidence")

    approval = packet.get("approval")
    if not isinstance(approval,dict) or set(approval) != {"state","source_refs"}:
        issue(out, "approval_shape", "$.approval", "Approval requires state and source refs")
        approval = {}
    state, refs = approval.get("state"), approval.get("source_refs")
    if not isinstance(state,str) or state not in APPROVAL:
        issue(out, "approval_state", "$.approval", "Invalid approval state")
    if not isinstance(refs,list) or any(not isinstance(x,str) or x not in source_ids for x in refs):
        issue(out, "approval_refs", "$.approval", "Approval refs must name declared sources")
    elif len(refs) != len(set(refs)):
        issue(out, "duplicate_approval_ref", "$.approval", "Approval refs must be unique")
    if state in {"approved","published","delivered"} and not refs:
        issue(out, "approval_without_evidence", "$.approval", "Approval/publishing/delivery requires source references")
    return out


def evaluate(batch):
    if not isinstance(batch,dict) or batch.get("version") != 1 or not isinstance(batch.get("packets"),list):
        return {"summary":{"passed":0,"failed":1,"total":1},
                "results":[{"id":None,"passed":False,"issues":[{"code":"invalid_batch","path":"$","message":"Expected version 1 and packets list"}]}]}
    results, seen = [], set()
    for packet in batch["packets"]:
        pid = packet.get("packet_id") if isinstance(packet,dict) else None
        problems = validate_packet(packet)
        if pid in seen:
            issue(problems,"duplicate_packet_id","$.packet_id","Packet IDs must be unique in a batch")
        seen.add(pid)
        results.append({"id":pid,"passed":not problems,"issues":problems})
    return {"summary":{"passed":sum(x["passed"] for x in results),
                       "failed":sum(not x["passed"] for x in results),"total":len(results)},
            "results":results,
            "limits":["Structural validation only; not proof of source truth, consent, real execution, or semantic correctness."]}


def read_json(path):
    if not path.is_file() or path.stat().st_size > 200_000:
        raise ValueError("Missing or oversized JSON input")
    with path.open("r",encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--examples",type=Path,default=HERE/"examples.json")
    parser.add_argument("--expect",choices=("pass","fail"),default="pass")
    args = parser.parse_args(argv)
    result = evaluate(read_json(args.examples))
    print(json.dumps(result,indent=2,sort_keys=True))
    ok = result["summary"]["failed"] == 0
    return 0 if ok == (args.expect == "pass") else 1


if __name__ == "__main__":
    sys.exit(main())
