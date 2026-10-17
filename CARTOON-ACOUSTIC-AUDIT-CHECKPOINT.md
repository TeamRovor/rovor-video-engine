# Cartoon Evan — acoustic evidence checkpoint (2026-10-16)

## Branch and scope
- Repo: TeamRovor/rovor-video-engine.
- Working branch: development/cartoon-acoustic-audit, forked from development/evan-painted-rig; no merge/deploy.
- The parent branch's PAINTED-EVAN-CHECKPOINT.md, CARTOON-EVAN-DIRECTION.md and CARTOON-EVAN-HEAD-MOTION.md remain the authoritative context.
- User's **latest** direction: entertaining, expressive 2D cartoon; photograph for loose identity cues only. Do NOT resume the superseded realistic painted style.
- Existing registered head is **experimental**, not an approved full rig. The body, independent arms and hands, and finished acting are absent; known F/V grimace, lip stroke and teeth/tongue overlap defects remain.

## Bounded improvement committed
- evan-engine/review_acoustic_flags.py exports separately indexed waveform/spectrogram images for each flagged acoustic word, with acoustic and independent anchor boundaries, phone sequence, 2-second-ish local visual evidence window, CSV and JSON decision records, and a human review checklist.
- Fail-closed guard: acoustic status is required; fallback-only plans are rejected; optional --expected 18 rejects a changed count; no word gets marked accepted by software.
- evan-engine/test_review_acoustic_flags.py uses synthetic 16 kHz audio to validate indexing, evidence rendering, the pending status and the fail-closed guards. Three focused local tests passed in a separate runtime. These tests are not a review of the real Evan narration.
- Neither the real saved 22.05-second WAV nor its full speech-plan JSON was available here. **The 18 flagged word boundaries remain unreviewed.** Their reported count is from the parent checkpoint, not a freshly executed real-audio audit.

## Reproduce on the Mac with the local speech plan and recording
From evan-engine (with the existing painted Python requirements):

    python review_acoustic_flags.py /absolute/path/speech-plan.json /absolute/path/evan-16000-mono.wav /absolute/path/outputs/cartoon-alignment-audit --expected 18
    python -m unittest -v test_review_acoustic_flags.py

Review all actual PNGs, listen normal and slower speed, compare mouth consonant contacts, inspect pause after "favicon", and write accept/revise/unresolved decisions. Re-run alignment or manually correct only after timestamp-level evidence. This audit script does not silently modify a speech plan.

## Next concrete work
1. On the authorized local Mac worktree, locate the exact recording and speech-plan files referenced in ACOUSTIC-SPEECH-ALIGNMENT.md, run the 18-word review packet and critically inspect every disagreement. Do not assume word/phone coverage implies accuracy.
2. Inspect design-sheet-v1.png, setup-v1.png and speech-poses-v2.png at native resolution. The GitHub text connector cannot decode binary PNG blobs in this environment; source-art approval cannot be determined remotely.
3. Redraw/register truly independent jaw, oral interior, teeth and tongue layers; fix documented 0.3125, 0.583 and 0.708 s defects. Keep source plates distinct from registered working rig components.
4. Create real head/neck/torso/upper arm/forearm/hand layers with hidden shoulder/elbow overlaps and independently animated joints; add useful point/open/explain/relaxed hand poses and discrete held facial expression controls. Render a staged Rovor narration shot with official branding at **normal and slow speed**, inspect frame-level defects and only then consider polished-cartoon review.
5. Preserve main, V3/V4, approved symlinks/updater, and native Moho files. Do not launch or probe Moho unattended. Keep commits on development branches. Never merge/deploy without approval. Do not stop/disable the existing automation: finished milestone is NOT ready.

## Status
A speech-review tooling milestone only — **not** a finished cartoon animation, validated real-audio alignment or studio-quality result.
