# Tongue/contact identity separated from jaw geometry

The rooted tongue study still used the tongue-viseme weight H to drive a wide-open mouth. During “little globe” this produced repeated large openings rather than a modest contact with a raised tongue. This optional study separates articulation/material identity from render geometry and eases the geometry across neighboring samples of the existing word/phone/audio plan.

No generated artwork, source layers, phone boundaries, recording or planner weights change. No new pronunciation prediction or speaker calibration is claimed. Existing H remains shared by L/TH/DH; their distinct tongue contacts and dark/coda L still need designed artwork/controls.

## Construction

LayeredCartoonHead.weights now accepts an optional geometry_weights vector. It drives mouth landmarks, aperture and face-skin/jaw deformation. The original weights still drive tongue lift, F/V material blending and lip/teeth visibility. ExpressiveCartoonHead forwards the optional vector while retaining its brow controls. Omitting the vector retains the original rendering exactly.

SeparatedCartoonHead uses the existing planned_weights at five times spaced 1/48 second, with binomial weights [1,4,6,4,1]. This is an authored symmetric 83.3 ms window, with up to 41.7 ms anticipation/release, not an estimated acoustic boundary change or a playback delay. Most H geometry contribution (75%) moves to the existing smaller B aperture, retaining 25% H geometry. The unfiltered tongue identity remains intact, so a strong contact no longer requires the full H mouth opening.

Current bilabial A and F/V G weights are reserved exactly in the geometry vector after filtering. The remaining weights share the remaining budget; a fully settled rest stays exact. This protects closures/contact releases from temporal smearing. Consequently some rapid mouth closures remain. The present split controls mouth aperture and chin through one geometry vector; a fully independent jaw-bone versus lip-seal deformation is still future work. This is not an anatomical simulation.

SeparatedCartoonSceneBody / render_cartoon_scene.py --separated-jaw puts the new head on the existing continuous-wrist body, compact independent index, neck/collar and word-anchored acting. Original modes/defaults remain baselines. There is no flattened character replacement or native Moho edit.

## Evidence and review

Outputs ../../outputs/evan-cartoon-separated-jaw. Native-head comparison covers recording time 2.5–5.0 s (120 frames at 48 fps), including “little globe … your logo” and its settle. Branded shot covers 86/48–5.0 s (154 frames), adding the phrase lead-in. Normal clips retain original audio; quarter-speed versions are muted (480/616 frames). All four completed films decode cleanly at 48 fps. Quarter-speed playback repeats the source frames rather than inventing new in-betweens. The waveform/spectrogram/controls plot shows unchanged tongue and closure weights alongside old/new aperture. Separated-Control-Track.json exports all 489 existing scene-clock samples for review/integration; it is not a native project or calibrated motion capture.

Across the 2.5–5.0 s comparison, the largest frame-to-frame aperture step falls from 14.8564 to 10.5905 native pixels. The largest remaining changes occur at the bilabial closures after “globe” and “up”; they were deliberately preserved. This numeric reduction does not establish smooth acting or correct lip-sync. All 489 scene samples retain positive skin/oral mesh orientation (minimum signed doubled triangle area .0544026); contact-weight difference is exactly zero. Seven actual-time rooted-tongue baseline renders remain pixel exact after the optional hook extraction. 40 affected head checks pass, including closure/rest preservation, nonmutation, tongue change at fixed jaw geometry and mesh orientation. Tests are construction safeguards only.

The selected cartoon design sheet was re-inspected. Native 512-pixel head pairs show a smaller contact opening while the tongue stays raised, preserving hair/glasses/brows and the selected cel-cartoon direction. Remaining defects: narrow lips pinch; the rounded mouth remains a warped raster drawing; an ear-adjacent cheek mark/deformation remains; tongue blade becomes compressed in shallow apertures. Shared H cannot distinguish L from TH/DH. The restrained opening is preferable to the old repeated yawn-like pose but still needs an animator's performance judgment. Continuous playback/listening acceptance is not claimed.

The 18 word-anchor flags retain their existing waveform/spectrogram visual review with exact boundaries unverified. The current plot revisits tiny/little context without using jaw smoothing to conceal or relabel timing uncertainty. Retain acoustic annotations until listening/ground-truth evidence supports a correction.

## Next work / safeguards

Critically inspect the completed normal/slow shots, then design clean shallow-contact and rounded-vowel contours and separate L/dental tongue controls. A separate jaw/chin envelope under lip seals may improve remaining contact motion without delaying closures. Keep hand rest/neighbor-finger drawings and shoulder cleanup on the backlog; static legs and missing eye/blink rig also remain. A human character artist/animator is still needed for final anatomy and acting approval. Native raster detail and CPU mesh rendering constrain iteration; hardware cannot provide missing drawings.

Main, V3/V4, approved releases/updater and native Moho projects remain untouched. Development branch only; no merge/deploy or unattended Moho launch/probe. Full polished cartoon milestone is incomplete; heartbeat remains active.
