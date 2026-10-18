# Rovor V14 — reusable contact physics + art readiness gate

**Status: engineering upgrade accepted for development; generated painter animation rejected for artistic quality.** This package does **not** produce a finished film, a new episode, or a publishable animation. The last verified long-form review remains **V12, [0,156.2833) seconds**, 59.5% of narration covered by preliminary blocking, **0% claimed studio-quality approval**.

## Why this was built

The V13 seven-second pilot technically passed its tests but still looked like a basic presentation puppet. The previous illustrator hard-coded a couple of blue painted shapes. Its elastic elbow formula could make a long arm or awkward hinge. The artist complained about a roller nowhere near the wall; a successful timestamp test does not address that.

We therefore separated **physically consistent 2D tool effects** from **artist-authored character performance**. The physics may be reused with a new, professionally drawn character. The current V13 painter artwork should **not** become the studio's default reusable rig.

## Files

- `physical_paint.py`: independent, reusable 2-bone IK with fixed segment lengths, world-space tool contacts, off-wall clearance, finite wall bounds, and persistent roller-deposited paint masks. New passes are read from actual contact sampling, not from independent blue rectangles.
- `painter_contact_v14.py`: the seven-second legacy V13 engineering fixture adapted to use the shared physics. **It looks worse in some arm poses; it is not a creative-approved animation.** It is included to prove and test scene integration, not for final production.
- `test_physical_paint.py`: 13 physics, renderer and anti-regression tests, including pixel sampling of the actual rendered SVG and intentionally broken tool states.
- `layered_art_gate.py`: a separate art readiness check. Validates original unique RGBA pose files and SHA-256 references, required body/hand/face layer registration, the pose coverage, portrait/landscape coverage, and independent human art/performance signoff. The software cannot determine whether a drawing is attractive. No test can substitute for human review.
- `test_layered_art_gate.py`: eight tests including missing artwork, duplicated poses, changed source bytes, unsafe paths, cropped portrait, absent visual approval.
- `V14-art-status.json` and `V14-art-report.json`: the actual V13/V14 source currently fails visual readiness; **ART_NOT_READY**.
- `V14_Contact_Physics_Comparison_NOT_ART.jpg`: factual screenshot comparison. Existing V13 is already rejected, V14 fixes some physical causality but the automatically posed elbow is obviously unnatural. Do not turn this into a trailer or a promoted video.

## Reuse on another video

1. Select and hash the permitted **original** audio, not a test voice. Do not put private narration in GitHub or this ZIP.
2. Draw / register the source character's actual hand, arm, head, torso and body poses. For action scenes, include an original three-quarter working view and distinct acting poses, not seven renamed identical PNGs.
3. Write a per-frame `Pose` source with physical coordinates and contact status; evaluate with `ContactPaint` for relevant rollers/brushes. For other props add a specific physical renderer; do not abuse this *vertical roller* model for tilted or diagonal action.
4. Build the dialogue/action choreography and independently staged landscape and portrait art. Sound effects only on verified visible actions.
5. Run the physics tests and full-frame audio checks. Then run the art gate. Human normal-speed review of silhouettes, expressions, poses and story is always required. The art gate must **fail** on the current V13 fixture.
6. Only after passing a strong visual review should the material advance to chapter rendering. Never call engineering coverage artistic completion.

## Test commands

```bash
python -m unittest -v test_physical_paint test_layered_art_gate
python layered_art_gate.py V14-art-status.json --out V14-art-report.json
python layered_art_gate.py V14-art-status.json --strict   # expected exit code 2: NOT READY
```

## Limitations and deliberately unapproved behaviors

- Exact 2-bone length constraints alone **do not produce attractive limb articulation**. This V14 demonstration's elbow spikes upward and looks wrong in several poses. **Reject the drawing and work from an artist's key-pose line of action instead.**
- The paint model is a deterministic flat 2D vertical wall contact mask. It is not a simulation of roller nap, wet material, shadows, drips, plaster microtextures, fabric or 3D perspective. Its output is still visually simplistic.
- Reusing `painter_contact_v14.py` as a character template is explicitly prohibited. Use its geometry integration only.
- `V14-art-status.json` is an incomplete, truthful art manifest, not a fabricated set of human approvals.
- Established original Evan appearance (dark tousled hair, sunglasses, navy shirt, black tie) is unchanged. This scene is a secondary hypothetical painter, not a fabricated Rovor client.
- The V12 2:36 reviews, earlier voice recordings, `main`, and the draft PR's historic revisions were **not merged or overwritten**. No spend, no publication.

## Concrete next creative milestone

Produce a **genuinely well-drawn single painter key-pose sheet** with believable anatomy and expression (seven distinct work poses, source-editable separate limb/hand/facial layers), inspect silhouettes at full size, build the Moho or equivalent layered deformation rig, then run this physical contact driver against that source art. A 6–8s pilot is only worth rendering after the drawing is appealing as a still. This is the art bottleneck, not missing computer render throughput.