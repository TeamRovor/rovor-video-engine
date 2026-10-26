#!/usr/bin/env python3
"""Offline, fail-closed OmniRoute request admission and response validation.

Pure helper for the EXISTING worker, not a client, scheduler, or permission to
invoke a model. Caller verifies actual route members and free billing separately.
"""
import re

ROUTE = re.compile(r"^rovor-[a-z0-9-]{3,64}$")
FREE_MODEL = re.compile(r"^openrouter/[a-z0-9][a-z0-9._/-]{1,110}:free$")
MAX_TOKENS = 2400
MAX_INPUT_CHARS = 28000
MAX_OUTPUT_CHARS = 22000


class AdmissionError(ValueError):
    """Stable error code without private provider response text."""


def _fail(code):
    raise AdmissionError(code)


def prepare_request(route, members, capabilities, messages, *,
                    route_verified_free=False):
    """Admit only a verified free route whose every member supports 'none'.

    'capabilities' is fresh trusted model metadata keyed by exact model ID.
    The caller must first verify route membership and zero-cost eligibility.
    Mandatory/unknown reasoning is blocked instead of silently ignored.
    """
    if (type(route) is not str or not ROUTE.fullmatch(route)
            or route_verified_free is not True):
        _fail("route_not_verified_free")
    if (not isinstance(members, (tuple, list)) or not 1 <= len(members) <= 5
            or any(type(m) is not str or not FREE_MODEL.fullmatch(m)
                   for m in members)
            or len(set(members)) != len(members)):
        _fail("unsafe_route_members")
    if not isinstance(capabilities, dict):
        _fail("capabilities_unavailable")
    for model in members:
        meta = capabilities.get(model)
        if not isinstance(meta, dict) or meta.get("id") not in (
                model, model.removeprefix("openrouter/")):
            _fail("model_capabilities_unverified")
        reasoning = meta.get("reasoning")
        if not isinstance(reasoning, dict):
            _fail("reasoning_capabilities_unknown")
        if reasoning.get("mandatory") is not False:
            _fail("reasoning_may_be_mandatory")
        efforts = reasoning.get("supported_efforts")
        if (not isinstance(efforts, list) or
                any(type(e) is not str for e in efforts) or
                "none" not in efforts):
            _fail("reasoning_disable_unsupported")
    if (not isinstance(messages, (tuple, list)) or len(messages) != 2
            or any(not isinstance(msg, dict)
                   or set(msg) != {"role", "content"}
                   for msg in messages)):
        _fail("invalid_public_prompt")
    if ([msg["role"] for msg in messages] != ["system", "user"]
            or any(type(msg["content"]) is not str
                   or not msg["content"].strip() for msg in messages)
            or sum(len(msg["content"]) for msg in messages) > MAX_INPUT_CHARS):
        _fail("invalid_public_prompt")
    return {
        "model": route,
        "messages": [dict(msg) for msg in messages],
        "temperature": 0.1,
        "stream": False,
        "max_tokens": MAX_TOKENS,
        "reasoning": {"effort": "none"},
    }


def extract_review_text(response):
    """Accept only a complete visible answer; reject length and blank outputs.

    Identifies reasoning-only budget exhaustion using usage when available.
    No retry, network access, output persistence or approval is performed.
    """
    if not isinstance(response, dict):
        _fail("invalid_response_shape")
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        _fail("invalid_response_shape")
    choice = choices[0]
    if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
        _fail("invalid_response_shape")
    content = choice["message"].get("content")
    if not isinstance(content, str):
        _fail("invalid_response_shape")
    usage = response.get("usage")
    reasoning_tokens = None
    completion_tokens = None
    if usage is not None:
        if not isinstance(usage, dict):
            _fail("invalid_usage_shape")
        completion_tokens = usage.get("completion_tokens")
        if (completion_tokens is not None and
                (type(completion_tokens) is not int or completion_tokens < 0)):
            _fail("invalid_usage_shape")
        details = usage.get("completion_tokens_details")
        if details is not None:
            if not isinstance(details, dict):
                _fail("invalid_usage_shape")
            reasoning_tokens = details.get("reasoning_tokens")
            if (reasoning_tokens is not None and
                    (type(reasoning_tokens) is not int or reasoning_tokens < 0
                     or completion_tokens is None
                     or reasoning_tokens > completion_tokens)):
                _fail("invalid_usage_shape")
    finish = choice.get("finish_reason")
    if finish == "length":
        if (not content.strip() and completion_tokens is not None
                and reasoning_tokens is not None
                and reasoning_tokens >= completion_tokens):
            _fail("reasoning_budget_exhausted")
        _fail("incomplete_length_stop")
    if finish != "stop":
        _fail("unapproved_finish_reason")
    if not content.strip():
        _fail("empty_visible_output")
    if len(content) > MAX_OUTPUT_CHARS:
        _fail("output_exceeds_review_limit")
    return content
