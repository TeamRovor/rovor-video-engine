# EVAN — Visual rebuild after rejected animation previews

**Creative authority:** Rovor user's established direction, not a generic reference animation, stock-video system, or the recent outside suggestions. **2026-10-17. Status: ARTWORK NOT APPROVED.**

## Decision

The existing `cartoon_rig_blockout.py` is no longer a candidate for the character's final drawn appearance. Its useful timing, phoneme, hand-pivot, and shot-control algorithms may remain as **private engineering components**; their visible procedural SVG shapes do not form the character artwork. Six-control jaw/lip articulation and audio evidence tools stay available. Preserve all previous branches as archives and do not rewrite main, V3/V4, approved updater/symlinks, or native Moho projects. No unattended Moho launch.

The next worthwhile production artifact is **one excellent, recognizably Evan, artistically consistent hero frame**, then a short 2–3-pose silent acting study with that **same registered design**, and only after that a narrated animation. Do not make another full-frame film out of rejected temporary drawings. Do not accept illustrated *pictures of* layer stacks/animation timelines as actual layers or motion. An apparently polished collage containing mock video players is not a tested video.

## Evan's unambiguous visual identity

- Original, entertaining **2D cartoon** host; approachable and charismatic, expressive, visually clean and readable in a phone-sized video. Accessible personal-storytelling energy, **not an imitation** of a particular creator's drawing.
- **Dark tousled hair, sunglasses, navy collared shirt, black tie**. These are established Rovor cues. Blue eyes or a hoodie are **not** substitutes. Do not let an image model replace the identity or invent a different mascot.
- Strong appealing shape language: distinctive hair mass and face silhouette, intentional 2–3-level cel-value hierarchy, smooth but not plastic face contours, disciplined line weight, simplified sleeves and hands, consistent face proportions across expressions.
- Genuine expression with sunglasses: brow/glasses angle, head orientation, mouth corners/cheeks, jaw, shoulders, torso, hands and staging. Avoid enormous generic cartoon eyes in place of his sunglasses.
- Genuine performances: thoughtful listening, explanation, playful skepticism, confident emphasis and amused reaction. Hold accents instead of perpetual automatic bobbing. Avoid stiffness and overproduced camera shake.
- Official **Rovor Digital** logo asset only when verifiable. No improvised brand mark promoted as official.

## Target opening shot and artistic acceptance

**Frame A — establishment:** Well-drawn 3/4 Evan at a tasteful, uncluttered original Rovor scene. Eyes implied behind sunglasses, approachable grin, unmistakable tie and shirt, hand resting naturally. Strong silhouette and clear face at 360p; no poster-style UI clutter or random logo copies.

**Frame B — explain:** Weight shifts slightly toward listener, one hand opens with naturally staged finger arcs and the other rests. Intentional head lead, shoulder-to-elbow-to-wrist chain, tiny delayed settle. Not a full-body pivot from one rigid stick to another.

**Frame C — emphasis/reaction:** One controlled point or skeptical shrug, clear attitude and readable closed-mouth hold between speech. No finger spaghettis; no duplicated outlines at overlaps.

Review still A at **100% and small mobile scale** before B/C. Review B/C first as thumbnails and silent acting beats, then motion at normal speed and quarter/half speed. Bad silhouettes or mechanical gestures block production no matter how many tests pass.

**Production anatomy:** Consistent registered editable transparent layers for hair rear/front, fixed upper face, eyes behind glasses if needed, brows, glasses, jaw, upper/lower lips, teeth, tongue, oral cavity, neck, torso/tie, independent upper arms/forearms and genuine shaped hands. Draw hidden sleeve and cheek overlaps. Shared face geometry for expressions, not inconsistent swapped heads. Separate full-resolution backgrounds and props; never bake character to scene.

**Source continuity:** Start from `evan-character/cartoon-v1/source/design-sheet-v1.png`, `setup-v1.png`, and `speech-poses-v2.png` **at native size**, with source annotations and critical review. They are reference studies, **not independently registered production rig pieces**. The current text-only GitHub connector cannot read those binary PNG pixels. Do not guess that freshly generated figures are identical to the source.

## Audio, performances and integration

The current 22.05s Evan audio and 18 disputed word regions remain unverified in this runtime. Keep alignment controls separate from acting cues. Test M/B/P seal, lower lip touching upper teeth for F/V, raised tongue for L, rounded vowels and real breaths on the actual master recording; verify real waveforms and pronunciation. Do not use a silent synthetic film as a voice-sync demo. Phonemes drive mouth; director-authored meaning drives acting. Rhubarb/Moho switch exports and JSON/Lua are optional sidecars, not alternatives to actual art and verified lips.

## Safeguards added in this pass

`evan-engine/character_art_gate.py` checks the mechanical readiness of a *future* registered RGBA art package: complete independent components, each file's hash, shared canvas and pivots, unclipped alpha silhouette, no solid background or duplicate hand exposures, and no use of the wrong wardrobe or superseded direction *as manifest claims*. This does **not** magically classify what is in the pixels, so even a passing manifest always reports `animationReady=false`, `visualApproved=false`, `releaseReady=false` until visual inspection. It is a production-art prerequisite, not an animation-quality score. Never auto-approve generated artwork from its metadata.

Commands after properly DRAWN plates have been produced:

```sh
python evan-engine/character_art_gate.py \
  evan-character/cartoon-production/art-manifest.json \
  --report /tmp/evan-art-check.json
python -m unittest -v test_character_art_gate
```

No professional preview can be shown until the correct identity, actual registered art, real narration timing and visual acting checks are available. The recent generated off-brief concept-image experiments depicting a hoodie/no sunglasses and mock video panels are **rejected** and will not be added to the official assets. Keep the reject decision even if the images appear shiny.