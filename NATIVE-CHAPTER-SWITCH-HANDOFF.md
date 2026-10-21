# Native Moho chapter switch compiler

This draft connects PR #16's checked WAV/phoneme chapter payloads to the
native ZIP compiler from PR #13. It generates a NEW Moho archive with an
existing, verified mouth switch's acoustic phoneme keys, preserving unrelated
source art and frame zero.

## Required inputs

A trusted local operator provides an existing private chapter package,
the chapter index, a verified native Moho source project with 60fps and
end_frame equal to that chapter's frame count, and a small calibration
JSON with these exact keys:

- schemaVersion: 1
- chapterIndex: zero-based selected chapter number
- templateSha256: hash of the exact native source project
- sourceWavSha256: hash of the original complete WAV
- mouthLayerUuid: real native switch layer UUID
- restChild: exact existing frame-zero rest child name
- phoneToChild: English base-phone names mapped to real switch children

These are manual art calibration inputs, not automatically inferred
bone names or a replacement for a professionally rigged Evan.

Command: python tools/native_chapter_switch.py --package PACKAGE_DIR
--chapter 0 --template CHAPTER_TEMPLATE.moho
--calibration CALIBRATION.json --out NEW_CHAPTER.moho

The output must not already exist. The compiler re-verifies the full
private bundle and checks SHA-256 identity, switch layer UUID, mouth rest
at frame zero, exact 60fps project duration and actual existing child names.
It computes keys from English acoustic phone timing at integer 60fps
chapter duration, writes an isolated native archive, reopens and checks it,
then exports to the new output path.

No 24fps retiming, no automatic rig substitutions, no source overwrites,
no video encoding, no live Moho control and no creative approval are
performed. This is a native archive proof, not a finished animation.

## Verification

Run python -m unittest -v tests.test_native_chapter_switch
tests.test_moho_compile tests.test_chapter_package
tests.test_longform_chapters tests.test_speech_plan_gate

Hosted CI uses source-free synthetic WAVs and disposable 1038/1045
Moho ZIP fixtures on Linux, Windows and macOS. A pass is only evidence of
safe native switch archive compilation, not that Evan's real rig has been
validated or that the Moho 14 GUI/CLI rendered video.

Next: inspect the genuine approved Evan native rig, stage a disposable
chapter scene with the correct duration, render 1080p60 with Moho on
an authorized host, verify speech and visual contact in real output,
and assemble with the original full narration.
