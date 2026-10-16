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


def convert(mouth_path, scene_path, output, fps=24):
    lips = json.loads(Path(mouth_path).read_text())
    scene = json.loads(Path(scene_path).read_text()) if scene_path else {}
    duration = scene.get("duration", lips.get("metadata", {}).get("duration"))
    keys = exposure(lips["mouthCues"], fps, duration)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(moho_dat(keys), encoding="utf-8")
    result = {"switch_file": str(output), "keyframes": len(keys), "fps": fps}
    if scene_path:
        gestures = output.with_suffix(".gestures.csv")
        with gestures.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("start_frame", "end_frame_exclusive", "gesture"))
            writer.writerows(gesture_rows(scene.get("gestures", []), fps))
        result["gesture_sheet"] = str(gestures)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mouth_json", type=Path)
    p.add_argument("--scene", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--fps", type=int, default=24)
    args = p.parse_args()
    print(json.dumps(convert(args.mouth_json, args.scene, args.output, args.fps), indent=2))
