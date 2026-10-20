#!/usr/bin/env python3
"""Cheap, read-only QA for *acoustically aligned* English phone animation plans.

Vendored from main tools/speech_plan_gate.py for the isolated PR #5 acting branch.\nConsumes the established PR #5 speech-plan schema; does not transcribe, render,
change audio, overwrite plans, or claim that mouth motion is visually approved.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import wave

# Existing english_articulation.PHONE_CATALOG first target at the PR #5 checkpoint.
# This contract is pinned intentionally: a future catalog change requires review.
PHONE_TO_SHAPE = {
    'AA':'D','AE':'D','AH':'C','AO':'E','AW':'D','AY':'C','EH':'C',
    'ER':'C','EY':'C','IH':'B','IY':'B','OW':'E','OY':'E','UH':'F','UW':'F',
    'B':'A','CH':'B','D':'B','DH':'H','F':'G','G':'B','HH':'C',
    'JH':'B','K':'B','L':'H','M':'A','N':'B','NG':'B','P':'A',
    'R':'B','S':'B','SH':'B','T':'B','TH':'H','V':'G',
    'W':'F','Y':'B','Z':'B','ZH':'B',
}
VOWELS = set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split())
CONTACTS = {'B', 'M', 'P', 'F', 'V', 'TH', 'DH', 'L'}
PHONE_PATTERN = re.compile(r'^([A-Z]+)([012]?)$')


def numeric(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float))
            and math.isfinite(value))


def bounds(row, duration, label, errors, tolerance=0.03):
    if not isinstance(row, dict):
        errors.append(label + ': expected object')
        return None
    a, b = row.get('start'), row.get('end')
    if not numeric(a) or not numeric(b) or not 0 <= a < b <= duration + tolerance:
        errors.append(label + ': invalid or out-of-recording time interval')
        return None
    return float(a), float(b)


def frames_sampled(a, b, fps):
    """Frame start samples at 0, 1/fps ... before the interval end."""
    return max(0, math.ceil(b * fps - 1e-9) - math.ceil(a * fps - 1e-9))


def audit(plan, duration, fps=60, wav_header_checked=False):
    if not numeric(duration) or not 0 < duration <= 3600:
        raise ValueError('Duration must be finite positive seconds, at most one hour')
    if type(fps) is not int or fps not in (24, 30, 48, 60, 120):
        raise ValueError('Choose a supported whole-number frame rate')
    if not isinstance(plan, dict):
        raise ValueError('Speech plan must be a JSON object')

    errors, flags = [], []
    align = plan.get('alignment')
    if not isinstance(align, dict) or align.get('status') != 'acoustic':
        errors.append('No verified-acoustic-source plan: estimates/Rhubarb mouth shapes are not phoneme timing')
    if not isinstance(align, dict) or align.get('wordCoverage') != 1.0:
        errors.append('Acoustic word coverage not confirmed complete')

    words = plan.get('words')
    phones = plan.get('phonemes')
    if not isinstance(words, list) or not words or not isinstance(phones, list) or not phones:
        errors.append('Nonempty words and phonemes arrays are required')
        words = words if isinstance(words, list) else []
        phones = phones if isinstance(phones, list) else []
    script = plan.get('script')
    scripted = re.findall(r"[a-z]+(?:'[a-z]+)?", script.lower()) if isinstance(script, str) else []
    if not scripted:
        errors.append('Missing reviewed English script; cannot reconcile phoneme words')
    elif len(scripted) != len(words):
        errors.append('Script word count and acoustically aligned words disagree')
    word_times = {}
    previous_start = -1.0
    previous_word_end = -1.0
    previous_word = -1
    for i, word in enumerate(words):
        label = 'word[%d]' % i
        t = bounds(word, duration, label, errors)
        if t is None:
            continue
        index = word.get('scriptIndex')
        if type(index) is not int or index != i or index <= previous_word:
            errors.append(label + ': missing or noncontiguous scriptIndex')
            continue
        previous_word = index
        if t[0] < previous_start - .02:
            errors.append(label + ': word time moves backwards')
        if i and t[0] < previous_word_end - .025:
            errors.append(label + ': acoustic word overlaps previous word')
        previous_start, previous_word_end = t
        if not isinstance(word.get('word'), str) or not word['word'].strip():
            errors.append(label + ': missing spoken word')
        elif i < len(scripted) and str(word['word']).lower() != scripted[i]:
            errors.append(label + ': recognized word differs from corrected script')
        word_times[index] = (t[0], t[1], str(word.get('word', '')).lower())
        if word.get('reviewFlags'):
            flags.append({'type':'unreviewed-acoustic-word', 'wordIndex':index,
                          'details':word['reviewFlags']})

    previous_end = 0.
    counts = {index:0 for index in word_times}
    shape_counts, missed_contacts = {}, []
    for i, phone in enumerate(phones):
        label = 'phone[%d]' % i
        t = bounds(phone, duration, label, errors)
        if t is None:
            continue
        a, b = t
        raw = phone.get('phone')
        matched = PHONE_PATTERN.fullmatch(raw) if isinstance(raw, str) else None
        base = matched.group(1) if matched else ''
        suffix = matched.group(2) if matched else ''
        if base not in PHONE_TO_SHAPE or (suffix and base not in VOWELS):
            errors.append(label + ': unsupported phoneme; spelling/letters are not audio phones: ' + str(raw))
            continue
        expected = PHONE_TO_SHAPE[base]
        if phone.get('value') != expected:
            errors.append(label + ': wrong first viseme for ' + raw + ' (expected ' + expected + ')')
        index = phone.get('scriptIndex')
        if type(index) is not int or index not in word_times:
            errors.append(label + ': absent or unknown word scriptIndex')
            continue
        counts[index] += 1
        x, y, word = word_times[index]
        if a < x - .035 or b > y + .035:
            errors.append(label + ': phone timing exceeds acoustic word bounds')
        if str(phone.get('word', '')).lower() != word:
            errors.append(label + ': phone and word identity differ')
        if a < previous_end - .025:
            errors.append(label + ': overlapping or unsorted acoustic phones')
        if a > previous_end + .20 and i:
            flags.append({'type':'phone-gap-needs-rest-review','start':round(previous_end,5),
                          'end':round(a,5)})
        previous_end = max(previous_end, b)
        shape_counts[expected] = shape_counts.get(expected, 0) + 1
        sampled = frames_sampled(a, min(b, duration), fps)
        if sampled == 0:
            entry = {'type':'unsampled-contact' if base in CONTACTS else 'unsampled-phone',
                     'phoneIndex':i,'phone':raw,'start':a,'end':b,'fps':fps}
            flags.append(entry)
            if base in CONTACTS:
                missed_contacts.append(i)
    for index, count in counts.items():
        if count == 0:
            errors.append('word scriptIndex %d has no usable acoustic phones' % index)
    for i, item in enumerate(plan.get('silences', [])):
        if bounds(item, duration, 'silence[%d]' % i, errors) is None:
            continue
    return {
        'status':'blocked' if errors else 'review_required' if flags else 'technical_pass_pending_visual_review',
        'alignmentSource': 'acoustic' if isinstance(align, dict) and align.get('status') == 'acoustic' else 'unverified',
        'provenance':'source-WAV header read' if wav_header_checked else 'operator-supplied duration; WAV unchecked',
        'fps':fps,'durationSeconds':round(duration,6),'wordCount':len(words),
        'phoneCount':len(phones),'firstTargetCounts':shape_counts,
        'unsampledContactCount':len(missed_contacts),'errors':errors,'reviewFlags':flags,
        'artisticApproval':False,'narrationPreserved':True,'published':False,
        'note':'Technical metadata review only; exact articulation needs rendered mouth, original audio, and a human listening/visual pass.'
    }


def wav_duration(path):
    with wave.open(str(path), 'rb') as f:
        if (f.getframerate(), f.getnchannels(), f.getsampwidth()) != (16000, 1, 2):
            raise ValueError('Expect source-derived 16kHz mono PCM16 WAV for duration verification')
        return f.getnframes() / f.getframerate()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', type=Path, required=True)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument('--wav', type=Path, help='read exact duration from source-derived 16k PCM16 WAV')
    source.add_argument('--duration', type=float, help='duration metadata only; NOT source-audio verified')
    p.add_argument('--fps', type=int, default=60)
    p.add_argument('--out', type=Path, help='optional standalone read-only report destination')
    args = p.parse_args(argv)
    try:
        plan = json.loads(args.plan.read_text(encoding='utf-8'))
        duration = wav_duration(args.wav) if args.wav else args.duration
        report = audit(plan, duration, args.fps, wav_header_checked=bool(args.wav))
        report['planSha256'] = hashlib.sha256(args.plan.read_bytes()).hexdigest()
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            temp = args.out.with_suffix(args.out.suffix + '.partial')
            temp.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            temp.replace(args.out)
        print(json.dumps(report, indent=2))
        return 1 if report['status'] == 'blocked' else 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, wave.Error) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
