#!/usr/bin/env python3
"""Read-only evidence-line citation gate for Walter's approved public workpacks.

A verified line citation is NOT proof that a model's claim is true. This module
only binds the model's explicit references to previously fingerprinted public
source bytes, before a separate human review. It never approves or dispatches
work, reads credentials, calls a model, or changes the worker's SQLite state.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MAX_ANSWER_CHARS = 22000
MAX_ANSWER_BYTES = 50000
MAX_SOURCE_BYTES = 19000
MAX_CITATIONS = 30
MAX_SPAN = 12
MAX_SOURCES = 4
SOURCE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
CITATION = re.compile(
    r"\[\[source:([A-Za-z0-9][A-Za-z0-9._/-]{0,159})"
    r"#L([1-9][0-9]{0,5})(?:-L([1-9][0-9]{0,5}))?\]\]"
)
CITATION_START = re.compile(r"\[\[source\b", re.IGNORECASE)


class CitationError(ValueError):
    """Fixed rejection code; never includes draft or source text."""


def _reject(code):
    raise CitationError(code)


def _valid_name(name):
    return (type(name) is str and SOURCE_NAME.fullmatch(name) is not None
            and all(part not in ("", ".", "..") for part in name.split("/")))


def verify(answer, sources, expected_sha256):
    """Validate references against exact trusted public source snapshots.

    Expected SHA256 values MUST be authoritative source digests captured at
    request creation, not digests computed from the same untrusted draft. The
    caller must separately verify packet identity and source allowlisting.
    Returns only public file names, line numbers and digests; never draft text.
    """
    if (type(answer) is not str or not answer.strip()
            or len(answer) > MAX_ANSWER_CHARS or "\x00" in answer):
        _reject("invalid_or_oversized_draft")
    if (not isinstance(sources, dict) or not 1 <= len(sources) <= MAX_SOURCES
            or not isinstance(expected_sha256, dict)
            or set(expected_sha256) != set(sources)):
        _reject("unverified_public_source_set")
    lines = {}
    for name, source in sources.items():
        if not _valid_name(name):
            _reject("invalid_public_source_name")
        if type(source) is not str or "\x00" in source:
            _reject("invalid_public_source")
        raw = source.encode("utf-8")
        if len(raw) > MAX_SOURCE_BYTES:
            _reject("oversized_public_source")
        digest = expected_sha256[name]
        if (type(digest) is not str or SHA256.fullmatch(digest) is None
                or hashlib.sha256(raw).hexdigest() != digest):
            _reject("source_digest_mismatch")
        lines[name] = source.splitlines()
    citations = list(CITATION.finditer(answer))
    starts = [match.start() for match in CITATION_START.finditer(answer)]
    if not citations:
        _reject("malformed_citation_marker" if starts else "missing_structured_citations")
    if len(citations) > MAX_CITATIONS:
        _reject("too_many_citations")
    # Reject partial markers even if another citation in the draft is valid.
    if starts != [match.start() for match in citations]:
        _reject("malformed_citation_marker")
    references = []
    for match in citations:
        name = match.group(1)
        if not _valid_name(name) or name not in lines:
            _reject("unapproved_citation_source")
        start = int(match.group(2))
        end = int(match.group(3) or match.group(2))
        if (end < start or end - start + 1 > MAX_SPAN
                or end > len(lines[name])
                or not any(line.strip() for line in lines[name][start - 1:end])):
            _reject("citation_line_range_invalid")
        references.append({"path": name, "start_line": start,
                           "end_line": end, "source_sha256": expected_sha256[name]})
    return {"status": "citation_format_verified_needs_human_review",
            "source_integrity_verified": True,
            "semantic_accuracy_verified": False,
            "approval_granted": False,
            "reference_count": len(references), "references": references}


def _public_source(root, name):
    if not _valid_name(name):
        _reject("invalid_public_source_name")
    current = root
    for part in name.split("/"):
        current = current / part
        if current.is_symlink():
            _reject("public_source_redirected")
    if not current.is_file():
        _reject("public_source_missing")
    with current.open("rb") as handle:
        raw = handle.read(MAX_SOURCE_BYTES + 1)
    if len(raw) > MAX_SOURCE_BYTES:
        _reject("oversized_public_source")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        _reject("invalid_public_source")


def _parse_expected(items):
    expected = {}
    for item in items:
        if type(item) is not str or "=" not in item:
            _reject("invalid_source_fingerprint_argument")
        name, digest = item.split("=", 1)
        if (not _valid_name(name) or SHA256.fullmatch(digest) is None
                or name in expected):
            _reject("invalid_source_fingerprint_argument")
        expected[name] = digest
    return expected


def inspect_packet(repo, slug, answer, expected):
    """Load only the previously released public Walter packet and sources."""
    from walter_workpack_compile import compile_packets, verify_checked_in

    repo = Path(repo)
    if repo.is_symlink() or not repo.is_dir():
        _reject("public_checkout_unavailable")
    root = repo.resolve(strict=True)
    verify_checked_in(root)
    packets = compile_packets(root)
    if slug not in packets:
        _reject("unapproved_packet")
    sources = {name: _public_source(root, name)
               for name in packets[slug]["inputs"]}
    return verify(answer, sources, expected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--packet", required=True)
    parser.add_argument("--expected-sha256", action="append", default=[],
                        metavar="PUBLIC_PATH=SHA256")
    args = parser.parse_args(argv)
    try:
        if sys.stdin.isatty():
            _reject("private_draft_stdin_required")
        raw = sys.stdin.buffer.read(MAX_ANSWER_BYTES + 1)
        if len(raw) > MAX_ANSWER_BYTES:
            _reject("invalid_or_oversized_draft")
        try:
            answer = raw.decode("utf-8")
        except UnicodeDecodeError:
            _reject("invalid_or_oversized_draft")
        verdict = inspect_packet(args.repo, args.packet, answer,
                                 _parse_expected(args.expected_sha256))
        print(json.dumps(verdict, sort_keys=True))
        return 0
    except (CitationError, OSError, UnicodeError, ValueError, TypeError):
        # Never echo model output, exceptions or private paths.
        print(json.dumps({"status": "citation_gate_refused",
                          "approval_granted": False,
                          "semantic_accuracy_verified": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
