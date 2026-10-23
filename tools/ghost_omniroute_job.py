#!/usr/bin/env python3
"""Opt-in, one-shot OmniRoute research adapter for the EXISTING SQLite queue.

No scheduler, shell executor, native app control, code changes, or automatic
model retry. Requires co-located reviewed OmniRoute workpack + review modules.
Private drafts always require review, never satisfy tasks automatically.
"""
import json
import os
from pathlib import Path
import subprocess

# Exact free-only combo members observed on the user's Mac 2026-10-23.
# Fail closed if local routes change; this does not prove upstream quota,
# provider availability, or that a third-party account cannot be billed.
ROUTES = {
    'runner-blocker': (
        'rovor-fast-free-v1',
        ('openrouter/cohere/north-mini-code:free',
         'openrouter/nvidia/nemotron-3.5-super-vl:free')),
    'supervisor-resilience': (
        'rovor-code-free-v1',
        ('openrouter/cohere/north-mini-code:free',
         'openrouter/nvidia/nemotron-3-ultra-550b-a55b:free')),
    'provider-efficiency': (
        'rovor-reason-free-v1',
        ('openrouter/nvidia/nemotron-3-ultra-550b-a55b:free',
         'openrouter/nvidia/nemotron-3.5-super-vl:free')),
}
MAX_24H = 5


def validate_payload(payload):
    if (not isinstance(payload, dict) or set(payload) != {'packet'}
            or not isinstance(payload['packet'], str)
            or payload['packet'] not in ROUTES):
        raise ValueError('OmniRoute jobs require one known public research packet')
    return payload['packet']


def read_combo_catalog(run=subprocess.run):
    """Consult installed CLI without making an inference request.

    The CLI prints informational lines before JSON on some machines; parse
    exactly the JSON object in stdout, reject errors and unknown shapes.
    Never expose CLI errors or stdout, which may contain private metadata.
    """
    try:
        p = run(['omniroute', 'combo', 'list', '--json'], capture_output=True,
                text=True, timeout=15, check=False)
        if p.returncode or not isinstance(p.stdout, str):
            raise ValueError('OmniRoute route catalog unavailable')
        start = p.stdout.find('{')
        if start < 0 or len(p.stdout) > 300000:
            raise ValueError('OmniRoute route catalog unavailable')
        parsed = json.loads(p.stdout[start:])
        if not isinstance(parsed, dict) or not isinstance(parsed.get('combos'), list):
            raise ValueError('OmniRoute route catalog malformed')
        return parsed['combos']
    except (OSError, ValueError, subprocess.TimeoutExpired):
        raise ValueError('OmniRoute route catalog unavailable') from None


def verify_route(packet, catalog):
    name, expected = ROUTES[packet]
    matching = [x for x in catalog if isinstance(x, dict) and x.get('name') == name]
    if len(matching) != 1:
        raise ValueError('Expected ROVOR free-only route missing or duplicated')
    entry = matching[0]
    if entry.get('strategy') != 'priority' or entry.get('isHidden') is not False:
        raise ValueError('ROVOR routing configuration changed')
    models = entry.get('models')
    if not isinstance(models, list) or len(models) != len(expected):
        raise ValueError('ROVOR free-only models changed')
    actual = []
    for model in models:
        if (not isinstance(model, dict) or model.get('kind') != 'model'
                or model.get('providerId') != 'openrouter'
                or not isinstance(model.get('model'), str)
                or not model['model'].endswith(':free')):
            raise ValueError('Non-free or unknown OmniRoute fallback blocked')
        actual.append(model['model'])
    if tuple(actual) != expected:
        raise ValueError('ROVOR free-only model order changed')
    return name


def execute(state, job_id, payload, *, stop_path=None, catalog=None):
    """Save one private, review-required draft; never self-approve it."""
    packet = validate_payload(payload)
    if not isinstance(job_id, str) or len(job_id) != 36:
        raise ValueError('Invalid SQLite OmniRoute job identifier')
    if catalog is None:
        catalog = read_combo_catalog()
    route = verify_route(packet, catalog)
    stop = Path(stop_path) if stop_path is not None else Path(state) / 'STOP'
    if os.path.lexists(stop):
        raise ValueError('STOP requested before OmniRoute inference')
    root = Path(__file__).resolve().parent.parent
    out = Path(state).resolve() / 'omniroute-drafts' / job_id
    # Neither this adapter nor a future imported caller may write a private
    # model draft into an ancestor public Git checkout.
    for source in (root, *root.parents):
        if (source / '.git').exists() or (source / '.git').is_symlink():
            if out == source or source in out.parents:
                raise ValueError('Private draft destination must be outside Git checkout')
    if out == root or root in out.parents:
        raise ValueError('Private draft destination must be outside source tree')
    try:
        import omniroute_workpack_runner as workpack
        import omniroute_draft_review as review
        if os.path.lexists(stop):
            raise ValueError('STOP requested before OmniRoute inference')
        key = workpack.access_key()
        result = workpack.run_packet(root, out, packet, route, key)
        verdict = review.inspect(root, out, packet)
        status = result.get('status')
        return {'packet': packet, 'route': route,
                'draft_status': status,
                'review_status': verdict['status'],
                'receipt': str(out / (packet + '.receipt.json')),
                'user_review_required': True,
                'facts_verified': False,
                'mac_app_control_verified': False}
    except (ImportError, OSError, ValueError, KeyError, TypeError):
        # Do not persist upstream errors or arbitrary provider response data
        # in the SQLite worker's world-readable status channel.
        raise ValueError('OmniRoute draft requires private review; no automatic retry') from None
