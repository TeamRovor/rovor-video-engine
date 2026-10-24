"""Offline adversarial checks: no inference, private receipts or Mac access."""
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_draft_actionability import TriageError, triage

SOURCE = "first\nThe WORK guide requires bounded research and a human review handoff.\nthird\n"
DIGEST = hashlib.sha256(SOURCE.encode("utf-8")).hexdigest()
PACKET = "walter-public-v1-blender-isolation-plan"
DELIVERABLE = "An isolated scene render checklist and evidence specification."

SECTIONS = {
    "Evidence": (
        "The public WORK guide requires bounded research and an explicit review "
        "handoff; that requirement is visible in the supplied source line and "
        "does not prove a running Blender application. [[source:WORK.md#L2]]"),
    "Proposed change": (
        "Propose a Blender scene render checklist that records disposable input "
        "assets, camera identity, frame count, and output checksums before a "
        "human decides whether any host execution is justified."),
    "Acceptance check": (
        "Verify the scene render checklist against a pinned public source "
        "snapshot; the expected result is a reproducible checklist with zero "
        "claims of Mac execution and clear failure reasons."),
    "Unverified": (
        "The Blender application and real scene rendering are not verified "
        "on the Mac; this research draft cannot confirm the actual installed "
        "version or the output frames."),
    "Next read-only check": (
        "Inspect the existing public Blender workflow documentation and "
        "compare its expected scene isolation fields with the checklist "
        "without touching a native project."),
}


def render(sections=None):
    data = SECTIONS if sections is None else sections
    return "\n\n".join("## " + k + "\n" + v for k, v in data.items()) + "\n"


def args(**changes):
    defaults = dict(packet_id=PACKET, role="gale", deliverable=DELIVERABLE,
                    public_sources={"WORK.md": SOURCE},
                    expected_source_sha256={"WORK.md": DIGEST},
                    previous_private_drafts=[],
                    trusted_packet=True, trusted_source_snapshot=True,
                    trusted_complete_history=True)
    defaults.update(changes)
    return defaults


def changed(section, value):
    sections = dict(SECTIONS)
    sections[section] = value
    return render(sections)


def prior(answer, packet=PACKET, role="gale"):
    return {"packet_id": packet, "role": role, "answer": answer}


class TriageTests(unittest.TestCase):
    def blocked(self, code, answer=None, **kwargs):
        with self.assertRaises(TriageError) as context:
            triage(render() if answer is None else answer, **args(**kwargs))
        self.assertEqual(str(context.exception), code)

    def test_good_draft_returns_no_private_content_or_approval(self):
        answer = render()
        result = triage(answer, **args())
        self.assertEqual(result["status"], "draft_actionable_needs_human_review")
        self.assertEqual(result["citation_count"], 1)
        self.assertFalse(result["human_approval_granted"])
        self.assertFalse(result["semantic_truth_verified"])
        self.assertFalse(result["mac_execution_verified"])
        self.assertEqual(result["queue_writes"], 0)
        self.assertEqual(result["model_calls"], 0)
        self.assertNotIn("Blender application", str(result))
        self.assertEqual(len(result["private_fingerprint_sha256"]), 64)

    def test_stable_fingerprint_for_whitespace_and_punctuation(self):
        original = triage(render(), **args())["private_fingerprint_sha256"]
        altered = render().replace("disposable input", "disposable,   input")
        self.assertEqual(triage(altered, **args())["private_fingerprint_sha256"],
                         original)

    def test_untrusted_packet(self):
        self.blocked("trusted_packet_required", trusted_packet=False)

    def test_unknown_role(self):
        self.blocked("trusted_packet_required", role="walter")

    def test_invalid_packet(self):
        self.blocked("trusted_packet_required", packet_id="../../secret")

    def test_bad_deliverable(self):
        self.blocked("trusted_packet_required", deliverable="brief")

    def test_untrusted_sources(self):
        self.blocked("trusted_public_sources_required", trusted_source_snapshot=False)

    def test_untrusted_history(self):
        self.blocked("trusted_private_history_required", trusted_complete_history=False)

    def test_missing_headings(self):
        self.blocked("required_sections_missing_or_reordered", answer="No sections")

    def test_reordered_headings(self):
        parts = render().split("\n\n")
        self.blocked("required_sections_missing_or_reordered",
                     answer="\n\n".join(parts[::-1]))

    def test_extra_heading(self):
        self.blocked("required_sections_missing_or_reordered",
                     answer=render() + "\n## Conclusion\nGeneric text\n")

    def test_preamble_rejected(self):
        self.blocked("unexpected_draft_preamble", answer="PRIVATE\n" + render())

    def test_blank_evidence(self):
        self.blocked("generic_or_unactionable_draft",
                     answer=changed("Evidence", "Fine."))

    def test_generic_change(self):
        self.blocked("generic_or_unactionable_draft",
                     answer=changed("Proposed change", "Use best practices to improve efficiency "
                         "and make it better with more investigation and other ideas."))

    def test_missing_uncertainty(self):
        self.blocked("missing_uncertainty_boundary",
                     answer=changed("Unverified", "Done."))

    def test_missing_next_check(self):
        self.blocked("missing_read_only_next_check",
                     answer=changed("Next read-only check", "Done."))

    def test_citation_only_in_wrong_section(self):
        sections = dict(SECTIONS)
        sections["Evidence"] = SECTIONS["Evidence"].replace(
            " [[source:WORK.md#L2]]", "")
        sections["Unverified"] += " [[source:WORK.md#L2]]"
        self.blocked("evidence_section_not_cited", answer=render(sections))

    def test_fabricated_citation_rejected(self):
        self.blocked("citation_or_source_integrity_rejected",
                     answer=render().replace("#L2", "#L999"))

    def test_source_digest_mismatch(self):
        self.blocked("citation_or_source_integrity_rejected",
                     expected_source_sha256={"WORK.md": "0" * 64})

    def test_wrong_source_rejected(self):
        self.blocked("citation_or_source_integrity_rejected",
                     answer=render().replace("source:WORK.md", "source:SECRET.md"))

    def test_malformed_citation_rejected(self):
        self.blocked("citation_or_source_integrity_rejected",
                     answer=render().replace("[[source:WORK.md#L2]]",
                                             "[[source:WORK.md#L2]"))

    def test_wrong_specialist(self):
        self.blocked("wrong_specialist_domain", role="saul")

    def test_deliverable_mismatch(self):
        self.blocked("deliverable_not_addressed",
                     deliverable="A structured client intake privacy and outreach campaign schedule.")

    def test_acceptance_without_test_verb(self):
        self.blocked("acceptance_not_testable",
                     answer=changed("Acceptance check",
                         "The scene render checklist contains an expected summary "
                         "of the source materials and records what could be learned "
                         "without touching any private assets or personal computers."))

    def test_acceptance_without_expected_result(self):
        self.blocked("acceptance_not_testable",
                     answer=changed("Acceptance check",
                         "Verify the scene render checklist using source documents "
                         "and detailed camera settings while keeping all notes "
                         "limited to public metadata for subsequent human review."))

    def test_uncertainty_not_explicit(self):
        self.blocked("uncertainty_not_explicit",
                     answer=changed("Unverified",
                         "The Blender application and the real scene rendering "
                         "have several details that deserve a careful second "
                         "look by an authorized reviewer before a decision."))

    def test_next_check_must_be_read_only(self):
        self.blocked("next_check_not_read_only",
                     answer=changed("Next read-only check",
                         "Deploy the new Blender scene rendering configuration "
                         "to the workstation and then inspect its outputs "
                         "before a human approves the project."))

    def test_next_check_cannot_hide_side_effect(self):
        self.blocked("next_check_not_read_only",
                     answer=changed("Next read-only check",
                         "Inspect the public Blender workflow documentation and "
                         "install the updated native application to compare "
                         "its expected scene isolation fields with the checklist."))

    def test_exact_duplicate_rejected(self):
        self.blocked("duplicate_specialist_draft",
                     previous_private_drafts=[prior(render())])

    def test_formatting_duplicate_rejected(self):
        old = render().replace("disposable input", "disposable, input")
        self.blocked("duplicate_specialist_draft",
                     previous_private_drafts=[prior(old)])

    def test_near_duplicate_rejected(self):
        old = render().replace("the output frames", "the delivered output frames")
        self.blocked("near_duplicate_specialist_draft",
                     previous_private_drafts=[prior(old)])

    def test_unrelated_history_does_not_block(self):
        result = triage(render(), **args(previous_private_drafts=[
            prior(render(), packet="walter-public-v1-proof-before-done", role="hank")]))
        self.assertEqual(result["checked_private_history_count"], 1)

    def test_invalid_history_rejected(self):
        self.blocked("private_history_unverified",
                     previous_private_drafts=[{"answer": "bad"}])

    def test_history_limit_rejected(self):
        self.blocked("private_history_unverified",
                     previous_private_drafts=[prior("x")] * 51)

    def test_rejects_control_characters(self):
        self.blocked("draft_invalid", answer=render() + "\x00")

    def test_rejects_code_fence(self):
        self.blocked("draft_invalid", answer=render() + "\x60\x60\x60")

    def test_rejects_oversized_draft(self):
        self.blocked("draft_invalid", answer=render() + "A" * 22000)

    def test_never_echoes_private_text_in_errors(self):
        secret = "PRIVATE_SECRET_DO_NOT_ECHO"
        with self.assertRaises(TriageError) as ctx:
            triage(render().replace("Propose a Blender", secret + " best practices Blender"),
                   **args())
        self.assertNotIn(secret, str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
