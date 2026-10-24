"""Offline regression for explicit free-route reasoning admission."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from omniroute_reasoning_admission import (
    AdmissionError, MAX_TOKENS, extract_review_text, prepare_request,
)

M1 = "openrouter/example/verified-text:free"
M2 = "openrouter/example/verified-code:free"


def meta(model, efforts=("none", "low"), mandatory=False):
    return {"id": model.removeprefix("openrouter/"), "reasoning": {
        "supported_efforts": list(efforts) if efforts is not None else None,
        "mandatory": mandatory}}


def request(members=None, capabilities=None, messages=None, approved=True):
    members = [M1, M2] if members is None else members
    capabilities = {M1: meta(M1), M2: meta(M2)} if capabilities is None else capabilities
    messages = [{"role": "system", "content": "Public research only"},
                {"role": "user", "content": "Cite approved public sources"}] if messages is None else messages
    return prepare_request("rovor-text-free-v1", members, capabilities,
                           messages, route_verified_free=approved)


def completed(content="A sourced review", finish="stop", usage=None):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {"completion_tokens": 20} if usage is None else usage}


class RequestAdmissionTests(unittest.TestCase):
    def assert_blocked(self, code, *args, **kwargs):
        with self.assertRaises(AdmissionError) as context:
            request(*args, **kwargs)
        self.assertEqual(str(context.exception), code)

    def test_exact_no_reasoning_shape_and_bounded_tokens(self):
        payload = request()
        self.assertEqual(payload["model"], "rovor-text-free-v1")
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertEqual(payload["max_tokens"], MAX_TOKENS)
        self.assertIs(payload["stream"], False)
        self.assertEqual(len(payload["messages"]), 2)

    def test_copies_messages(self):
        msgs = [{"role": "system", "content": "Public"},
                {"role": "user", "content": "Cite sources"}]
        payload = request(messages=msgs)
        msgs[0]["content"] = "CHANGED"
        self.assertEqual(payload["messages"][0]["content"], "Public")

    def test_route_requires_explicit_verified_free_approval(self):
        self.assert_blocked("route_not_verified_free", approved=False)

    def test_rejects_paid_and_dynamic_model(self):
        for member in ["openrouter/vendor/paid", "openrouter/free",
                       "openrouter/vendor/paid:paid", "http://localhost/model"]:
            self.assert_blocked("unsafe_route_members", members=[member])

    def test_rejects_duplicate_members(self):
        self.assert_blocked("unsafe_route_members", members=[M1, M1])

    def test_rejects_missing_model_metadata(self):
        self.assert_blocked("model_capabilities_unverified",
                            capabilities={M1: meta(M1)})

    def test_rejects_mismatched_model_metadata(self):
        self.assert_blocked("model_capabilities_unverified",
                            capabilities={M1: meta(M2), M2: meta(M2)})

    def test_rejects_unknown_reasoning(self):
        self.assert_blocked("reasoning_capabilities_unknown",
                            capabilities={M1: {"id": M1}, M2: meta(M2)})

    def test_rejects_mandatory_reasoning(self):
        self.assert_blocked("reasoning_may_be_mandatory",
                            capabilities={M1: meta(M1, mandatory=True), M2: meta(M2)})

    def test_rejects_no_none_support(self):
        self.assert_blocked("reasoning_disable_unsupported",
                            capabilities={M1: meta(M1, efforts=["low", "medium"]), M2: meta(M2)})

    def test_rejects_null_effort_catalog(self):
        self.assert_blocked("reasoning_disable_unsupported",
                            capabilities={M1: meta(M1, efforts=None), M2: meta(M2)})

    def test_rejects_oversized_public_prompt(self):
        self.assert_blocked("invalid_public_prompt",
                            messages=[{"role": "system", "content": "a" * 28000},
                                      {"role": "user", "content": "b"}])

    def test_rejects_unexpected_prompt_role(self):
        self.assert_blocked("invalid_public_prompt",
                            messages=[{"role": "system", "content": "Public"},
                                      {"role": "tool", "content": "unsafe"}])


class ResponseTests(unittest.TestCase):
    def assert_blocked(self, code, response):
        with self.assertRaises(AdmissionError) as context:
            extract_review_text(response)
        self.assertEqual(str(context.exception), code)

    def test_accepts_complete_visible_text(self):
        self.assertEqual(extract_review_text(completed()), "A sourced review")

    def test_rejects_empty_text(self):
        self.assert_blocked("empty_visible_output", completed("   "))

    def test_rejects_reasoning_only_length_stop(self):
        self.assert_blocked("reasoning_budget_exhausted", completed(
            "", "length", {"completion_tokens": 2400,
                            "completion_tokens_details": {"reasoning_tokens": 2400}}))

    def test_rejects_partial_text_with_length_stop(self):
        self.assert_blocked("incomplete_length_stop", completed("Partial", "length"))

    def test_rejects_blank_length_without_usage_as_incomplete(self):
        self.assert_blocked("incomplete_length_stop", {"choices": [
            {"message": {"content": ""}, "finish_reason": "length"}]})

    def test_rejects_missing_choices(self):
        self.assert_blocked("invalid_response_shape", {"choices": []})

    def test_rejects_unexpected_finish(self):
        self.assert_blocked("unapproved_finish_reason", completed("Answer", "content_filter"))

    def test_rejects_non_string_content(self):
        self.assert_blocked("invalid_response_shape", completed(content=["private"]))

    def test_inconsistent_provider_reasoning_counter_does_not_hide_complete_visible_answer(self):
        # Exact accounting anomaly observed on owner's macOS OmniRoute:
        # prompt=27, completion=52, reasoning=59, total=79.
        usage={"prompt_tokens": 27, "completion_tokens": 52,
               "total_tokens": 79,
               "completion_tokens_details": {"reasoning_tokens": 59}}
        self.assertEqual(extract_review_text(completed("READY", usage=usage)),
                         "READY")

    def test_inconsistent_usage_still_rejects_truncation_and_blank_answers(self):
        usage={"prompt_tokens": 27, "completion_tokens": 52,
               "total_tokens": 79,
               "completion_tokens_details": {"reasoning_tokens": 59}}
        self.assert_blocked("incomplete_length_stop",
                            completed("Partial", "length", usage))
        self.assert_blocked("incomplete_length_stop",
                            completed("", "length", usage))
        self.assert_blocked("empty_visible_output",
                            completed("   ", "stop", usage))
        self.assert_blocked("unapproved_finish_reason",
                            completed("READY", "content_filter", usage))

    def test_rejects_genuinely_malformed_reasoning_usage(self):
        for value in (-1, True, "59"):
            self.assert_blocked("invalid_usage_shape", completed(
                "READY", usage={"completion_tokens": 52,
                               "completion_tokens_details": {"reasoning_tokens": value}}))
        self.assert_blocked("invalid_usage_shape", completed(
            "READY", usage={"completion_tokens": 52,
                            "completion_tokens_details": "PRIVATE_INVALID_DATA"}))

    def test_rejects_boolean_usage(self):
        self.assert_blocked("invalid_usage_shape", completed(
            "Answer", usage={"completion_tokens": True}))

    def test_rejects_oversized_answer(self):
        self.assert_blocked("output_exceeds_review_limit", completed("A" * 22001))

    def test_error_never_echoes_provider_private_text(self):
        private = "PRIVATE_PROVIDER_SECRET_123"
        self.assert_blocked("unapproved_finish_reason", completed(private, "tool_calls"))


if __name__ == "__main__":
    unittest.main()
