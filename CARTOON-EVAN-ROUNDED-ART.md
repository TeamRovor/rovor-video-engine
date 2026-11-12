# Rounded mouth artwork / registered component study

The old wide cavity drawing became jagged and pinched when squeezed into rounded vowels. This study generates a clean rounded mouth in the selected Evan cel-cartoon language, registers separate cavity and lip-rim components, and keeps existing teeth/tongue as independently rendered layers. It is an optional development candidate, not approved production artwork or studio-quality animation.

## Source versus working components

Built-in imagegen edited the isolated old cavity component, using source/design-sheet-v1.png only as the cartoon style/character reference. No new realistic portrait or surrounding skin patch was requested. Exact prompts and references are versioned in round-source-v1. The first output's upper-left spur was corrected in one targeted edit; rounded-mouth-v2.png is the chosen raw source. Both generations remain available. The raw source plate is not a rig or registered animation frame.

build_rounded_oral_art.py fits raw alpha bounds [487,440,820,851] to E source space [211,320,240,366]. This affine fit uses canonical controls, not traced anatomical correspondence. The generated intended-solid interior is predominantly alpha 253; the working builder snaps alpha >=250 to 255 while preserving antialiased edges. Four-times registration supersampling avoids simply skipping high-resolution source pixels. A colour-selected filled cavity mask separates cavity and rim, with 12 source-pixel underlap to prevent an internal transparent seam. The independent interior matte clips the existing teeth/tongue behind the rim. Source/context/prompt hashes, matrix and parameters are recorded in round-rig-v1/manifest.json; animationReady remains false.

Runtime RoundedArtCartoonHead extends BoundedCartoonHead. Each new pixel component is warped separately from E space to the existing continuous oral mesh. Their premultiplied assembly interpolates with the old oral material using current active rounded-phone identity. An early trial used the width lead/release mixture and retained too much old outline during an already rounded vowel; current art identity follows the current phone mixture instead. Width easing remains unchanged. Rounded art also suppresses teeth visibility independently of audio amplitude; tongue visibility is clipped by the new cavity matte. These are authored cartoon controls, not measured anatomy.

LayeredCartoonHead gains default cavity/interior/clip hooks without changing default output. RoundedArtCartoonSceneBody / --rounded-art integrates the candidate with the anchored face, separate jaw/contact controls, articulated continuous-wrist body, separate index and official branding. No full-head/body sprite replacement was used. Old modes and defaults are preserved.

## Review / evidence

Outputs ../../outputs/evan-cartoon-rounded-art. Native-head before/after and branded integration cover recording time 2.5–5.0 s, “little globe … your logo” and the pause: 120 normal frames at 48 fps, original audio; muted quarter-speed versions repeat those frames to 480 frames. All four films decode cleanly at 48 fps. Exact source prompts, chosen raw PNG, registered components/matte, manifest and an editable two-layer E-space PSD are included. The PSD reopens with mean premultiplied difference .0002743/255; it is a source construction plate, not a complete rig or native Moho project.

57 affected checks pass: six new art/occlusion/coverage checks plus 51 prior head checks. Non-rounded pure controls remain exact, source cavity/rim preserve opaque coverage, full rounding hides teeth at low energy, future width cues cannot override contacts, tongue edits remain inside the cavity matte, and geometry/nonoral pixels are retained. Seven actual-time Bounded baseline images remain pixel exact after hook extraction. These establish compatibility and layer construction, not animation quality or phonetic accuracy.

The selected cartoon direction and native 512-pixel head pairs were inspected. The held rounded silhouette is smoother and has a softer designed lower-lip edge. The original tongue remains separate and moving. The lead-in still has a soft brown/double-edge appearance where the old/new contours mix; the affine canonical fit is not yet a clean artist-designed shape correspondence. The new lower-lip volume is heavier than the concept's restrained tiny O and needs animator judgment. Narrow B/contact shapes and the gray FV plate remain unchanged. Do not describe this as a polished animation breakthrough. Keep it opt-in; do not promote it to defaults on the strength of tests or one held pose. Continuous playback/listening acceptance is not claimed.

Audio, phone/word boundaries, geometry targets and planner weights are unchanged. The 18 word-anchor flags retain their waveform/spectrogram visual review with exact boundaries unverified. The comparison uses the same sample-clock waveform; this artwork pass supplies no new timing-accuracy evidence.

## Next work / limits

Refine actual contour correspondence through rounding entry/release; avoid solving it with a flatter full-character replacement or more transparency layering. Design clean shallow contacts and distinguish L/dental tongue construction. A human character artist/animator is still needed for final anatomy, appeal and performance approval. Softer resting hand/neighbor fingers, shoulder linework, static legs and missing eyes/blinks remain open. CPU raster rendering is slow, and native source detail is limited; hardware cannot supply missing drawings.

Main, V3/V4, approved releases/updater and native Moho projects remain untouched. Development commits only; no merge/deploy or unattended Moho action. Full polished cartoon milestone remains incomplete and the heartbeat stays active.
