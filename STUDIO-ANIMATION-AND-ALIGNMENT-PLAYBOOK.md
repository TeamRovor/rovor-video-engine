# Rovor cartoon animation — studio process and voice-timing upgrades

**2026-10-17.** Research-informed engineering playbook. This is **not a studio-quality certificate** and it does not claim Disney/Pixar collaboration or approval. Latest user direction: entertaining, expressive **2D cartoon Evan**, using the photograph only for broad identity cues; dark messy hair, sunglasses, navy shirt and black tie. The realistic painted style is superseded.

## Production insights and how to apply them

| Verified source/principle | Concrete Rovor rule | Acceptance evidence |
|---|---|---|
| Walt Disney Animation's animation process: acting, appeal, clear staging, timing, anticipation, follow-through and secondary action | Author *intentional* anticipations, readable held poses and different gesture styles; never use perpetual energy-driven joint wiggle as a substitute for acting | Muted viewing shows the idea and emotion before hearing the words; head and body accents occur on meaningful beats |
| Disney Animation's Layout and Final Layout: rough staging/camera blocking then tightening composition/cuts | Script -> shot board -> timed animatic -> director-authored beats -> silhouette/pose block -> final artwork/polish. Shot borders and on-screen marketing graphics need an editorial purpose | 4–8 s test understandable as stills and in silent playback; clean eyelines and screen-direction continuity |
| Pixar in a Box story process: story reels, timing and Editorial | Record / lock dialogue and build animatic before high-cost character cleanup; keep mouth timing and acting direction independently editable | Audio and shot timelines report the same time zero, duration and fps; after editorial change the rig can be re-rendered |
| Disney Animation rigging: expressive controls co-designed for animators | Actual registered separate upper/lower face, jaw, teeth, tongue, eyebrows, neck, upper/forearm/wrist/hand, hidden limb overlaps and mouth contact landmarks | Independent 2D drawings with no double strokes at critical F/V, L, P/B/M and transitions; hands interpolate anatomically, not just dissolve |
| MFA 3.x: speaker-aware acoustic alignment; measurement against manually annotated word/phone boundaries | Keep current PocketSphinx planner in place; *optionally* run modern MFA as an independent benchmark on real recordings. Do not assume model agreement is ground truth. Convert reference measurements into absolute start/end errors | Human evidence on disputed intervals, median and p95 boundary deviations, no unsupported confidence scores |
| MFA alignment quality guide: runs of 10ms phones, duration anomalies, acoustic levels can expose weak alignment | Audit the actual exact WAV, very short phone runs, interval containment, low energy, word-anchor discrepancy; none alone automatically edits the speech plan | A review report with recording fingerprint, flagged intervals, reviewer notes, evidence image and unresolved status |
| WhisperX paper/project: VAD plus wav2vec2 alignment; it documents nonalignable tokens/overlap limits | Potential second opinion for word boundaries when language/model license and resources permit. Preserve acronym and brand pronunciation dictionary; do not silently use unaligned words | Provenance of every backend, missing tokens called out, disagreements surfaced rather than averaged away |

## Two independent but synchronized timelines

**1. Sound-time is measured.** Store the exact master audio checksum, sample rate, mono proxy derivation, dialogue offset in frames, transcript + project-specific pronunciation dictionary, forced-aligned phone start/end times, speaker ID and fallback status. Lip seals, rounded vowels, F/V lower-lip contacts, L tongue contacts, silence relaxation and coarticulation use the six existing control channels. Preserve plosive closures even when the waveform is quiet. Never convert model scores into a percentage confidence. For project phrases like “Rovor” or “favicon,” provide deliberate pronunciation entries.

**2. Performance-time is directed.** Record each shot beat as a named expressive intent with a time of arrival, a finite anticipation duration, a hold and independently keyed head, body, eyebrows, arms, wrists and hands. The mouth timeline does **not** drive every joint; nor should word loudness automatically imply anger or excitement. The animator may adjust head and hand accents based on editorial intent. The stage is still a construction blockout until an artist approves finished poses.

`evan-engine/studio_performance.py` and `studio-direction-example.json` implement explicit, held acting cues. Direction JSON is *editorial authored*; the example is a synthetic performance fixture and must not be relabeled as real narration. The existing `cartoon_rig_blockout.py` gains optional `--direction` without changing old callers or its continuous acoustic control API.

## Voice alignment quality gates

`studio_alignment_qa.py` is a **diagnostic** companion to `review_acoustic_flags.py`. It verifies word/phone ordering, phone containment, repeated <=11ms phones, recording duration, aligned word amplitude anomalies and discrepancy with independent word estimates. A PCM16 WAV is read directly; the fingerprint hashes the *decoded sample bytes*, not a claim about the full container file. An optional reviewer packet explicitly stores `accept`, `revise` or `pending`. A `revise` decision cannot become resolved until the underlying speech plan is corrected and re-audited.

An optional `--reference` JSON must declare `"provenance":"human-annotated"` and contain word `scriptIndex/start/end`; the tool then reports median and 95th-percentile absolute boundary errors and fraction within **50ms**. **50ms is a proposed internal QC benchmark, not a universal Hollywood requirement.** Do not mark performance ready merely because numerical test thresholds pass. A recording is required to assess audio evidence, and flagged boundaries (18 from prior checkpoint) require individual inspection. Phone-level gold annotation would be needed for genuine phone-boundary accuracy measurement.

Sample local commands:

```sh
python evan-engine/studio_alignment_qa.py path/to/speech-plan.json path/to/qa.json \
  --wav path/to/evan-16000-mono.wav --review path/to/flag-review/review.json
python evan-engine/review_acoustic_flags.py path/to/speech-plan.json path/to/evan-16000-mono.wav \
  path/to/flag-review --expected 18
python evan-engine/cartoon_rig_blockout.py path/to/shot-output --direction evan-engine/studio-direction-example.json \
  --speech-plan path/to/speech-plan.json --fps 24 --frames 96
python -m unittest -v test_studio_performance test_studio_alignment_qa test_cartoon_rig_blockout
```

**Review recipe:** Confirm the WAV/plan are from the *same take*. Inspect each flagged word against spectrogram + waveform at normal and slowed speed, including after “favicon” and P in “open.” Confirm consonant contacts in actual artwork. Check sustained vowels, inhalations, silence breaks, and any word whose sound merges with its neighbors. Compare proposed model A vs B vs a manually marked reference if available; never substitute model consensus for a reference. Fix wrong boundaries explicitly and regenerate the six normalized speech controls, then visually inspect at both normal and slower speed.

## Review/delivery gates

- **Source and rig gate:** full-resolution artwork matches the accepted cartoon direction; contours and outlines do not swim; independent assets remain properly registered across poses; correct Rovor mark is **verified**, not a synthetic placeholder.
- **Voice gate:** reference take and checksum present, flagged regions reviewed, no unresolved structural errors, actual lip sealing/teeth/tongue anatomy at critical F/V, L, P/B/M and rounded vowel transitions. Speech controls at render FPS carry explicit source info.
- **Acting gate:** silent performance communicates the point; readable silhouettes, anticipation, holds and follow-through; interesting acting does not mean constant movement; hands never become stiff spokes. Head vs body motion is intentionally offset, not procedural noise.
- **Shot gate:** useful composition, safe crop at horizontal/vertical output, editorial timing, no unmotivated camera movement, sharp native-resolution frames, readable branding, no generic stock footage.
- **Review gate:** inspect head detail at 100% and normal playback as well as slow motion; annotate defects per frame/timecode; require human signoff before calling work polished. The test render remains an engineering blockout until accepted.

## Latest development status

The authored-acting fixture now renders at 1280x720, 24fps in approximately 4s normal and 8s slowed review films. It works with existing hardcoded synthetic mouth in the absence of real speech plan; **not a new accurate narration-sync film**. Visual inspection still finds stiff limb silhouettes, rough fingers, rigid mouth anatomy and placeholder branding in this environment. Voice metrics tested only on synthetic PCM; real Evan 22.05-second recording and 18 flagged regions **not reviewed** here. The local baseline is a design experiment, not a polished showreel.

Preserve main, all V3/V4 approved materials/symlinks/updater and Moho projects. No unattended Moho launch; no merge/deploy. Bounded development commits only. Keep recurring milestone work active until an actually polished *cartoon* animation merits review.

## Primary sources

- Walt Disney Animation, Animation: https://www.disneyanimation.com/process/animation/
- Walt Disney Animation, Rigging: https://www.disneyanimation.com/process/rigging/
- Walt Disney Animation, Layout: https://www.disneyanimation.com/process/layout/
- Walt Disney Animation, Story: https://www.disneyanimation.com/process/story/
- Pixar in a Box, Storytelling: https://www.khanacademy.org/computing/pixar/storytelling
- Pixar in a Box, Animation: https://www.khanacademy.org/pixar/animate
- Montreal Forced Aligner, Align with an acoustic model: https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/workflows/alignment.html
- Montreal Forced Aligner, Evaluating alignments: https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/implementations/alignment_evaluation.html
- Montreal Forced Aligner, Analyzing alignment quality: https://montreal-forced-aligner.readthedocs.io/en/latest/user_guide/implementations/alignment_analysis.html
- WhisperX, source and documented limits: https://github.com/m-bain/whisperX