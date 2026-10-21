# Long-form original-narration chapter planner (draft)

## Problem and scope

The existing PR #13 job intake and native archive compiler intentionally
accept a maximum of 60 seconds per job/project. A 4:23 or 8-9 minute narration
therefore **cannot yet** be submitted to the end-to-end ChatGPT-to-Moho queue.

This independent module prepares a **manifest** for a future chapter adapter.
It does not lift PR #13's upload, artifact, or project-duration limits, generate
a video, slice WAV files, render Moho, certify phoneme boundaries, or produce a
ready-to-publish film. Keep the existing limits until all adapter and media QA
work is complete.

## Required verified inputs

1. One **unaltered source-derived** 16 kHz mono 16-bit PCM WAV (max 15 minutes).
   The program reads every PCM sample and rejects a truncated WAV. The WAV's
   SHA-256 is recorded; the original file is not rewritten or copied.
2. One reviewed English acoustic word/phone plan using the existing
   PR #5 speech schema. The shared `speech_plan_gate.audit` must return
   `technical_pass_pending_visual_review` (no errors/review flags). This
   prevents fallback/Rhubarb-only phonemes and unresolved pronunciation/word
   contradictions from entering automatic planning. Even a passing metadata
   gate still needs listening verification against real source speech.

CLI, from repository root:

    python tools/longform_chapters.py --wav /private/original-16khz.wav --plan /private/reviewed-speech-plan.json --out /private/chapter-manifest.json

The output file must not already exist; it will not overwrite user work.
The private MP3/WAV/transcript contents are **never** included in the manifest,
only hashes and timing metadata. Do not publish source-derived sensitive
timings/metadata without consent.

## Planning contract

- 60 fps exactly. Up to 900 seconds input / 54,000 video frames.
- Every chapter is <= 3,600 frames (60 seconds), suitable for the existing
  *duration restriction* of the native compiler. This does NOT mean each
  chapter has a valid dedicated Evan Moho project.
- For longer narration, each chapter is at least 900 frames (15 seconds);
  the optimizer prefers approximately 2,700 frames (45 seconds).
- A cut may be placed **only between adjacent acoustically aligned full words**
  with a positive gap after 12 ms margins. It also checks that it does not
  lie in any aligned phone. If there is no valid way to fit chapters within
  60 seconds, the planner refuses rather than guessing a split inside speech.
- Timing uses a continuous source frame coordinate system with
  `startFrame` inclusive and `endFrameExclusive` exclusive. Local Moho
  chapter frame 1 corresponds to the global chapter's first time sample,
  subject to future rig-specific startup and project validation.
- Source PCM boundaries are rounded **once at global frame boundaries** using
  integers: sample = round_nearest(frame * 16000 / 60). Exact chapter starts
  equal previous chapter ends, preserving every source sample without overlap.
  The last chapter ends at the *true* WAV sample count; video frame count uses
  ceiling of the original duration times 60.
- SHA-256 hashes bind the unmodified WAV and plan. Every chapter includes
  both exclusive source sample and source frame spans, a source word-gap cut
  reference and a pending-review status. Internal chunks shorter than 30s
  are NOT independently publishable short videos; the user-facing
  30-second minimum applies to the complete reviewed deliverable.

## Safe next integration (not implemented)

A future authenticated host adapter must hold a stable original MP3/WAV
reference, transcribe/correct/force-align once, generate the manifest, derive
true chapter-local phone timestamps and keys from the approved Evan mouth rig,
then create **disposable per-chapter native 60fps Moho projects**.

It must verify absolute/relative keyframe translations, chapter frame-zero
setup, audio chunk sample hashes, scene asset continuity, physical contact,
both formats' renders and audio timestamps at every seam. The finished video
must mux the original narration exactly once (not per-chapter AAC segments),
verify it against the source at distant checkpoints and pass human visual
approval. Chunk concatenation and 64 MiB return transport remain separate,
unimplemented bottlenecks.

No per-frame hallucinated phonemes, word truncation, automatic paid services,
new artwork, arbitrary network uploads, or producer approvals are added.

## Synthetic cross-platform acceptance

The new hosted workflow tests both 4:23 and 8:30 WAV sizes, total
sample/frame coverage, deterministic chapter selection, failure when no word
gap is safe, acoustic-gate refusal, malformed input, and no overwrite.

All examples use **synthetic WAV and JSON fixtures**, not production
narration. A successful test proves planning invariants only, not a working
long-form Moho animation or frame-accurate English mouth art.
