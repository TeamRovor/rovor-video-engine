"""Convert Rhubarb mouth cues and Evan gestures to Moho's native switch-layer timing.
Creates text data for a correctly constructed Moho Switch layer; not a rig.
No external services or dependencies.
"""
import argparse
import csv
import json
import math
from pathlib import Path

VALID = frozenset("ABCDEFGHX")
# Matches Rhubarb's built-in --datUsePrestonBlair mapping.
# Prefer Rhubarb's native -f dat exporter when the CLI is available.
DEFAULT_MAP = {"X":"rest", "A":"MBP", "B":"etc", "C":"E", "D":"AI",
               "E":"O", "F":"U", "G":"FV", "H":"L"}


def exposure(cues, fps=24, duration=None, mapping=None):
    """Return nonredundant 1-indexed Moho frame selections."""
    if not 1 <= fps <= 120:
        raise ValueError("FPS must be between 1 and 120")
    mapping = dict(DEFAULT_MAP if mapping is None else mapping)
    for symbol in VALID:
        if not mapping.get(symbol):
            raise ValueError("Missing mapping: " + symbol)
    sorted_cues = []
    for cue in cues:
        shape = cue.get("value")
        start, end = float(cue["start"]), float(cue["end"])
        if shape not in VALID:
            raise ValueError("Unknown Rhubarb cue: " + str(shape))
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise ValueError("Invalid Rhubarb cue timing")
        if sorted_cues and start < sorted_cues[-1][1] - 1e-5:
            raise ValueError("Overlapping or unsorted mouth cues")
        sorted_cues.append((start, end, shape))
    if duration is None:
        duration = sorted_cues[-1][1] if sorted_cues else 0
    duration = float(duration)
    if not math.isfinite(duration) or duration < 0:
        raise ValueError("Invalid duration")
    count = math.ceil(duration * fps)
    out, last, j = [], None, 0
    for i in range(count + 1):
        t = i / fps
        while j < len(sorted_cues) and sorted_cues[j][1] <= t + 1e-8:
            j += 1
        shape = "X"
        if i < count and j < len(sorted_cues) and sorted_cues[j][0] <= t < sorted_cues[j][1]:
            shape = sorted_cues[j][2]
        name = mapping[shape]
        if name != last:
            out.append((i + 1, name))
            last = name
    return out


def moho_dat(keys):
    return "MohoSwitch1\n" + "".join(f"{frame} {name}\n" for frame, name in keys)


def exposure_review(cues, fps=24, duration=None):
    """Report actual frame sampling losses without inventing phone corrections.

    An interval shorter than a frame can still be sampled. Conversely, an
    interval between samples can vanish entirely. Track cue identity rather
    than key count: adjacent cues may legitimately select the same drawing.
    """
    cues = list(cues)
    keys = exposure(cues, fps, duration)
    duration = float(duration if duration is not None else
                     (cues[-1]["end"] if cues else 0))
    count = math.ceil(duration * fps)
    sampled = [[] for _ in cues]
    j = 0
    for i in range(count):
        t = i / fps
        while j < len(cues) and float(cues[j]["end"]) <= t + 1e-8:
            j += 1
        if j < len(cues) and float(cues[j]["start"]) <= t < float(cues[j]["end"]):
            sampled[j].append(i + 1)
    rows = []
    for i, (cue, frames) in enumerate(zip(cues, sampled)):
        start, end = float(cue["start"]), float(cue["end"])
        reasons = []
        if not frames:
            reasons.append("not-sampled")
        if end - start < 1 / fps:
            reasons.append("shorter-than-frame")
        if end > duration:
            reasons.append("extends-past-scene")
        rows.append({"cueIndex": i, "shape": cue["value"], "start": start,
                     "end": end, "sampledFrameCount": len(frames),
                     "firstFrame": frames[0] if frames else None,
                     "lastFrame": frames[-1] if frames else None,
                     "reviewReasons": reasons})
    return {"fps": fps, "sceneDurationSeconds": duration,
            "renderFrameCount": count, "renderDurationSeconds": count / fps,
            "endRestFrame": count + 1, "switchKeyCount": len(keys),
            "unsampledCueIndices": [r["cueIndex"] for r in rows
                                    if not r["sampledFrameCount"]],
            "reviewRequired": any(r["reviewReasons"] for r in rows),
            "phonemeTimingVerified": False, "cues": rows}


def gesture_rows(gestures, fps=24):
    """Moho exposure sheet, not bone keyframes."""
    result = []
    for gesture in gestures:
        start, end = float(gesture["start"]), float(gesture["end"])
        if start < 0 or end <= start:
            raise ValueError("Invalid gesture")
        result.append((max(1, math.floor(start * fps) + 1),
                       max(1, math.ceil(end * fps) + 1), gesture["kind"]))
    return sorted(result)


def convert(mouth_path, scene_path, output, fps=60):
    lips = json.loads(Path(mouth_path).read_text())
    scene = json.loads(Path(scene_path).read_text()) if scene_path else {}
    duration = scene.get("duration", lips.get("metadata", {}).get("duration"))
    keys = exposure(lips["mouthCues"], fps, duration)
    review = exposure_review(lips["mouthCues"], fps, duration)
    rows = gesture_rows(scene.get("gestures", []), fps) if scene_path else []
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(moho_dat(keys), encoding="utf-8")
    result = {"switch_file": str(output), "keyframes": len(keys), "fps": fps}
    review_path = output.with_suffix(".review.json")
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    result["timing_review"] = str(review_path)
    result["unsampled_cues"] = len(review["unsampledCueIndices"])
    if scene_path:
        gestures = output.with_suffix(".gestures.csv")
        with gestures.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("start_frame", "end_frame_exclusive", "gesture"))
            writer.writerows(rows)
        result["gesture_sheet"] = str(gestures)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mouth_json", type=Path)
    p.add_argument("--scene", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--fps", type=int, default=60)
    args = p.parse_args()
    print(json.dumps(convert(args.mouth_json, args.scene, args.output, args.fps), indent=2))
