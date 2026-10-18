"""Rovor user-visible video handoff gate: 30 seconds is a HARD minimum.

A 3-second or 22-second development test must never be delivered or labeled
a Rovor video. Validate *actual decoded* 60fps frame count and synchronized
audio evidence, not filename, expected duration, container metadata alone,
or time-stretching. This is a technical handoff gate, not artistic approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

MIN_USER_VIDEO_SECONDS = 30.0
REQUIRED_FPS = 60
MIN_USER_VIDEO_FRAMES = 1800
SIZES = {"landscape": (1920, 1080), "portrait": (1080, 1920)}


class HandoffRejected(ValueError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(video, report, orientation):
    """Return validated handoff evidence or raise, fail closed."""
    if orientation not in SIZES:
        raise HandoffRejected("Unknown video orientation")
    video, report = Path(video), Path(report)
    if not video.is_file() or video.stat().st_size < 1:
        raise HandoffRejected(f"{orientation}: missing nonempty MP4")
    if not report.is_file():
        raise HandoffRejected(f"{orientation}: missing decoded verification report")
    try:
        data = json.loads(report.read_text())
    except (ValueError, UnicodeError, OSError) as exc:
        raise HandoffRejected(f"{orientation}: malformed verification report") from exc

    try:
        fps = data["fps"]
        frames = data["decodedFrames"]
        dimensions = tuple(data["dimensions"])
        stable = data["continuousTimestamps"]
        correlation = float(data["referenceCorrelation"])
        offset = int(data["offsetSamples"])
        audio_seconds = float(data["decodedAudioSeconds"])
        reference_seconds = float(data["referenceAudioSeconds"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HandoffRejected(f"{orientation}: missing audio/frame evidence") from exc

    if type(fps) is not int or fps != REQUIRED_FPS:
        raise HandoffRejected(f"{orientation}: must be exactly 60 fps")
    if type(frames) is not int or frames < MIN_USER_VIDEO_FRAMES:
        raise HandoffRejected(f"{orientation}: only {frames} decoded frames; at least 1800 required")
    seconds = frames / fps
    if seconds < MIN_USER_VIDEO_SECONDS:
        raise HandoffRejected(f"{orientation}: {seconds:.3f}s below mandatory 30s")
    if dimensions != SIZES[orientation] or stable is not True:
        raise HandoffRejected(f"{orientation}: wrong dimensions or discontinuous frames")
    if (not all(math.isfinite(x) for x in (correlation, audio_seconds, reference_seconds))
            or correlation < 0.98 or abs(offset) > 32):
        raise HandoffRejected(f"{orientation}: original narration matching failed")
    if (abs(audio_seconds - reference_seconds) > .05
            or abs(audio_seconds - seconds) > .05
            or audio_seconds < MIN_USER_VIDEO_SECONDS - .05
            or reference_seconds < MIN_USER_VIDEO_SECONDS - .05):
        raise HandoffRejected(f"{orientation}: audio length or video/audio timing mismatch")
    if data.get("videoSha256") != sha256(video):
        raise HandoffRejected(f"{orientation}: SHA256 mismatch")
    if data.get("phonemeTimingVerified") is True and not data.get("phonemeEvidenceId"):
        raise HandoffRejected(f"{orientation}: phoneme certification lacks supporting evidence")
    return {
        "orientation": orientation,
        "video": video.name,
        "decodedFrames": frames,
        "fps": fps,
        "durationSec": seconds,
        "sha256": data["videoSha256"],
        "technicalHandoffReady": True,
        "publicationApproved": False,
        "studioQualityCertified": False,
    }


def validate_pair(landscape, landscape_report, portrait, portrait_report):
    a = check(landscape, landscape_report, "landscape")
    b = check(portrait, portrait_report, "portrait")
    if a["decodedFrames"] != b["decodedFrames"]:
        raise HandoffRejected("Portrait and landscape do not cover the same narration")
    return {
        "minimumVideoSeconds": MIN_USER_VIDEO_SECONDS,
        "minimumDecodedFrames": MIN_USER_VIDEO_FRAMES,
        "technicalHandoffReady": True,
        "publicationApproved": False,
        "studioQualityCertified": False,
        "outputs": [a, b],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--landscape", type=Path, required=True)
    parser.add_argument("--landscape-report", type=Path, required=True)
    parser.add_argument("--portrait", type=Path, required=True)
    parser.add_argument("--portrait-report", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = validate_pair(args.landscape, args.landscape_report,
                           args.portrait, args.portrait_report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print("ROVOR_VIDEO_HANDOFF_30SEC_MINIMUM=PASS")


if __name__ == "__main__":
    main()
