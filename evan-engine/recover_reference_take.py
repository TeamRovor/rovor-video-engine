"""Recover the *actual* 22 s Evan favicon take from an authorized V3 handoff.

This is a provenance/acoustic-inspection tool, not a forced aligner or animation
renderer. It deliberately does NOT certify any phoneme boundary or artwork.

Example:
    python recover_reference_take.py Evan-Engine-V3-Reference-Art.zip /tmp/evan-real-take \\
        --expected-scene-git-sha cc00782e6f4c72800e0be5962647e389a172519a

The MP3 and decoded WAV remain local. Only the non-sensitive JSON report should
be committed to Git. Never copy this voice recording to a public repository.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave
from zipfile import ZipFile

import numpy as np

AUDIO_MEMBER = "evan-character/evan-original-extracted.mp3"
SCENE_MEMBER = "evan-character/scene.json"
KNOWN_SCENE_BLOB = "cc00782e6f4c72800e0be5962647e389a172519a"
CUE_SYMBOLS = set("XABCDEFGH")


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode("ascii") + b"\0" + content).hexdigest()


def load_source(handoff_zip: Path) -> tuple[bytes, bytes]:
    with ZipFile(handoff_zip) as z:
        for name in (AUDIO_MEMBER, SCENE_MEMBER):
            if z.namelist().count(name) != 1:
                raise ValueError(f"Expected exactly one {name} in {handoff_zip.name}")
        # read() checks the member's CRC and avoids unsafe extraction paths.
        return z.read(AUDIO_MEMBER), z.read(SCENE_MEMBER)


def decode_pcm(mp3: bytes, wav_path: Path, ffmpeg: str = "ffmpeg") -> tuple[np.ndarray, bytes]:
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    temp_mp3 = wav_path.with_suffix(".source.mp3")
    temp_mp3.write_bytes(mp3)
    try:
        proc = subprocess.run(
            [ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i",
             str(temp_mp3), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(wav_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=45,
        )
        if proc.returncode:
            raise RuntimeError("FFmpeg decode failed: " + proc.stderr.decode("utf-8", "replace")[-500:])
    finally:
        temp_mp3.unlink(missing_ok=True)
    with wave.open(str(wav_path), "rb") as w:
        if w.getnchannels() != 1 or w.getframerate() != 16000 or w.getsampwidth() != 2:
            raise ValueError("Decoder did not produce mono 16kHz PCM16")
        data = w.readframes(w.getnframes())
    samples = np.frombuffer(data, dtype="<i2").copy()
    return samples, data


def rms_dbfs(samples: np.ndarray) -> float | None:
    if samples.size == 0:
        return None
    values = samples.astype(np.float64) / 32768.0
    rms = math.sqrt(float(np.mean(values * values)))
    return round(20 * math.log10(max(rms, 1e-9)), 2)


def validate_scene(scene: dict, decoded_duration: float) -> tuple[list[str], dict]:
    errors = []
    if not isinstance(scene.get("duration"), (int, float)) or scene["duration"] <= 0:
        raise ValueError("Scene has no valid duration")
    duration = float(scene["duration"])
    delta_ms = round((decoded_duration - duration) * 1000, 2)
    if abs(delta_ms) > 100:
        errors.append(f"Decoded audio differs from scene duration by {delta_ms} ms")
    cues = scene.get("mouthCues", [])
    if not cues:
        errors.append("Scene has no mouth cues")
    prev_end = 0.0
    largest_gap = 0.0
    largest_overlap = 0.0
    invalid_cues = []
    for i, cue in enumerate(cues):
        start, end = float(cue["start"]), float(cue["end"])
        if start < 0 or end <= start or end > duration + .2:
            invalid_cues.append(i)
        if cue.get("value") not in CUE_SYMBOLS:
            invalid_cues.append(i)
        largest_gap = max(largest_gap, start - prev_end)
        largest_overlap = max(largest_overlap, prev_end - start)
        prev_end = end
    if invalid_cues:
        errors.append(f"Invalid cue indices: {sorted(set(invalid_cues))}")
    if largest_gap > .025 or largest_overlap > .025:
        errors.append(f"Mouth cue timeline has gap/overlap >25ms: {largest_gap:.3f}/{largest_overlap:.3f}s")
    if cues and abs(float(cues[-1]["end"]) - duration) > .05:
        errors.append("Last mouth cue does not cover scene duration")
    segments = scene.get("segments", [])
    last_end = 0.0
    for i, segment in enumerate(segments):
        start, end = float(segment["start"]), float(segment["end"])
        if start < last_end - .01 or end <= start or end > duration + .1:
            errors.append(f"Invalid coarse segment {i}")
        last_end = end
    return errors, {
        "sceneDurationSeconds": duration,
        "decodedDurationSeconds": round(decoded_duration, 6),
        "decodedMinusSceneMs": delta_ms,
        "mouthCueCount": len(cues),
        "mouthCueMaxGapMs": round(largest_gap * 1000, 2),
        "mouthCueMaxOverlapMs": round(largest_overlap * 1000, 2),
        "coarseSegmentCount": len(segments),
    }


def build_report(zip_path: Path, out_dir: Path, expected_scene_git_sha: str | None = None) -> dict:
    mp3, scene_bytes = load_source(zip_path)
    scene = json.loads(scene_bytes)
    out_dir.mkdir(parents=True, exist_ok=True)
    wav_path = out_dir / "evan-v3-16000-mono.wav"
    samples, pcm = decode_pcm(mp3, wav_path)
    scene_blob = git_blob_sha(scene_bytes)
    scene_matched = expected_scene_git_sha is not None and scene_blob == expected_scene_git_sha
    if expected_scene_git_sha is not None and not scene_matched:
        raise ValueError("Scene JSON does not match expected Git blob SHA; refuse provenance claim")
    decoded_duration = len(samples) / 16000
    issues, scene_metrics = validate_scene(scene, decoded_duration)
    # Acoustic *review candidates* only. A low-energy phone may be a legitimate
    # stop closure or unvoiced consonant; never auto-change mouth cues from RMS.
    low_energy_cues = []
    long_cues = []
    for i, cue in enumerate(scene.get("mouthCues", [])):
        start, end = float(cue["start"]), float(cue["end"])
        a = max(0, min(len(samples), round(start * 16000)))
        b = max(a, min(len(samples), round(end * 16000)))
        db = rms_dbfs(samples[a:b])
        entry = {"index": i, "start": start, "end": end,
                 "rhubarbShape": cue["value"], "rmsDbfs": db}
        if cue["value"] != "X" and end - start >= .05 and db is not None and db < -37:
            low_energy_cues.append(entry)
        if cue["value"] != "X" and end - start > .4:
            long_cues.append(entry)
    segments = []
    for i, s in enumerate(scene.get("segments", [])):
        a = max(0, min(len(samples), round(float(s["start"]) * 16000)))
        b = max(a, min(len(samples), round(float(s["end"]) * 16000)))
        block = samples[a:b]
        segments.append({
            "index": i,
            "start": float(s["start"]),
            "end": float(s["end"]),
            "text": str(s.get("text", "")),
            "rmsDbfs": rms_dbfs(block),
            "peakDbfs": round(20 * math.log10(max(float(np.max(np.abs(block.astype(np.int32)))) / 32768, 1e-9)), 2) if block.size else None,
        })
    # All 18 disputed word/phone intervals from the later speech planner are still
    # unresolved: these coarse scene segments and Rhubarb cues are NOT gold labels.
    report = {
        "kind": "source-audio-provenance-and-coarse-qa",
        "sourceArchiveName": zip_path.name,
        "sourceAudioMember": AUDIO_MEMBER,
        "sourceSceneMember": SCENE_MEMBER,
        "sourceAudioSha256": hashlib.sha256(mp3).hexdigest(),
        "sourceSceneGitBlobSha1": scene_blob,
        "expectedSceneGitBlobSha1": expected_scene_git_sha,
        "sceneMatchesExpectedGitBlob": scene_matched,
        "decodedPcmSha256": hashlib.sha256(pcm).hexdigest(),
        "decodedFormat": {"sampleRate": 16000, "channels": 1, "bitsPerSample": 16, "sampleCount": len(samples)},
        **scene_metrics,
        "signal": {
            "rmsDbfs": rms_dbfs(samples),
            "peakDbfs": round(20 * math.log10(max(float(np.max(np.abs(samples.astype(np.int32)))) / 32768, 1e-9)), 2),
            "clippedSampleCount": int(np.count_nonzero((samples >= 32767) | (samples <= -32768))),
        },
        "segments": segments,
        "lowEnergyMouthCueReviewCandidates": low_energy_cues,
        "longMouthCueReviewCandidates": long_cues,
        "cueAnomaliesAreProvenErrors": False,
        "structuralIssues": issues,
        "phonemeBoundaryVerified": False,
        "later18FlaggedRegionsReviewed": False,
        "isVerifiedFinalMaster": False,
        "visualApproved": False,
        "releaseReady": False,
        "note": "Paired original V3 audio and scene by handoff archive provenance, not proof of word-accurate alignment or the later master WAV identity.",
    }
    (out_dir / "reference-take-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff_zip", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--expected-scene-git-sha", default=KNOWN_SCENE_BLOB)
    args = parser.parse_args()
    report = build_report(args.handoff_zip, args.out_dir, args.expected_scene_git_sha)
    print(json.dumps({k: report[k] for k in ("sceneMatchesExpectedGitBlob", "decodedDurationSeconds", "decodedMinusSceneMs", "mouthCueCount", "structuralIssues", "phonemeBoundaryVerified")}, indent=2))
    return 0 if not report["structuralIssues"] else 2


if __name__ == "__main__":
    raise SystemExit(main())