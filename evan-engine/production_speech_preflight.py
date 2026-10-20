"""Opt-in acoustic QA for existing Evan cartoon acting renders.

Uses source-WAV header for duration, but does NOT re-align speech, certify
listening accuracy, render video, or mutate the source plan. Standard library
only. The renderer keeps its development behavior unless explicitly enabled.
"""
import math

from english_articulation import PHONE_CATALOG
from speech_plan_gate import PHONE_TO_SHAPE, audit, wav_duration


def check_speech_plan(plan, wav, mode="require", fps=60):
    if mode not in ("require", "report"):
        raise ValueError("Speech QA mode must be 'report' or 'require'")
    if type(fps) is not int or fps != 60:
        raise ValueError("Speech QA requires the established 60fps acting profile")
    # Fail closed if a newer art branch changes the articulation contract without
    # a coordinated change to this small source-branch audit module.
    if set(PHONE_CATALOG) != set(PHONE_TO_SHAPE) or any(
        PHONE_CATALOG[phone]["targets"][0] != target
        for phone, target in PHONE_TO_SHAPE.items()
    ):
        raise ValueError("English phone-to-cartoon mapping drift; reconcile catalog and QA gate")
    seconds = wav_duration(wav)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Missing original 16kHz PCM16 mono source-derived WAV")
    report = audit(plan, seconds, fps=fps, wav_header_checked=True)
    report["requestedMode"] = mode
    report["acousticBoundariesPerceptuallyApproved"] = False
    report["cartoonActingApproved"] = False
    report["readOnly"] = True
    report["audioContentCompared"] = False
    if mode == "require" and report["status"] != "technical_pass_pending_visual_review":
        causes = report["errors"][:3]
        flags = report["reviewFlags"][:3]
        raise ValueError(
            "Strict English speech QA rejected plan before render: "
            + report["status"]
            + " | errors=" + repr(causes)
            + " | pending-review=" + repr(flags)
            + ". Resolve audio/phoneme evidence; do not rewrite boundaries from spelling."
        )
    return report
