#!/usr/bin/env python3
"""Compile Walter's approved public research backlog into inert OmniRoute workpacks.

No HTTP, model use, worker queue, SQLite, Mac services, scheduler, or credentials.
Existing workpack runner retains a separate hard-coded packet allowlist.
"""
import argparse
import json
from pathlib import Path
import re
import sys

from walter_research_backlog import validated

ROOT = Path(__file__).resolve().parents[1]
OUT = Path("coordination/omniroute-workpacks")
SOURCE_PREFIX = "walter-public-v1-"
SLUG_PREFIX = "walter-v1-"
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,55}$")
ROLE_TYPES = {
    "mike": "evidence-triage",
    "jane": "software-architecture",
    "jesse": "software-architecture",
    "gale": "software-architecture",
    "gus": "evidence-triage",
    "saul": "evidence-triage",
    "hank": "evidence-triage",
}
SCHEMA_KEYS = {
    "schema_version", "slug", "id", "title", "role", "inputs", "task",
    "deliverable", "acceptance", "visibility", "output_mode",
    "max_input_chars", "max_output_chars", "external_effects_allowed",
    "mac_gui_required",
}


def packet_slug(job):
    ident = job["id"]
    if not isinstance(ident, str) or not ident.startswith(SOURCE_PREFIX):
        raise ValueError("unapproved_backlog_identifier")
    slug = SLUG_PREFIX + ident[len(SOURCE_PREFIX):]
    if not SLUG_RE.fullmatch(slug):
        raise ValueError("legacy_runner_slug_limit")
    return slug


def compile_packets(root=ROOT):
    """Pure compilation, returning slug-to-packet objects; does not write."""
    release = validated(root)
    packets = {}
    for job in release["jobs"]:
        slug = packet_slug(job)
        role = job["role"]
        if slug in packets or role not in ROLE_TYPES:
            raise ValueError("duplicate_packet_or_unknown_role")
        task = (
            "ROVOR ghost specialist: " + role.upper() + ". "
            "Research only from the provided public source excerpts; "
            "cite exact supplied files and identify unverified claims. "
            "No model-generated follow-up may enqueue itself. "
            + job["task"]
        )
        packet = {
            "schema_version": 1,
            "slug": slug,
            "id": job["id"],
            "title": "ROVOR " + role.title() + " research: " + slug[len(SLUG_PREFIX):].replace("-", " "),
            "role": ROLE_TYPES[role],
            "inputs": list(job["sources"]),
            "task": task,
            "deliverable": job["deliverable"],
            "acceptance": list(job["acceptance"]),
            "visibility": "public-repository-metadata-only",
            "output_mode": "draft_review_only",
            "max_input_chars": 28000,
            "max_output_chars": 22000,
            "external_effects_allowed": False,
            "mac_gui_required": False,
        }
        validate_legacy_packet(root, packet, expected_job=job)
        packets[slug] = packet
    if len(packets) != 14:
        raise ValueError("missing_specialist_packets")
    return packets


def validate_legacy_packet(root, packet, expected_job=None):
    """Match PR41 workpack runner's structural and source-size guards."""
    if not isinstance(packet, dict) or set(packet) != SCHEMA_KEYS:
        raise ValueError("invalid_packet_shape")
    slug = packet["slug"]
    if (not isinstance(slug, str) or not SLUG_RE.fullmatch(slug)
            or not slug.startswith(SLUG_PREFIX)
            or packet["schema_version"] != 1
            or packet["role"] not in ("evidence-triage", "software-architecture", "inference-routing")
            or packet["visibility"] != "public-repository-metadata-only"
            or packet["output_mode"] != "draft_review_only"
            or type(packet["external_effects_allowed"]) is not bool
            or packet["external_effects_allowed"] is not False
            or packet["mac_gui_required"] is not False
            or type(packet["max_input_chars"]) is not int
            or packet["max_input_chars"] != 28000
            or type(packet["max_output_chars"]) is not int
            or packet["max_output_chars"] != 22000):
        raise ValueError("legacy_packet_policy")
    if (not isinstance(packet["id"], str) or not packet["id"].startswith(SOURCE_PREFIX)
            or packet_slug({"id": packet["id"]}) != slug
            or not isinstance(packet["title"], str) or len(packet["title"]) > 240
            or not isinstance(packet["task"], str) or len(packet["task"]) > 3800
            or not isinstance(packet["deliverable"], str)
            or not isinstance(packet["acceptance"], list)
            or not packet["acceptance"]
            or any(not isinstance(x, str) for x in packet["acceptance"])):
        raise ValueError("legacy_packet_content")
    inputs = packet["inputs"]
    if (not isinstance(inputs, list) or not 1 <= len(inputs) <= 4
            or len(inputs) != len(set(inputs))
            or any(not isinstance(name, str) for name in inputs)):
        raise ValueError("legacy_input_list")
    chars = 0
    root = Path(root).resolve(strict=True)
    for relative in inputs:
        if (relative.startswith("/") or "\\" in relative
                or any(bit in ("", ".", "..") for bit in relative.split("/"))
                or ".env" in relative.lower() or ".git" in relative.split("/")):
            raise ValueError("unsafe_public_source")
        part = root
        for segment in relative.split("/"):
            part = part / segment
            if part.is_symlink():
                raise ValueError("redirected_public_source")
        if not part.is_file():
            raise ValueError("source_missing")
        body = part.read_bytes()
        if len(body) > 19000:
            raise ValueError("public_source_over_limit")
        chars += len(body.decode("utf-8", errors="strict"))
    if chars > 28000:
        raise ValueError("combined_public_sources_over_limit")
    if expected_job is not None and (
            packet["id"] != expected_job["id"]
            or inputs != expected_job["sources"]
            or packet["role"] != ROLE_TYPES[expected_job["role"]]):
        raise ValueError("backlog_packet_mismatch")
    blob = json.dumps(packet, indent=2, ensure_ascii=False) + "\n"
    if len(blob.encode("utf-8")) > 10000:
        raise ValueError("legacy_packet_file_over_limit")
    return blob


def verify_checked_in(root=ROOT):
    """Fail closed on missing/extra/modified checked-in Walter workpacks."""
    root = Path(root).resolve(strict=True)
    expected = compile_packets(root)
    folder = root / OUT
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("workpack_directory_missing_or_redirected")
    existing = list(folder.glob(SLUG_PREFIX + "*.json"))
    if len(existing) != len(expected):
        raise ValueError("incomplete_or_extra_workpacks")
    for slug, packet in expected.items():
        path = folder / (slug + ".json")
        if path.is_symlink() or not path.is_file():
            raise ValueError("workpack_missing_or_redirected")
        blob = validate_legacy_packet(root, packet)
        if path.read_bytes() != blob.encode("utf-8"):
            raise ValueError("checked_in_workpack_drift")
    return {"status": "all_packets_schema_verified_staged_not_executable",
            "packets": len(expected), "model_calls": 0, "queue_writes": 0,
            "mac_runtime_changed": False, "pending_runner_allowlist": True}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(verify_checked_in(args.root), sort_keys=True))
        return 0
    except (ValueError, KeyError, OSError, TypeError, UnicodeError) as exc:
        print(json.dumps({"status": "blocked",
                          "error_class": type(exc).__name__,
                          "model_calls": 0, "queue_writes": 0},
                         sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
