"""Source-faithful production continuity ledger for repeatable Rovor episodes.

The ledger records which *frames* have review coverage, exactly which revision
edited those frames, and which creative gates are still outstanding. It never
claims a source video exists solely because a manifest says so. Library files
stay private; this code and the reviewed hashes can safely live in GitHub.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SIZES = {"landscape": [1920, 1080], "portrait": [1080, 1920]}


class LedgerError(ValueError):
    """The ledger is incomplete, contradictory, or falsely approved."""


def source_hash(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def check_frame_pair(pair, bound, label):
    if not isinstance(pair, list) or len(pair) != 2 or any(type(x) is not int for x in pair):
        raise LedgerError(f"{label}: expected integer [start,endExclusive] frame pair")
    a, b = pair
    if a < 0 or b <= a or b > bound:
        raise LedgerError(f"{label}: invalid frame interval {pair} (bound {bound})")
    return a, b


def validate(ledger, *, source=None, archives=None):
    """Return evidence-backed status; never approve artwork or publication.

    `archives` maps source ZIP *filenames* to real local paths, optional in
    repo-only mode. If supplied, validate actual archive bytes, not names.
    """
    if not isinstance(ledger, dict):
        raise LedgerError('Ledger must be an object')
    project = ledger.get('project_id')
    if not isinstance(project, str) or not re.fullmatch('[a-z0-9][a-z0-9-]{3,80}', project):
        raise LedgerError('Invalid stable project_id')
    meta = ledger.get('original_audio')
    if not isinstance(meta, dict) or not isinstance(meta.get('sha256'), str) or not HEX64.fullmatch(meta['sha256']):
        raise LedgerError('Exact original audio SHA256 required')
    dur = meta.get('duration_seconds')
    if isinstance(dur, bool) or not isinstance(dur, (int, float)) or not math.isfinite(dur) or not 30 <= dur <= 3600:
        raise LedgerError('Invalid original narration duration')
    fps = ledger.get('fps')
    if type(fps) is not int or fps != 60:
        raise LedgerError('Rovor release timeline must be 60 fps')
    if ledger.get('orientations') != SIZES:
        raise LedgerError('Both native 1080p orientations must be listed')
    final_frame_count = math.ceil(dur * fps - 1e-8)
    if ledger.get('total_source_frames') != final_frame_count:
        raise LedgerError('Total source frames mismatch; final partial audio frame counts')
    revs = ledger.get('revisions')
    if not isinstance(revs, list) or not revs:
        raise LedgerError('At least one real revision required')
    seen = set()
    last_end = 0
    for i, rev in enumerate(revs):
        if not isinstance(rev, dict):
            raise LedgerError('Revisions must be objects')
        name = rev.get('revision')
        if not isinstance(name, str) or not re.fullmatch(r'v[0-9]+', name) or name in seen:
            raise LedgerError('Missing, duplicate, or invalid revision ID')
        seen.add(name)
        a, b = check_frame_pair(rev.get('review_coverage'), final_frame_count, f'{name}.review_coverage')
        if a != 0 or b < last_end:
            raise LedgerError(f'{name}: coverage must start at 0 and cannot regress')
        edit = rev.get('edited_intervals')
        if not isinstance(edit, list) or not edit:
            raise LedgerError(f'{name}: no real edited intervals')
        intervals = [check_frame_pair(p, b, f'{name}.edited_intervals') for p in edit]
        if any(x[0] < prev[1] for prev, x in zip(intervals, intervals[1:])):
            raise LedgerError(f'{name}: edits overlap or are out of order')
        # Any newly covered audio must have actual new visual editing.
        if b > last_end and not any(x[0] <= last_end and x[1] >= b for x in intervals):
            covered = last_end
            for x, y in intervals:
                if x <= covered:
                    covered = max(covered, y)
            if covered < b:
                raise LedgerError(f'{name}: unsupported new-coverage claim [{covered},{b})')
        digest = rev.get('editable_archive_sha256')
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise LedgerError(f'{name}: original editable archive SHA256 missing')
        archive_name = rev.get('editable_archive')
        if not isinstance(archive_name, str) or '/' in archive_name or '\\' in archive_name or not archive_name.endswith('.zip'):
            raise LedgerError(f'{name}: private source ZIP filename required (no path)')
        if rev.get('artist_approved') is not False or rev.get('publication_approved') is not False:
            raise LedgerError(f'{name}: artistic/publication approval must remain explicitly false')
        if archives is not None and archive_name in archives:
            p = Path(archives[archive_name])
            if not p.is_file() or source_hash(p) != digest:
                raise LedgerError(f'{name}: editable source archive hash failed')
        last_end = b
    if source is not None:
        p = Path(source)
        if not p.is_file() or source_hash(p) != meta['sha256']:
            raise LedgerError('Wrong, missing or changed original narration')
    if ledger.get('current_revision') != revs[-1]['revision']:
        raise LedgerError('Current revision not latest')
    if ledger.get('human_visual_review_approved') is not False or ledger.get('publication_approved') is not False:
        raise LedgerError('Technical coverage must not be represented as creative release approval')
    return {
        'project_id': project,
        'current_revision': revs[-1]['revision'],
        'review_coverage_frames': last_end,
        'review_coverage_seconds': round(last_end / fps, 6),
        'source_duration_seconds': dur,
        'remaining_source_seconds': round(dur - last_end / fps, 6),
        'remaining_source_frames': final_frame_count - last_end,
        'coverage_fraction': round(min(1, last_end / (fps * dur)), 6),
        'next_start_frame': last_end,
        'source_hash_verified': source is not None,
        'archive_hashes_verified': sorted(k for k in (archives or {}) if k in {x['editable_archive'] for x in revs}),
        'technical_video_verified_from_media': False,
        'artistic_approval': False,
        'publication_approved': False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('--original-audio', type=Path)
    p.add_argument('--archive', action='append', type=Path, default=[], help='Optional private source zip to SHA-verify by basename')
    p.add_argument('--json-out', type=Path)
    args = p.parse_args()
    try:
        archives = {f.name: f for f in args.archive}
        if len(archives) != len(args.archive):
            raise LedgerError('Duplicate archive filenames')
        report = validate(json.loads(args.ledger.read_text()), source=args.original_audio, archives=archives)
    except (LedgerError, json.JSONDecodeError, OSError) as e:
        p.exit(status=2, message=f'CONTINUITY_LEDGER=REJECTED: {e}\n')
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    print('CONTINUITY_LEDGER=VALIDATED_NOT_ARTISTICALLY_APPROVED')


if __name__ == '__main__':
    main()