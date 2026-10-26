"""Offline, no-model regression for the public research citation review gate."""
import contextlib
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from walter_source_citation_gate import (CitationError, inspect_packet, main,
                                         verify, _parse_expected, _public_source)

NAME = "WORK.md"
TEXT = "# Worker rules\nUse STOP before every dispatch.\nOnly approved public sources.\n"
HASH = hashlib.sha256(TEXT.encode()).hexdigest()


def check(answer="Claim [[source:WORK.md#L2-L3]]", sources=None, digests=None):
    return verify(answer, {NAME: TEXT} if sources is None else sources,
                  {NAME: HASH} if digests is None else digests)


class CitationTests(unittest.TestCase):
    def blocked(self, code, *args, **kwargs):
        with self.assertRaises(CitationError) as err:
            check(*args, **kwargs)
        self.assertEqual(str(err.exception), code)

    def test_valid_range_needs_human_review_not_approval(self):
        result = check()
        self.assertEqual(result["status"], "citation_format_verified_needs_human_review")
        self.assertFalse(result["approval_granted"])
        self.assertFalse(result["semantic_accuracy_verified"])
        self.assertEqual(result["reference_count"], 1)
        self.assertEqual(result["references"][0]["start_line"], 2)
        self.assertEqual(result["references"][0]["end_line"], 3)
        self.assertEqual(result["references"][0]["source_sha256"], HASH)
        self.assertNotIn("Claim", str(result))

    def test_single_line_reference(self):
        self.assertEqual(check("[[source:WORK.md#L1]]")["reference_count"], 1)

    def test_repeated_references_counted_without_draft_content(self):
        r = check("secret answer [[source:WORK.md#L1]] then [[source:WORK.md#L2]]")
        self.assertEqual(r["reference_count"], 2)
        self.assertNotIn("secret answer", str(r))

    def test_empty_draft(self):
        self.blocked("invalid_or_oversized_draft", "  ")

    def test_nul_draft(self):
        self.blocked("invalid_or_oversized_draft", "x\x00 [[source:WORK.md#L1]]")

    def test_long_draft(self):
        self.blocked("invalid_or_oversized_draft", "a" * 22001)

    def test_missing_structured_citation(self):
        self.blocked("missing_structured_citations", "WORK.md line 1")

    def test_malformed_marker_rejected_even_if_other_marker_valid(self):
        self.blocked("malformed_citation_marker", "[[source:WORK.md#L1]] [[source:BAD]]")

    def test_mixed_case_marker_rejected(self):
        self.blocked("malformed_citation_marker", "[[SOURCE:WORK.md#L1]]")

    def test_unknown_source(self):
        self.blocked("unapproved_citation_source", "[[source:OTHER.md#L1]]")

    def test_parent_escape(self):
        self.blocked("malformed_citation_marker", "[[source:../WORK.md#L1]]")

    def test_absolute_path(self):
        self.blocked("malformed_citation_marker", "[[source:/tmp/WORK.md#L1]]")

    def test_reversed_range(self):
        self.blocked("citation_line_range_invalid", "[[source:WORK.md#L3-L2]]")

    def test_out_of_bounds_line(self):
        self.blocked("citation_line_range_invalid", "[[source:WORK.md#L4]]")

    def test_excessive_span(self):
        content = "line\n" * 15
        self.blocked("citation_line_range_invalid", "[[source:WORK.md#L1-L13]]",
                     sources={NAME: content},
                     digests={NAME: hashlib.sha256(content.encode()).hexdigest()})

    def test_whitespace_only_line(self):
        content = " \n\n"
        self.blocked("citation_line_range_invalid", "[[source:WORK.md#L1-L2]]",
                     sources={NAME: content},
                     digests={NAME: hashlib.sha256(content.encode()).hexdigest()})

    def test_wrong_digest(self):
        self.blocked("source_digest_mismatch", digests={NAME: "0" * 64})

    def test_missing_expected_hash(self):
        self.blocked("unverified_public_source_set", digests={})

    def test_extra_expected_hash(self):
        self.blocked("unverified_public_source_set", digests={NAME: HASH, "other": HASH})

    def test_rejects_bad_source_name(self):
        self.blocked("invalid_public_source_name", sources={"../secret": TEXT},
                     digests={"../secret": HASH})

    def test_rejects_oversized_source(self):
        content = "x" * 19001
        self.blocked("oversized_public_source", sources={NAME: content},
                     digests={NAME: hashlib.sha256(content.encode()).hexdigest()})

    def test_rejects_more_than_30_citations(self):
        self.blocked("too_many_citations", " ".join(["[[source:WORK.md#L1]]"] * 31))

    def test_rejects_boolean_or_nonstring_draft(self):
        self.blocked("invalid_or_oversized_draft", None)

    def test_rejects_invalid_digest_format(self):
        self.blocked("source_digest_mismatch", digests={NAME: "xyz"})

    def test_rejects_duplicate_fingerprint_arguments(self):
        with self.assertRaises(CitationError):
            _parse_expected(["WORK.md=" + HASH, "WORK.md=" + HASH])

    def test_rejects_symlinked_public_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "real.md").write_text(TEXT)
            (root / "WORK.md").symlink_to(root / "real.md")
            with self.assertRaises(CitationError) as err:
                _public_source(root, NAME)
            self.assertEqual(str(err.exception), "public_source_redirected")

    def test_inspect_packet_binds_to_approved_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / NAME).write_text(TEXT)
            with mock.patch("walter_workpack_compile.verify_checked_in") as release, \
                 mock.patch("walter_workpack_compile.compile_packets",
                            return_value={"walter-v1-test": {"inputs": [NAME]}}):
                result = inspect_packet(root, "walter-v1-test",
                                        ("The public workflow describes a verified STOP "
                                         "check before each task dispatch. Reviewers must "
                                         "separately authenticate the source snapshot and "
                                         "the worker's receipt before accepting a finding. "
                                         "This offline test does not contact a Mac or "
                                         "run any inference. [[source:WORK.md#L2]]"),
                                        {NAME: HASH})
            self.assertEqual(result["reference_count"], 1)
            release.assert_called_once()

    def test_research_draft_rejects_citation_only_answer(self):
        from walter_source_citation_gate import _research_draft_quality
        with self.assertRaises(CitationError) as error:
            _research_draft_quality("[[source:WORK.md#L2]]")
        self.assertEqual(str(error.exception), "draft_not_substantive")
        # The low-level citation binding used by reviewed findings remains valid.
        self.assertEqual(check("[[source:WORK.md#L2]]")["reference_count"], 1)

    def test_research_draft_rejects_uncited_second_paragraph(self):
        from walter_source_citation_gate import _research_draft_quality
        first = ("The source describes the current dispatch STOP check and requires "
                 "fresh verification before another task is proposed to a specialist. "
                 "[[source:WORK.md#L2]]")
        second = ("This additional unsupported paragraph claims that the worker "
                  "is constantly productive and all models have been verified "
                  "throughout the day despite no new independent evidence.")
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(first + "\n\n" + second)
        self.assertEqual(str(error.exception), "draft_paragraph_missing_citation")

    def test_research_draft_rejects_single_citation_padding(self):
        from walter_source_citation_gate import _research_draft_quality
        prose = ("This proposed workflow uses documented task identity and source "
                 "verification before any specialist draft is considered for review. " * 9)
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(prose + " [[source:WORK.md#L2]]")
        self.assertEqual(str(error.exception), "draft_citation_density_insufficient")

    def test_research_draft_rejects_repetitive_generic_filler(self):
        from walter_source_citation_gate import _research_draft_quality
        prose = ("The worker should improve results with a better process. " * 5)
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(prose + " [[source:WORK.md#L2]]")
        self.assertEqual(str(error.exception), "draft_not_substantive")

    def test_research_draft_accepts_two_grounded_paragraphs(self):
        from walter_source_citation_gate import _research_draft_quality
        answer = (
            "The dispatch workflow must verify its STOP state before selecting "
            "another grounded task. This is a proposed code-review check rather "
            "than proof of live host operation. [[source:WORK.md#L2]]\n\n"
            "The research packet should preserve its source fingerprint and "
            "separate any model-authored conclusions from authenticated evidence. "
            "A reviewer can then evaluate the proposed regression tests before "
            "approving further engineering work. [[source:WORK.md#L3]]"
        )
        result = _research_draft_quality(answer)
        self.assertTrue(result["draft_quality_checked"])
        self.assertEqual(result["cited_prose_blocks"], 2)
        self.assertGreaterEqual(result["prose_word_count"], 30)

    def test_direct_verifier_enforces_utf8_byte_limit(self):
        # 13,000 astral symbols fit the character limit but exceed 50 KiB.
        self.blocked("invalid_or_oversized_draft",
                     "\U0001f600" * 13000 + " [[source:WORK.md#L2]]")

    def test_direct_verifier_rejects_unencodable_surrogates(self):
        self.blocked("invalid_or_oversized_draft",
                     "\ud800 [[source:WORK.md#L2]]")

    def test_fenced_citation_cannot_satisfy_research_gate(self):
        from walter_source_citation_gate import _research_draft_quality
        fence = chr(96) * 3
        answer = (fence + "text\n" +
                  "This code sample repeats apparently credible source claims. " * 7 +
                  "\n[[source:WORK.md#L2]]\n" + fence)
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(answer)
        self.assertEqual(str(error.exception), "draft_citation_in_code")
        # Low-level binding still supports independently reviewed citations.
        self.assertEqual(check(answer)["reference_count"], 1)

    def test_tilde_fenced_and_indented_citations_rejected(self):
        from walter_source_citation_gate import _research_draft_quality
        for answer in ("~~~python\n[[source:WORK.md#L2]]\n~~~",
                       "    [[source:WORK.md#L2]]"):
            with self.subTest(answer=answer):
                with self.assertRaises(CitationError) as error:
                    _research_draft_quality(answer)
                self.assertEqual(str(error.exception), "draft_citation_in_code")

    def test_inline_code_citation_cannot_launder_prose(self):
        from walter_source_citation_gate import _research_draft_quality
        marker = chr(96)
        answer = ("This text discusses real operational checks but deliberately "
                  "provides no normal prose citation despite numerous words. " * 3
                  + marker + "[[source:WORK.md#L2]]" + marker)
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(answer)
        self.assertEqual(str(error.exception), "draft_citation_in_code")

    def test_code_words_cannot_pad_short_cited_prose(self):
        from walter_source_citation_gate import _research_draft_quality
        fence = chr(96) * 3
        answer = ("A STOP check is required. [[source:WORK.md#L2]]\n\n" +
                  fence + "text\n" +
                  "Many irrelevant source-free code words are repeated here. " * 12 +
                  "\n" + fence)
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(answer)
        self.assertEqual(str(error.exception), "draft_not_substantive")

    def test_valid_research_with_code_example_still_passes(self):
        from walter_source_citation_gate import _research_draft_quality
        fence = chr(96) * 3
        answer = (
            "The existing dispatch design requires a STOP check before "
            "each new claim and separates candidate drafts from human "
            "approval. A reviewer can verify the source digest and then "
            "evaluate the proposed change without running any model. "
            "[[source:WORK.md#L2]]\n\n" +
            fence + "python\nprint('read-only example')\n" + fence)
        result = _research_draft_quality(answer)
        self.assertTrue(result["draft_quality_checked"])
        self.assertEqual(result["cited_prose_blocks"], 1)
        self.assertGreaterEqual(result["prose_word_count"], 30)

    def test_unclosed_fence_rejected(self):
        from walter_source_citation_gate import _research_draft_quality
        answer = ("This source documents the STOP gate and human review. "
                  "[[source:WORK.md#L2]]\n\n" + chr(96) * 3 +
                  "python\nprint('unterminated')")
        with self.assertRaises(CitationError) as error:
            _research_draft_quality(answer)
        self.assertEqual(str(error.exception), "draft_unclosed_code_fence")

    def test_unknown_packet_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("walter_workpack_compile.verify_checked_in"), \
                 mock.patch("walter_workpack_compile.compile_packets", return_value={}):
                with self.assertRaises(CitationError) as err:
                    inspect_packet(tmp, "unknown", "[[source:WORK.md#L1]]", {NAME: HASH})
            self.assertEqual(str(err.exception), "unapproved_packet")

    def test_cli_private_stdin_never_prints_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / NAME).write_text(TEXT)
            answer = ("VERY_PRIVATE_MODEL_ANSWER: The existing public worker "
                      "source requires a STOP check before each dispatch. "
                      "A human reviewer should independently inspect the "
                      "claimed task identity, verified source fingerprint, "
                      "and receipt status before any new work is approved. "
                      "No Mac or provider execution is asserted here. "
                      "[[source:WORK.md#L2]]")
            fake_stdin = io.TextIOWrapper(io.BytesIO(answer.encode()), encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch("sys.stdin", fake_stdin), contextlib.redirect_stdout(stdout), \
                 mock.patch("walter_workpack_compile.verify_checked_in"), \
                 mock.patch("walter_workpack_compile.compile_packets",
                            return_value={"walter-v1-test": {"inputs": [NAME]}}):
                status = main(["--repo", tmp, "--packet", "walter-v1-test",
                               "--expected-sha256", NAME + "=" + HASH])
            self.assertEqual(status, 0)
            self.assertNotIn("VERY_PRIVATE", stdout.getvalue())
            self.assertIn("citation_format_verified_needs_human_review", stdout.getvalue())

    def test_cli_rejects_citation_only_draft_without_leaking_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / NAME).write_text(TEXT)
            answer = "PRIVATE_CITATION_ONLY [[source:WORK.md#L2]]"
            fake_stdin = io.TextIOWrapper(io.BytesIO(answer.encode()), encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch("sys.stdin", fake_stdin), contextlib.redirect_stdout(stdout), \
                 mock.patch("walter_workpack_compile.verify_checked_in"), \
                 mock.patch("walter_workpack_compile.compile_packets",
                            return_value={"walter-v1-test": {"inputs": [NAME]}}):
                status = main(["--repo", tmp, "--packet", "walter-v1-test",
                               "--expected-sha256", NAME + "=" + HASH])
            self.assertEqual(status, 2)
            self.assertNotIn("PRIVATE_CITATION_ONLY", stdout.getvalue())
            self.assertIn("citation_gate_refused", stdout.getvalue())

    def test_cli_mismatch_is_content_free(self):
        fake_stdin = io.TextIOWrapper(io.BytesIO(b"SECRET_UNTRUSTED"), encoding="utf-8")
        stdout = io.StringIO()
        with mock.patch("sys.stdin", fake_stdin), contextlib.redirect_stdout(stdout):
            code = main(["--repo", "/does-not-exist", "--packet", "test"])
        self.assertEqual(code, 2)
        self.assertNotIn("SECRET_UNTRUSTED", stdout.getvalue())
        self.assertIn("citation_gate_refused", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
