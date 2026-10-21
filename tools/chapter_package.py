#!/usr/bin/env python3
"""Prepare private, sample-exact chapter WAVs and English phone plans for Moho.

Consumes the verified longform_chapters schema v1. No resampling, MP3 editing,
networking, shell execution, made-up phonemes, native .moho files or rendering.
The complete original PCM payload must equal concatenated chapter PCM bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import wave

from longform_chapters import (_reject_constant, _unique_pairs, plan_chapters,
                               SAMPLE_RATE, FPS)
from speech_plan_gate import audit as acoustic_audit

MAX_METADATA_BYTES = 8 * 1024 * 1024
PCM_WIDTH = 2


def load_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("Invalid, symlinked or oversized metadata")
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=_reject_constant, object_pairs_hook=_unique_pairs)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_new(path, data):
    with path.open("xb") as out:
        out.write(data)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def json_bytes(data):
    return (json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)
            + "\n").encode("utf-8")


def _local_rows(rows, indices, source_sample, sample_count, index_map):
    """Shift only acoustic times, keeping original phone/viseme metadata."""
    offset = source_sample / SAMPLE_RATE
    duration = sample_count / SAMPLE_RATE
    result = []
    for row in rows:
        if row["scriptIndex"] not in index_map:
            continue
        new = dict(row)
        for side in ("start", "end"):
            local = round(float(row[side]) - offset, 8)
            if -1e-6 < local < 0:
                local = 0.
            if not -1e-6 <= local <= duration + 1e-6:
                raise ValueError("Acoustic event crosses chapter boundary: " + str(row["scriptIndex"]))
            new[side] = max(0., min(duration, local))
        if not new["start"] < new["end"]:
            raise ValueError("Zero-duration acoustic event in chapter")
        new["scriptIndex"] = index_map[row["scriptIndex"]]
        result.append(new)
    return result


def _local_silences(silences, source_sample, sample_count):
    offset = source_sample / SAMPLE_RATE
    stop = (source_sample + sample_count) / SAMPLE_RATE
    result = []
    for silence in silences:
        start = max(offset, float(silence["start"]))
        end = min(stop, float(silence["end"]))
        if end <= start:
            continue
        local = dict(silence)
        local["start"], local["end"] = (round(start - offset, 8),
                                         round(end - offset, 8))
        result.append(local)
    return result


def local_speech(plan, row, number):
    """Return an independently gated, per-chapter plan.

    The chapter frame origin and audio sample offset differ by <= 0.5 PCM
    sample. Acoustic timestamps follow audio samples, not guessed Moho frames.
    """
    off, count = row["startSample"], row["sampleCount"]
    start = off / SAMPLE_RATE
    end = (off + count) / SAMPLE_RATE
    included = [w for w in plan["words"]
                if float(w["start"]) >= start - 1e-6
                and float(w["end"]) <= end + 1e-6]
    index_map = {w["scriptIndex"]: i for i, w in enumerate(included)}
    if not included or len(index_map) != len(included):
        raise ValueError("Chapter has no complete distinct acoustic words")
    for word in plan["words"]:
        if word["scriptIndex"] not in index_map and (
            start + 1e-6 < float(word["end"]) and
            float(word["start"]) < end - 1e-6):
            raise ValueError("Cut passes through aligned word")
    for phone in plan["phonemes"]:
        if phone["scriptIndex"] not in index_map and (
            start + 1e-6 < float(phone["end"]) and
            float(phone["start"]) < end - 1e-6):
            raise ValueError("Cut passes through aligned phone")
    words = _local_rows(plan["words"], included, off, count, index_map)
    phones = _local_rows(plan["phonemes"], included, off, count, index_map)
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", plan["script"].lower())
    script = " ".join(tokens[w["scriptIndex"]] for w in included)
    local = {
        "script": script,
        "alignment": dict(plan["alignment"]),
        "words": words,
        "phonemes": phones,
        "silences": _local_silences(plan.get("silences", []), off, count)
    }
    qa = acoustic_audit(local, count / SAMPLE_RATE, FPS, wav_header_checked=True)
    if qa["status"] != "technical_pass_pending_visual_review":
        raise ValueError("Chapter-local acoustic QA not clear (chapter " +
                         str(number) + "): " + str(qa["errors"] or qa["reviewFlags"])[:450])
    return local


def package(wav_path, plan_path, manifest_path, destination):
    wav_path, plan_path = Path(wav_path), Path(plan_path)
    manifest_path, destination = Path(manifest_path), Path(destination)
    if (any(p.is_symlink() or not p.is_file() for p in
            (wav_path, plan_path, manifest_path))):
        raise ValueError("Missing or symlinked original source or plan")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Output directory already exists; never overwrite chapters")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("Output parent must already exist and not be a symlink")
    verified = plan_chapters(wav_path, plan_path)
    declared = load_json(manifest_path)
    if declared != verified:
        raise ValueError("Chapter manifest differs from independently verified original inputs")
    original_plan = load_json(plan_path)
    chapters = verified["chapters"]
    # Preflight all events before writing any files, so a late alignment error
    # does not leave a misleading completed package on disk.
    per_chapter = [local_speech(original_plan, row, row["index"]) for row in chapters]
    wav_hash = hashlib.sha256()
    packed_hash = hashlib.sha256()
    index = []
    wrote_destination = False
    try:
        destination.mkdir(mode=0o700, exist_ok=False)
        wrote_destination = True
        with wave.open(str(wav_path), "rb") as reader:
            for row, speech in zip(chapters, per_chapter):
                index_no = row["index"]
                folder = destination / ("chapter-%03d" % index_no)
                folder.mkdir(mode=0o700)
                dest_audio = folder / "narration.wav"
                samples = row["sampleCount"]
                reader.setpos(row["startSample"])
                with wave.open(str(dest_audio), "wb") as wav:
                    wav.setparams((1, PCM_WIDTH, SAMPLE_RATE, 0, "NONE", "not compressed"))
                    pending = samples
                    chapter_pcm = hashlib.sha256()
                    while pending:
                        n = min(pending, 65536)
                        data = reader.readframes(n)
                        if len(data) != n * PCM_WIDTH:
                            raise ValueError("Truncated PCM while extracting original chapter")
                        wav.writeframesraw(data)
                        chapter_pcm.update(data)
                        packed_hash.update(data)
                        pending -= n
                    wav.writeframes(b"")
                try:
                    dest_audio.chmod(0o600)
                except OSError:
                    pass
                speech_data = json_bytes(speech)
                write_new(folder / "acoustic-plan.json", speech_data)
                chapter_evidence = {
                    "schemaVersion": 1, "chapterIndex": index_no,
                    "sourceWavSha256": verified["sourceWavSha256"],
                    "sourceSpeechPlanSha256": verified["sourceSpeechPlanSha256"],
                    "chapterPlan": row,
                    "narrationWavSha256": hashlib.sha256(dest_audio.read_bytes()).hexdigest(),
                    "narrationPcmSha256": chapter_pcm.hexdigest(),
                    "speechPlanSha256": digest(speech_data),
                    "localMohoFirstFrame": 1,
                    "localMohoLastFrame": row["frameCount"],
                    "nativeMohoRendered": False,
                    "visualApproval": False
                }
                write_new(folder / "chapter.json", json_bytes(chapter_evidence))
                index.append({
                    "chapterIndex": index_no,
                    "directory": folder.name,
                    "narrationPcmSha256": chapter_pcm.hexdigest(),
                    "narrationWavSha256": chapter_evidence["narrationWavSha256"],
                    "speechPlanSha256": chapter_evidence["speechPlanSha256"],
                    "frameCount": row["frameCount"],
                    "sampleCount": samples
                })
            # Stream the original a second time instead of trusting source
            # metadata; raw PCM equality with every packaged part is mandatory.
            reader.rewind()
            remaining = verified["sourceSamples"]
            while remaining:
                take = min(remaining, 65536)
                data = reader.readframes(take)
                if len(data) != take * PCM_WIDTH:
                    raise ValueError("Source PCM unexpectedly truncated during final verification")
                wav_hash.update(data)
                remaining -= take
        if packed_hash.digest() != wav_hash.digest():
            raise ValueError("Packaged PCM does not reconstruct original sample bytes")
        if verified["sourceWavSha256"] != hashlib.sha256(wav_path.read_bytes()).hexdigest():
            raise ValueError("Original source WAV mutated during package creation")
        report = {
            "schemaVersion": 1,
            "status": "private_chapter_payloads_created_pending_native_render",
            "sourceWavSha256": verified["sourceWavSha256"],
            "sourceSpeechPlanSha256": verified["sourceSpeechPlanSha256"],
            "chapterManifestSha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "originalPcmSha256": wav_hash.hexdigest(),
            "reassembledChapterPcmSha256": packed_hash.hexdigest(),
            "audioSampleCount": verified["sourceSamples"],
            "totalVideoFrames": verified["totalFrames"],
            "fps": FPS,
            "chapterCount": len(index),
            "chapters": index,
            "nativeMohoRendered": False,
            "audioMuxed": False,
            "artisticApproval": False,
            "publishable": False
        }
        # The bundle ledger is committed LAST. Missing ledger means incomplete.
        write_new(destination / "bundle.json", json_bytes(report))
        return report
    except BaseException:
        if wrote_destination:
            shutil.rmtree(destination)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--chapters", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = package(args.wav, args.plan, args.chapters, args.out)
        print(json.dumps({key: result[key] for key in
                          ("status", "chapterCount", "audioSampleCount", "totalVideoFrames")},
                         indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError, wave.Error) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
