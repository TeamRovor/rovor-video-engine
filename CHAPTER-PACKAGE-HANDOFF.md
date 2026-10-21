# ROVOR native Moho chapter handoff — private audio + phone payloads

The previous draft PR #15 produces a verified **planning manifest**.
This follow-on work turns that plan into the actual **chapter PCM WAV files**
and **chapter-local phoneme JSON**, without transcoding or editing the master.

**Scope boundary:** this is a *private data package for a future trusted
native Moho worker*, not a completed video, an approved Evan master rig,
a functioning remote upload, or an automatic PR #13 duration-limit increase.
Do not merge into main before checking branch dependencies and ownership.

## Run on host already holding the original source

The inputs must already exist on an authorized machine:

- Original source-derived 16 kHz mono PCM16 WAV, **not** a resynthesized voice.
- The full reviewed/acoustically aligned English word+phone plan. Its existing
  gate must have no timing errors or unresolved review flags.
- The original PR #15 manifest generated from those exact same input bytes.

At repository root:

    python tools/chapter_package.py \
      --wav /private/source.wav \
      --plan /private/english-phones.json \
      --chapters /private/chapter-plan.json \
      --out /private/native-chapter-package

`--out` must not exist. The output parent directory must already exist.
Never send originals, phone transcripts, private directory paths, or bundles
to public GitHub Actions or commit them into this repository. CI fixtures
are synthetic only.

### What the private output contains

    native-chapter-package/
      chapter-000/
        narration.wav
        acoustic-plan.json
        chapter.json
      chapter-001/
        narration.wav
        acoustic-plan.json
        chapter.json
      ...
      bundle.json

Each WAV is an exact PCM16 portion of the master source recording. The
package streams samples in bounded memory (64K sample chunks), measures
individual raw PCM and RIFF/WAV file SHA-256s, reconstructs the **entire**
master PCM hash in chapter order, and refuses mismatches. Chapter-local
English word and phone timestamps are shifted by the exact original
sample offset and verified using the shared `speech_plan_gate.audit`.
Cuts occur only in the original reviewed word gaps, not inside the mouth
motions of a pronounced English phone.

Every chapter has a local Moho frame-1 origin and an intended end frame
of at most 3600 at 60 fps, as *data metadata*. This does **not** mean
a compliant Moho project or native animation has been rendered. The
source file, source audio bytes and reviewed full phoneme plan remain
unaltered and are source-hash-bound in each evidence record.

The status ledger is written last. An absent `bundle.json` means a
package is incomplete; any error removes only the newly allocated
destination. Existing destinations are never overwritten. Raw WAV
segments and phone transcripts are private local media, not GitHub
artifacts.

## Verify again before a native renderer opens the package

    python tools/chapter_package.py \
      --verify-package /private/native-chapter-package

Read-back verification rejects missing/symlinked or unexpected chapter
files, altered WAV, altered local phoneme timelines, changed frame/sample
boundaries, wrong chapter order, forged success/approval status, and a
combined PCM mismatch. It checks source-related hashes in the ledger,
but because the ledger is not digitally signed the trusted host must
retain the original source hashes separately when accepting transfers.

## Studio-native integration still required

A future approved worker must do all of the following before any film is
treated as deliverable:

1. Match the private bundle to the actual verified original Evan master
   Moho rig and create *disposable* 60 fps per-chapter native projects.
2. Compile each chapter's local phone events onto its **real** rig switch
   names and calibrated mouth/face channels, respecting frame zero/setup.
3. Independently stage 1920x1080 and 1080x1920 animated scene compositions,
   character acting, prop contacts, transitions, camera and shot direction.
4. Render actual full-frame native Moho chapter visuals and check exact
   60 fps decode/PTS/frame continuity at each join.
5. Prefer muxing **the unchanged full original narration once** into the
   assembled silent video to avoid per-chapter AAC gaps or drift. Verify
   audio correlation throughout the finished 4–9-minute film.
6. Run normal-speed human creative review, captions, music/SFX level QA,
   and secure return of large files beyond the currently supported
   64 MiB single-artifact transport limit.

The existing PR #13 60-second MP3 intake / native Moho compiler limits
and current private Mac adapter restrictions are intentionally unchanged.
This step only makes downstream native work cheaper, deterministic and
auditable; it does not claim physical Moho/ChatGPT control.

## Verification evidence

Run from repo root:

    python -m unittest -v tests.test_chapter_package \
      tests.test_longform_chapters tests.test_speech_plan_gate

The workflow tests Linux, Windows and macOS against *synthetic* 4:23 and
8:30 WAVs with repeatable mock acoustic word data. These prove byte-exact
packaging arithmetic and proper failure behavior but are not evidence
that original real narration was force-aligned or that studio visual
quality is achieved.
