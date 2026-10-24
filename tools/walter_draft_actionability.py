#!/usr/bin/env python3
"""Private actionability and novelty triage for Walter specialist drafts.

An independently trusted caller supplies an approved public packet, pinned
source bytes/digests, and COMPLETE private history. This is a filter BEFORE
human review, not a truth checker, approver, Mac worker, queue or model client.
Never publish draft content or private fingerprints to GitHub.
"""
import hashlib
import re
import unicodedata

from walter_source_citation_gate import CitationError, verify as verify_citations

ROLES = frozenset(("mike", "jane", "jesse", "gale", "gus", "saul", "hank"))
PACKET = re.compile(r"^walter-public-v1-[a-z0-9-]{3,64}$")
HEADINGS = (
    "Evidence", "Proposed change", "Acceptance check", "Unverified",
    "Next read-only check",
)
HEADER = re.compile(r"(?m)^## ([^\r\n]+)[ \t]*$")
CITE = re.compile(r"\[\[source:[^\r\n\]]+\]\]")
WORDS = re.compile(r"[a-z0-9]+")
BAD_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
GENERIC = (
    "best practices", "improve efficiency", "make it better",
    "research more", "explore options", "general improvements",
    "to be determined", "future work", "tbd", "todo",
)
ROLE_TERMS = {
    "mike": ("mac", "launchagent", "sqlite", "omniroute", "worker", "quota", "route"),
    "jane": ("final cut", "fcpxml", "timeline", "editing", "library", "export"),
    "jesse": ("moho", "viseme", "rig", "lip", "animation", "layer"),
    "gale": ("blender", "scene", "render", "camera", "mesh", "3d"),
    "gus": ("intake", "client", "delivery", "operations", "approval", "workflow"),
    "saul": ("social", "content", "outreach", "campaign", "post", "marketing"),
    "hank": ("qa", "test", "verification", "evidence", "ci", "proof"),
}
STOP_WORDS = frozenset((
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on",
    "with", "from", "by", "as", "at", "is", "be", "that", "this",
    "specification", "review", "proposed", "research",
))
CHECK_VERBS = ("verify", "compare", "inspect", "assert", "test", "check",
               "validate", "count", "diff", "reproduce", "measure")
CHECK_RESULTS = ("pass", "fail", "reject", "match", "zero", "expected",
                 "unchanged", "before", "after", "at least", "no more")
UNCERTAINTY = ("not verified", "unverified", "not run", "unknown",
               "cannot confirm", "requires host", "requires review")
READ_ONLY = re.compile(r"^\s*(read|inspect|compare|review|check|verify|audit|examine)\b", re.I)
SIDE_EFFECT = re.compile(
    r"\b(run|execute|deploy|install|send|publish|post|write|commit|merge|delete|modify)\b", re.I
)
MAX_ANSWER = 22000
MAX_HISTORY = 50
NEAR_DUPLICATE_THRESHOLD = 0.82


class TriageError(ValueError):
    """Only stable codes, never private content or provider output."""


def _deny(code):
    raise TriageError(code)


def _words(value):
    return WORDS.findall(unicodedata.normalize("NFKC", value).casefold())


def _normalized(value):
    # Strip citation formatting and normalize punctuation/whitespace in memory.
    return " ".join(_words(CITE.sub(" ", value)))


def _shingles(value):
    tokens = _normalized(value).split()
    if len(tokens) < 5:
        return set(tokens)
    return set(tuple(tokens[i:i + 5]) for i in range(len(tokens) - 4))


def _specific(value, minimum):
    if len(value) < minimum or len(value) > 14000:
        return False
    words = _words(value)
    return (len(words) >= 10 and len(set(words)) >= 8
            and not any(x in value.casefold() for x in GENERIC))


def _sections(answer):
    if (type(answer) is not str or not 1 <= len(answer) <= MAX_ANSWER
            or BAD_CONTROLS.search(answer) or "&#" in answer
            or "\x60\x60\x60" in answer):
        _deny("draft_invalid")
    matches = list(HEADER.finditer(answer))
    if len(matches) != len(HEADINGS) or tuple(
            m.group(1).strip() for m in matches) != HEADINGS:
        _deny("required_sections_missing_or_reordered")
    if answer[:matches[0].start()].strip():
        _deny("unexpected_draft_preamble")
    result = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(answer)
        result[HEADINGS[i]] = answer[match.end():end].strip()
    return result


def _has_phrase(value, phrases):
    words = " " + " ".join(_words(value)) + " "
    return any(" " + phrase + " " in words for phrase in phrases)


def _check_history(history, packet_id, role, answer):
    if not isinstance(history, list) or len(history) > MAX_HISTORY:
        _deny("private_history_unverified")
    current = _normalized(answer)
    shingles = _shingles(answer)
    for record in history:
        if (not isinstance(record, dict) or set(record) !=
                {"packet_id", "role", "answer"}
                or type(record["packet_id"]) is not str
                or PACKET.fullmatch(record["packet_id"]) is None
                or type(record["role"]) is not str or record["role"] not in ROLES
                or type(record["answer"]) is not str
                or len(record["answer"]) > MAX_ANSWER
                or BAD_CONTROLS.search(record["answer"])):
            _deny("private_history_unverified")
        if record["packet_id"] != packet_id or record["role"] != role:
            continue
        if current == _normalized(record["answer"]):
            _deny("duplicate_specialist_draft")
        previous = _shingles(record["answer"])
        union = len(shingles | previous)
        if union and len(shingles & previous) / union >= NEAR_DUPLICATE_THRESHOLD:
            _deny("near_duplicate_specialist_draft")


def triage(answer, *, packet_id, role, deliverable, public_sources,
           expected_source_sha256, previous_private_drafts,
           trusted_packet=False, trusted_source_snapshot=False,
           trusted_complete_history=False):
    """Return private-safe metrics only; NEVER an approval or permission to act.

    The trust flags must be established independently, never from AI output.
    Citation binding does not establish semantic truth. Novelty is lexical.
    """
    if (trusted_packet is not True or type(packet_id) is not str
            or PACKET.fullmatch(packet_id) is None or type(role) is not str
            or role not in ROLES or type(deliverable) is not str
            or not 20 <= len(deliverable) <= 400):
        _deny("trusted_packet_required")
    if trusted_source_snapshot is not True:
        _deny("trusted_public_sources_required")
    if trusted_complete_history is not True:
        _deny("trusted_private_history_required")
    sections = _sections(answer)
    if not all(_specific(sections[k], 65) for k in
               ("Evidence", "Proposed change", "Acceptance check")):
        _deny("generic_or_unactionable_draft")
    if not _specific(sections["Unverified"], 40):
        _deny("missing_uncertainty_boundary")
    if not _specific(sections["Next read-only check"], 40):
        _deny("missing_read_only_next_check")
    if not CITE.search(sections["Evidence"]):
        if "[[source" in sections["Evidence"].casefold():
            _deny("citation_or_source_integrity_rejected")
        _deny("evidence_section_not_cited")
    try:
        citations = verify_citations(
            answer, public_sources, expected_source_sha256)
    except (CitationError, UnicodeError):
        _deny("citation_or_source_integrity_rejected")
    proposed = sections["Proposed change"]
    acceptance = sections["Acceptance check"]
    if not _has_phrase(proposed + " " + acceptance, ROLE_TERMS[role]):
        _deny("wrong_specialist_domain")
    deliverable_words = set(_words(deliverable)) - STOP_WORDS
    matched = deliverable_words.intersection(
        _words(proposed + " " + acceptance))
    if len(matched) < min(2, len(deliverable_words)):
        _deny("deliverable_not_addressed")
    if not (_has_phrase(acceptance, CHECK_VERBS)
            and _has_phrase(acceptance, CHECK_RESULTS)):
        _deny("acceptance_not_testable")
    if not _has_phrase(sections["Unverified"], UNCERTAINTY):
        _deny("uncertainty_not_explicit")
    next_check = sections["Next read-only check"]
    if not READ_ONLY.search(next_check) or SIDE_EFFECT.search(next_check):
        _deny("next_check_not_read_only")
    _check_history(previous_private_drafts, packet_id, role, answer)
    return {
        "status": "draft_actionable_needs_human_review",
        "packet_id": packet_id,
        "role": role,
        "private_fingerprint_sha256": hashlib.sha256(
            _normalized(answer).encode("utf-8")).hexdigest(),
        "citation_count": citations["reference_count"],
        "checked_private_history_count": len(previous_private_drafts),
        "trusted_history_attested_by_caller": True,
        "semantic_truth_verified": False,
        "human_approval_granted": False,
        "mac_execution_verified": False,
        "queue_writes": 0,
        "model_calls": 0,
    }
