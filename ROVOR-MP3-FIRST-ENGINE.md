# ROVOR MP3-first animation engine — divided development work

## The actual target

**Input:** one user-approved MP3 file.

**Output after approval:** a 1080p / 60 fps film in portrait and landscape where Evan's established source-art character speaks the actual narration with correct English pronunciation, continuous facial articulation, purposeful body acting, illustrated environments, edit-worthy comedic/cinematic direction, music and effects only when suitable, and no misleading invented customer claims. A final user-facing preview is at least 30 seconds. The original MP3 remains unchanged and time-aligned; no artificial stretching.

This is the **goal**, not a claim that the current V3/PR #5 pipeline already performs the entire process flawlessly.

## Two independent workstreams, one shared interface

| Lane | Owner once claimed | Responsibility | Explicit exclusions |
| --- | --- | --- | --- |
| **Engine cost, speed and robustness** | Evan's GitHub-connected ChatGPT | Hosted Windows/macOS/Linux tests, stage timings, memory, hash-based cache reuse, restart and resume, duplicate-file handling, setup diagnosis, minimum successful processing per MP3 | No rewriting Evan's artistic rig, no re-authoring acoustic phone curves, no claiming local Windows access without evidence |
| **Speech and acting intelligence** | Amar's animation-development ChatGPT | Audio-grounded English phoneme and viseme verification, real phoneme contacts, coarticulation, mouth and body acting, shot direction, continuity and creative QA | No rerunning Windows package engineering or restructuring shared media work without coordination |

**Canonical task status:** `coordination/tasks.json`. Select current eligible efficiency or animation work using WORK.md. Historical tasks mentioned here may already be complete; the live queue controls availability and ownership. Shared audio import and Windows runtime already have separate owners; do not duplicate their scopes.

## Audio must win over spelling

Do not map English letters to mouth drawings. Map **the actual pronounced phone, at the time the audio produces it**, using the corrected transcript and acoustic alignment as inputs. Examples:

- *phone* `F OW N` — the letters `p` and `h` produce one /f/ sound; no P/B/M closure.
- *through* `TH R UW` versus *though* `DH OW` — the written letters are deceptively similar, the spoken sounds differ.
- *make* `M EY K` — the written final `e` is silent.
- *laugh* `L AE F` — `gh` does not receive a G animation.

Pronunciation dictionaries and a small, reviewed project-specific lexicon help choose intended phones, but the recording—not a guessed word length—determines each phoneme's start/end. English connected speech, reductions, stress, emphasis, accent and coarticulation need audio alignment. A forced aligner may still be wrong and must retain review flags. Rhubarb `A-H/X` cues are **mouth-shape estimates**, not phoneme labels.

## Single-MP3 pipeline, optimized to avoid repeat work

1. **Audio intake:** hash the original MP3; decode/measure once to a cached PCM16 WAV; preserve source identity. Reject empty, corrupt, mismatched or unsupported audio before high-cost steps.
2. **Speech understanding:** transcribe once with local Whisper, save timed text, highlight uncertain words; preserve corrected text in a versioned artifact instead of replacing the audio. If a script is supplied later, confirm it matches the recording.
3. **Pronunciation and alignment:** derive English phonetic sequences, including project-specific pronunciations; acoustic forced-align actual words and phones to the WAV. Treat fallback timings as draft only.
4. **Preflight:** run `tools/speech_plan_gate.py` on the existing PR #5 speech-plan JSON, reject structurally false phone/mouth/timing claims, and generate review flags for cues shorter than a frame. No 1080p final render needed at this step.
5. **Cartoon directing:** interpret the ideas being said; form a timed shot/storyboard and action plan with motives, anticipation, reaction, prop/contact choreography, cuts, camera changes, pacing and distinct portrait blocking. Avoid mechanically switching slides on keywords.
6. **Rig animation:** animate Evan's approved layered artwork through continuous jaw/lips/tongue/eyebrow/arm/hands with bounded holds and coarticulation, not PNG face stickers. Mouth poses and scene movement should respond to audio dynamics without inventing phone identity from energy.
7. **Cheap first pass:** deterministic rig and thumbnail/low-resolution animatic, sampled lip frames, scene action timeline, and continuity/error reports. Human creative review when unresolved. Reuse cached analysis if only visual timing or art changes.
8. **Final after gate:** render changed frames only, deterministic resumable chunks, separate portrait/landscape compositions reusing valid character-body work, encode complete unchanged narration once, measure actual speed/RAM and verify media.
9. **Editorial review:** replay challenging phrases at actual speed and reduced speed, inspect contacts, lips, anatomy, physical prop action, subtitles, music and scene pacing. Only Amar's signoff can mark art approved or ready to publish.

### Usage-conservative design requirements

- Store stage inputs and outputs by **content hashes and version**, including source MP3/WAV, transcript revision, pronunciation lexicon, alignment model/version, phoneme plan, rig/art assets, storyboard, renderer version, fps and composition.
- Reuse exact-match transcription, alignment, and audio analysis for future renders. Invalidate only downstream stages affected by an actual dependency change; rerun phone alignment if corrected words change.
- Use CPU-based local and GitHub-hosted development tests before any costly final render. Avoid subscriptions, repeated LLM calls, rebuilding every frame for a caption change, and parallel jobs competing for the same output folder.
- Never automatically discard previous successful output after failed replacements; checkpoint render state, bound processing time and memory, and prove cache hits with logs.
- Report cold run, warm run, correction-only run, crash/resume run, memory peak, stage timings, CI platform and current commit; **do not claim a faster pipeline until the difference is measured**.
- Keep local machine executable paths, private recordings and Moho original files out of commits unless the user has explicitly authorized sharing the particular files in the private repo. The shared MP3 import has its own active claim.

## First independent acoustic safety gate (not a full phoneme aligner)

`tools/speech_plan_gate.py` consumes the **existing** PR #5 plan structure: `alignment.status`, `words`, `phonemes`, `silences`. It supports all 39 English ARPABET base phones and preserves the current 39-phone-to-cartoon-target catalog. It checks claims rather than creating new boundaries from spelling.

```sh
# Best evidence when the WAV is available (requires source-derived mono 16 kHz PCM16)
python tools/speech_plan_gate.py --plan /private/path/speech-plan.json --wav /private/path/source.wav --fps 60 --out /private/path/speech-audit.json

# Without media, permit a metadata review but label provenance as unverified
python tools/speech_plan_gate.py --plan /private/path/speech-plan.json --duration 262.687313 --fps 60
```

Statuses:
- `blocked`: invalid phone/timing/viseme, incomplete acoustic coverage, or estimate masquerading as acoustic evidence.
- `review_required`: unresolved word flags or phone/contact intervals skipped by frame sampling.
- `technical_pass_pending_visual_review`: structural checks passed; **does not** mean accurate speech, visual approval, finished video or production readiness.

This new tool is **not yet integrated into PR #5's render path** and does not replace `acoustic_alignment.py`, `english_articulation.py`, `speech_planner.py`, or `rovor-production/lip_cue_audit.py`. Integration requires review of the exact current V5 branches and original-audio evidence; it cannot be implied by a green synthetic test.

## Shared handoff

Evan's ChatGPT should read [REMOTE-EVAN-GITHUB.md](REMOTE-EVAN-GITHUB.md), this page and the fresh [task queue](coordination/tasks.json). Use the live efficiency routing; never re-claim a completed task from an old document. Work in the existing Windows-reliability PR branch; keep the benchmarks as separately named files/tests. GitHub-hosted testing can continue without Evan's laptop, but his machine remains an unverified endpoint until an actual local diagnostic succeeds.

For the speech/acting track, keep the original Evan look and work in the existing art branches PR #4/#5 where appropriate. Verify actual audio and eye-level rendered movement before declaring quality. This specification does not authorize downloading or mutating a private recording or Moho original.
