#!/usr/bin/env python3
"""Plan 60fps, <=60s native Moho *candidate chapters* without altering narration.

Inputs are the original source-derived mono 16kHz PCM16 WAV and the existing
reviewed English phoneme plan. This is a planning-only stage for the draft
longform adapter, NOT a longer MP3 intake, WAV cutter, Moho rig or renderer.
No guessed word cuts, silent fallback, network access, or model dependency.
"""
from __future__ import annotations

import argparse
from bisect import bisect_left
from hashlib import sha256
import json
import math
from pathlib import Path
import sys
import wave

from speech_plan_gate import audit as acoustic_audit

SAMPLE_RATE = 16000
FPS = 60
MAX_TOTAL_SECONDS = 900
MAX_CHAPTER_FRAMES = 3600
TARGET_CHAPTER_FRAMES = 2700
MIN_CHAPTER_FRAMES = 900
CUT_MARGIN_SECONDS = 0.012


def _reject_constant(value):
    raise ValueError("Nonfinite JSON constant: " + value)


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field: " + key)
        result[key] = value
    return result


def source_hash(path):
    result = sha256()
    with Path(path).open("rb") as reader:
        for block in iter(lambda: reader.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def pcm_samples(path):
    """Verify all claimed WAV samples are present; never trust a header alone."""
    with wave.open(str(path), "rb") as stream:
        if (stream.getnchannels(), stream.getsampwidth(),
                stream.getframerate(), stream.getcomptype()) != (1, 2, SAMPLE_RATE, "NONE"):
            raise ValueError("Source must be uncompressed mono 16kHz PCM16 WAV")
        n = stream.getnframes()
        if not 0 < n <= MAX_TOTAL_SECONDS * SAMPLE_RATE:
            raise ValueError("Source narration duration must be within 15 minutes")
        remaining = n
        while remaining:
            count = min(65536, remaining)
            if len(stream.readframes(count)) != count * 2:
                raise ValueError("Truncated source WAV data")
            remaining -= count
    return n


def frames_for_samples(samples):
    # A video frame starts at n / 60. Need enough frames to cover every PCM
    # sample without looping, padding, or shortening the original WAV.
    return (samples * FPS + SAMPLE_RATE - 1) // SAMPLE_RATE


def samples_at_frame(frame, total_samples):
    if type(frame) is not int or frame < 0:
        raise ValueError("Invalid frame boundary")
    # Exact integer round-to-nearest: individual chapters may differ by one
    # audio sample at a boundary, but concatenation never loses/repeats samples.
    return min(total_samples, (frame * SAMPLE_RATE * 2 + FPS) // (2 * FPS))


def _cut_candidates(plan, total_frames):
    words = plan["words"]
    phones = plan["phonemes"]
    candidates = {}
    # Only between *complete adjacent words*, never inside a word/phone.
    for before, after in zip(words, words[1:]):
        left = float(before["end"])
        right = float(after["start"])
        first = math.ceil((left + CUT_MARGIN_SECONDS) * FPS)
        last = math.floor((right - CUT_MARGIN_SECONDS) * FPS)
        if first > last:
            continue
        cut = max(first, min(last, round((left + right) * FPS / 2)))
        if not 0 < cut < total_frames:
            continue
        t = cut / FPS
        if any(float(phone["start"]) - CUT_MARGIN_SECONDS < t <
               float(phone["end"]) + CUT_MARGIN_SECONDS for phone in phones):
            continue
        candidates.setdefault(cut, {
            "afterWordIndex": before["scriptIndex"],
            "beforeWordIndex": after["scriptIndex"],
            "betweenWordsSeconds": round(right - left, 6),
            "cutFrame": cut,
        })
    return candidates


def _choose_boundaries(total_frames, candidates):
    if total_frames <= MAX_CHAPTER_FRAMES:
        return [0, total_frames]
    ends = [0] + sorted(candidates) + [total_frames]
    best_cost = [math.inf] * len(ends)
    previous = [-1] * len(ends)
    chapter_counts = [0] * len(ends)
    best_cost[0] = 0
    for i in range(1, len(ends)):
        for j in range(i - 1, -1, -1):
            frames = ends[i] - ends[j]
            if frames > MAX_CHAPTER_FRAMES:
                break
            if frames < MIN_CHAPTER_FRAMES or not math.isfinite(best_cost[j]):
                continue
            cost = best_cost[j] + (frames - TARGET_CHAPTER_FRAMES) ** 2
            count = chapter_counts[j] + 1
            if cost < best_cost[i] or (cost == best_cost[i] and count < chapter_counts[i]):
                best_cost[i], previous[i], chapter_counts[i] = cost, j, count
    if previous[-1] == -1:
        raise ValueError(
            "No safe 60fps word-boundary chapter plan: an interval exceeds 60 seconds "
            "or would require cutting inside speech; review actual acoustic gaps"
        )
    indices = []
    current = len(ends) - 1
    while current >= 0:
        indices.append(current)
        current = previous[current]
    return [ends[i] for i in reversed(indices)]


def plan_chapters(wav_path, speech_plan_path):
    wav_path, speech_plan_path = Path(wav_path), Path(speech_plan_path)
    samples = pcm_samples(wav_path)
    plan_bytes = speech_plan_path.read_bytes()
    plan = json.loads(plan_bytes, parse_constant=_reject_constant,
                      object_pairs_hook=_unique_pairs)
    duration = samples / SAMPLE_RATE
    qa = acoustic_audit(plan, duration, FPS, wav_header_checked=True)
    if qa["status"] != "technical_pass_pending_visual_review":
        raise ValueError("Acoustic plan is not reviewed and clear: " +
                         json.dumps({"status": qa["status"],
                                     "errors": qa["errors"],
                                     "reviewFlags": qa["reviewFlags"]})[:800])
    total_frames = frames_for_samples(samples)
    candidates = _cut_candidates(plan, total_frames)
    boundaries = _choose_boundaries(total_frames, candidates)
    chapters = []
    for index, (start, end) in enumerate(zip(boundaries, boundaries[1:])):
        a = samples_at_frame(start, samples)
        b = samples_at_frame(end, samples)
        if not 0 <= a < b <= samples or not 0 < end - start <= MAX_CHAPTER_FRAMES:
            raise ValueError("Internal chapter range/PCM continuity error")
        chapters.append({
            "index": index,
            "startFrame": start,
            "endFrameExclusive": end,
            "frameCount": end - start,
            "startSample": a,
            "endSampleExclusive": b,
            "sampleCount": b - a,
            "durationSeconds": round((b - a) / SAMPLE_RATE, 6),
            "cutBefore": None if index == 0 else candidates[start],
        })
    if (not chapters or chapters[0]["startSample"] != 0 or
            chapters[-1]["endSampleExclusive"] != samples or
            any(a["endFrameExclusive"] != b["startFrame"] or
                a["endSampleExclusive"] != b["startSample"]
                for a, b in zip(chapters, chapters[1:])) or
            sum(c["sampleCount"] for c in chapters) != samples or
            sum(c["frameCount"] for c in chapters) != total_frames):
        raise ValueError("Source continuity invariants failed")
    return {
        "schemaVersion": 1,
        "status": "technical_chapter_plan_pending_native_and_artistic_review",
        "sourceWavSha256": source_hash(wav_path),
        "sourceSpeechPlanSha256": sha256(plan_bytes).hexdigest(),
        "fps": FPS,
        "sourceSampleRate": SAMPLE_RATE,
        "sourceSamples": samples,
        "originalDurationSeconds": round(duration, 6),
        "totalFrames": total_frames,
        "chapterCount": len(chapters),
        "chapters": chapters,
        "provenance": "fully read source PCM and acoustically reviewed word/phone plan",
        "completeSourceSampleCoverage": True,
        "cutsOnlyBetweenReviewedWords": True,
        "sourceAudioEdited": False,
        "audioChunksWritten": False,
        "nativeMohoRendered": False,
        "artisticApproval": False,
        "publicationApproved": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--out", type=Path, help="Create new JSON manifest; never overwrite")
    args = parser.parse_args(argv)
    try:
        manifest = plan_chapters(args.wav, args.plan)
        content = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as output:
                output.write(content)
        else:
            print(content, end="")
        return 0
    except (OSError, KeyError, ValueError, TypeError, wave.Error) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
