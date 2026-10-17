# Evan acting development — 2026-10-17

Continue from this checkout without rebuilding earlier work. Branch: `development/evan-timing-review`, based on local/remote body-rig commit `79bd397`. First continuation commit `b62d839` preserved the separate art-reset safeguards from `09e0717` and added 1080p60 output. Main, V3/V4, approved updater/symlink and native Moho are untouched. No merge or deployment.

## New animation work

- `narration_acting()` authors held attitudes across the complete 22.047375-second favicon recording, replacing the old study's 4.8-second-only motion for the new scene. The original `acting()` comparison baseline remains. Head lead, shoulder/elbow/wrist delays and a closing settle are expressed in seconds, independently of output fps.
- `cartoon_wrist.py` attaches a separately generated pointing hand to screen-right wrist FK, with a separately masked forearm. The new hand activates during the globe explanation. Source and registration metadata are in `hand-source`. This is experimental art, not an approved hand rig; the join, pose-switch pop and skin/line match still need refinement.
- `cartoon_expression.py` moves the original eyebrows and nearby skin by small independent offsets while keeping the glasses, hair and mouth outside the deformation region. This is a local source-art warp, not newly drawn expression plates or visible-eye animation.
- `render_favicon_acting.py` provides separately composed 1920×1080 and 1080×1920 scenes at 60 fps. Evan points at the globe; the tab uses the verified Rovor mark during the favicon explanation. Close framing was corrected after inspection caught clipped fingers and a graphic covering the pointing tip.

## Rendering workflow and evidence

`render_acting_video.py` streams both formats from each body sample once, in bounded local worker chunks. It preserves a fingerprinted RGBA body cache so later composition changes can reuse expensive animation frames. A repeat render verified 6/6 cache hits. Source, plan and recording hashes prevent reusing incompatible output folders. The audio guard compares the plan's rounded RMS envelope against the actual WAV; the current take matches all 2,205 samples exactly (maximum difference 0).

Two corrected 3.4-second narrated internal reviews cover source time 1.8–5.2 seconds. FFmpeg decoding verified 204 frames per file, 60 fps, AAC narration, and the expected 1920×1080 / 1080×1920 dimensions. These are internal acting studies, not finished marketing videos or approval of phone timing. The earlier v1 composition study is retained as rejected framing; v2 is the corrected layout.

Local intermediate evidence lives in the parent work directory: `acting-review`, `acting-video-v1`, `acting-video-v2`, `cache-reuse-check`, `body-cache`, and `acoustic-word-review`. They are reproducible development evidence, not release assets. The recording is kept local and must not enter a public repository.

## Rejected or unresolved artwork

- A targeted generated torso repair (`body-source/armpit-cleanup-v2.png`) failed ECC registration. It is not loaded. The original armpit ghost folds and imperfect neck/collar transition remain.
- An alternative generated F/V mouth is preserved independently in `oral-source` and `oral-rig/fv-contact-v2.*`, with its registration builder. Native side-by-side inspection found that it reads as a smile, not convincing labiodental contact. It is **not active** in the new scene; the default retains the old contact. The optional candidate constructor exists only for explicit internal comparisons.
- A tighter torso matte and a larger/proximally shifted wrist overlap were tried as local visual prototypes; neither is silently installed as a completed repair. Original source drawings remain intact.

The new hand, authored acting, eyebrows and compositions are actual implementation progress. Passing geometry or encoding checks does not make this studio-level animation. Hidden surfaces, convincing mouth anatomy, cleaner hand transitions, perspective turns and stronger character acting remain necessary.

## Timing evidence

Recovered the existing regular-chat `review_acoustic_flags.py` and its tests verbatim from `09e0717`; did not rewrite that work. Ran it on the verified original recording to produce all 18 waveform/spectrogram/phone evidence packets. Inspected the two full-resolution plots for opening “tiny” and post-pause “it's,” plus overview sheets covering all 18 flagged words.

The independent coarse anchors visibly shift across pauses: the “it's” estimate is around 9.04–9.42 seconds in a low-energy/pause interval, whereas the acoustic interval is 10.19–10.31 seconds at the next speech onset. Opening “tiny” has a coarse estimate ending inside the longer voiced region. These observations explain why disagreement alone cannot label the acoustic timing wrong. They do not prove each phoneme boundary. No original boundaries were retimed; all 18 still require perceptual decisions before sync can be certified.

## Checks and next work

33 focused narration/body/oral/output tests pass, including full-take non-inverting meshes, wrist attachment, eyebrow displacement bounds, final settle and rejection of a mismatched recording. The recovered evidence-packet tests are run separately before the next checkpoint commit. `git diff --check` passes.

Next priorities: genuinely registered hidden shoulder/neck artwork; a relaxed/half-point hand breakdown and clean wrist overlap; correct F/V and L drawings; perceptual timing decisions. Preserve the 1080p60 settings, body cache, previous branches and existing rejected-art guard. Do not regenerate unchanged source sheets, alignments or completed layers just to show activity.
