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
        "raw_credentials_disclosed": False,
        "model_requests": 0,
        "billing_eligibility_verified": False,
        "connections_verified_working": False,
    }
    try:
        p = run(["omniroute", "providers", "list", "--json"],
                capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return result
    if p.returncode != 0 or not isinstance(p.stdout, str) or len(p.stdout) > MAX_OUTPUT:
        return result
    raw = p.stdout
    starts = [pos for pos in (raw.find("{"),raw.find("[")) if pos >= 0]
    if not starts:
        return result
    try:
        obj = json.loads(raw[min(starts):])
    except (ValueError, TypeError):
        return result
    if isinstance(obj, list):
        entries = obj
    elif isinstance(obj, dict):
        entries = next((obj[key] for key in ("connections", "providers", "items", "data")
                       if isinstance(obj.get(key), list)), None)
    else:
        entries = None
    if not isinstance(entries, list) or len(entries) > 200:
        return result
    buckets = {}
    for item in entries:
        if not isinstance(item, dict):
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
        "configured_connections_count": len(entries),
        "provider_connection_counts": buckets,
        "note": "Connections are model resources, not employee identities or live model-call proof",
    })
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), sort_keys=True, indent=2))
