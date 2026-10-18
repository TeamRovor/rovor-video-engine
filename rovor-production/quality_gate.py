"""Fail-closed editorial storyboard audit for original Rovor 2D animation.

This checks whether a shot plan can plausibly support entertaining illustrated
storytelling. It NEVER marks an actual video publishable without visual review.
"""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

KINDS = {"environment", "action", "visual-explainer", "object-demo",
         "metaphor", "reaction", "transition", "endcard"}
TALKING_HEAD = {"talking-head", "static-puppet", "still-portrait"}
BANNED = {"stock-footage", "stock-video", "unlicensed-asset", "generic-ai-video"}


def audit(plan):
    problems = []
    try:
        duration = float(plan["durationSec"])
        shots = plan["shots"]
    except (KeyError, TypeError, ValueError):
        return {"valid": False, "problems": ["Missing durationSec or shots"], "publicationApproved": False}
    if not math.isfinite(duration) or duration <= 0 or duration > 900:
        problems.append("Duration must be finite, positive and at most 900 seconds")
    if not isinstance(shots, list) or not shots:
        return {"valid": False, "problems": problems + ["No shots"], "publicationApproved": False}
    cursor = 0.
    kinds = Counter()
    assets = set()
    talking_duration = 0.
    explanatory_duration = 0.
    long_shots = []
    for number, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            problems.append(f"Shot {number} must be an object")
            continue
        try:
            start, end = float(shot["start"]), float(shot["end"])
        except (KeyError, TypeError, ValueError):
            problems.append(f"Shot {number}: invalid start/end")
            continue
        if not (math.isfinite(start) and math.isfinite(end) and start >= 0 and start < end):
            problems.append(f"Shot {number}: invalid time interval")
            continue
        if abs(start-cursor) > 0.04:
            problems.append(f"Shot {number}: gap or overlap at {start:.3f}s")
        cursor = end
        span = end-start
        kind = shot.get("kind")
        kinds[kind] += 1
        if kind in TALKING_HEAD:
            talking_duration += span
        if kind in {"visual-explainer", "object-demo", "metaphor", "action"}:
            explanatory_duration += span
        if kind not in KINDS and kind not in TALKING_HEAD:
            problems.append(f"Shot {number}: unknown animation scene kind")
        if span > 15:
            long_shots.append(number)
        if not isinstance(shot.get("visualPurpose"), str) or len(shot["visualPurpose"].strip()) < 12:
            problems.append(f"Shot {number}: missing specific on-screen storytelling purpose")
        motions = shot.get("animatedActions", [])
        if not isinstance(motions, list) or not any(isinstance(x, str) and x.strip() for x in motions):
            problems.append(f"Shot {number}: no timed visual action")
        shot_assets = shot.get("originalAssetIds", [])
        if not isinstance(shot_assets, list) or not shot_assets:
            problems.append(f"Shot {number}: no named original illustration or character asset")
        else:
            for asset in shot_assets:
                if not isinstance(asset, str) or not asset.strip():
                    problems.append(f"Shot {number}: invalid asset ID")
                elif asset.lower().strip() in BANNED:
                    problems.append(f"Shot {number}: stock/generic footage not permitted")
                else:
                    assets.add(asset.strip())
        if kind not in ("transition", "endcard") and not shot.get("composition"):
            problems.append(f"Shot {number}: missing camera/composition direction")
    if abs(cursor - duration) > .04:
        problems.append("Shots do not cover exactly the narration duration")
    if long_shots:
        problems.append("Shots longer than 15 seconds: " + ", ".join(map(str, long_shots)))
    if duration > 30:
        if len(shots) < math.ceil(duration / 12):
            problems.append("Insufficient illustrated story beats for narration length")
        if talking_duration / duration > .20:
            problems.append("Talking-head or static-puppet screen time exceeds 20%")
        if explanatory_duration / duration < .35:
            problems.append("Less than 35% of video is visual storytelling or demonstration")
        if len(set(kinds) & KINDS) < 4:
            problems.append("At least four distinct illustrated shot types are required")
    if duration >= 240 and len(assets) < 10:
        problems.append("Long-form work needs at least ten distinct designed assets")
    return {
        "valid": not problems,
        "durationSec": duration,
        "shotCount": len(shots),
        "distinctAssetCount": len(assets),
        "talkingHeadFraction": round(talking_duration / duration, 4) if duration > 0 else 0,
        "illustratedStoryFraction": round(explanatory_duration / duration, 4) if duration > 0 else 0,
        "sceneKinds": dict(kinds),
        "problems": problems,
        "publicationApproved": False,
        "visualAndNarrativeReviewRequired": True,
        "note": "Passing editorial structure does not certify actual movement, humor, pacing, art or final-video quality."
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("storyboard", type=Path)
    p.add_argument("--report", type=Path)
    p.add_argument("--production-assets", type=Path,
                   help="Strict production-only source-art manifest; no fake asset labels")
    args = p.parse_args()
    plan = json.loads(args.storyboard.read_text())
    if args.production_assets:
        from original_art_story_gate import inspect_storyboard
        registry = json.loads(args.production_assets.read_text())
        report = inspect_storyboard(plan, registry, args.production_assets.parent)
    else:
        report = audit(plan)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if not report["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
