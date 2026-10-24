#!/usr/bin/env python3
"""Sanitized local OmniRoute provider inventory; no keys, inference or writes."""
import json
import re
import subprocess

MAX_OUTPUT = 250000
ALLOWED_PROVIDER_NAMES = {
    "openrouter", "groq", "nvidia", "nvidia-nim", "mistral",
    "gemini", "google", "google-ai-studio", "openai", "anthropic",
    "cerebras", "cloudflare", "deepseek", "together", "fireworks",
    "ollama", "qwen", "cohere", "inference", "glm", "zai",
}


def audit(*, run=subprocess.run):
    result = {
        "omniroute_cli_inventory": "unavailable",
        "sanitized_blocker": "not_checked",
        "raw_credentials_disclosed": False,
        "model_requests": 0,
        "billing_eligibility_verified": False,
        "connections_verified_working": False,
    }
    try:
        p = run(["omniroute", "providers", "list", "--json"],
                capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        result["sanitized_blocker"] = "cli_not_executable_or_timed_out"
        return result
    if p.returncode != 0:
        result["sanitized_blocker"] = "cli_nonzero_exit"
        return result
    if not isinstance(p.stdout, str) or len(p.stdout) > MAX_OUTPUT:
        result["sanitized_blocker"] = "cli_output_invalid_or_too_large"
        return result
    raw = p.stdout
    # OmniRoute versions may prepend banners, ANSI color sequences, and
    # human-readable status before their JSON, or append an extra notice.
    # Find an actual bounded JSON root rather than assuming the earliest
    # '[' belongs to the JSON (ANSI itself uses '['). Never print raw text.
    def connection_list(parsed):
        if isinstance(parsed, list):
            return parsed
        if not isinstance(parsed, dict):
            return None
        for key in ("connections", "providers", "items", "data"):
            value = parsed.get(key)
            if isinstance(value, list):
                return value
            if key == "data" and isinstance(value, dict):
                for inner in ("connections", "providers", "items"):
                    if isinstance(value.get(inner), list):
                        return value[inner]
        return None

    decoder = json.JSONDecoder()
    entries = None
    parsed_something = False
    candidates = 0
    for match in re.finditer(r"[\\[{]", raw):
        candidates += 1
        if candidates > 512:
            break
        try:
            parsed, _end = decoder.raw_decode(raw, match.start())
        except (ValueError, TypeError):
            continue
        parsed_something = True
        proposed = connection_list(parsed)
        if proposed is not None:
            entries = proposed
            break
    if entries is None:
        result["sanitized_blocker"] = (
            "cli_json_shape_unrecognized" if parsed_something else
            "cli_json_parse_failed")
        return result
    if len(entries) > 200:
        result["sanitized_blocker"] = "cli_connection_count_exceeds_limit"
        return result
    buckets = {}
    for item in entries:
        if not isinstance(item, dict):
            result["sanitized_blocker"] = "cli_connection_entries_invalid"
            return result
        raw_provider = None
        for field in ("providerId", "provider", "providerType", "type"):
            if isinstance(item.get(field), str):
                raw_provider = item[field].lower()
                break
        provider = raw_provider if raw_provider in ALLOWED_PROVIDER_NAMES else "other"
        buckets[provider] = buckets.get(provider, 0) + 1
    result.update({
        "omniroute_cli_inventory": "parsed_safely",
        "sanitized_blocker": None,
        "configured_connections_count": len(entries),
        "provider_connection_counts": buckets,
        "note": "Connections are model resources, not employee identities or live model-call proof",
    })
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True, indent=2))
