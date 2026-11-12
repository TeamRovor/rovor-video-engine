# Guided jaw exposure: a source component, not a finished facial rig

A fixed guide produced a separate painted jaw/lower-lip source at the intended native scale. The first version painted a closed smile inside the jaw and was rejected. The second removes that line and places a peach lip roll on the upper alpha edge. Original source alpha is retained. The component has no enclosed mouth or neck; its lower lip and jaw remain ONE combined painted plane, not independently drawn lip/jaw surfaces.

## Registration and assembly

Canvas normalization places the generated source into native window [128,288,384,448]. Four sampled 50%-alpha edges land at -1/-1/+1/+2px relative to authored left lip/lip center/right lip/chin guide positions. This is better placement than the preceding unregistered source; it does not establish correct anatomy, overlap or quality. Source canvas dimensions changed during generation and the tool redrew the jaw, so pixel-exact invariants are not claimed. Original files remain untouched; derived native part uses premultiplied resampling, no color key or opacity extraction.

A review-only surface uses the existing lip and independent chin controls on a grid mesh. The lip can move while the chin row stays fixed, and chin motion leaves the lip edge fixed. The first linear lip field created an unintended V during opening. A rounded field corrects that code defect while retaining the same center/corner targets. All final film frames use the rounded field. Four control tests pass, including refusal to reuse a stale painted target on unsupported full F/V. That full F/V jaw assembly is not implemented; the rendered excerpt contains no full F/V contact.

The old face is partitioned by a placeholder guide polygon. This is NOT complementary artist-painted upper-face, cheek or neck overlap. It visibly creates a cheek seam, tonal mask, silhouette remnants and exposed overlap around the jaw. Lip volume is too large/shaded for the selected clean cartoon direction, and the tongue remains prominent. Opening is rounder after the field correction, but mouth/corner construction remains weak. DO NOT promote this assembly or hide the seam with an opacity wash. Passing mesh/placement checks does not make it appealing or studio quality.

## Render evidence

Normal comparison: 60 frames at 1280x720/48fps, source frames714–773 inclusive (14.875–16.125s). Native 512px heads; quarter-speed muted comparison240frames/48fps. Both films fully decode. The original mono16k narration crop contains exactly20,000samples (238000:258000), with exactly20,000decoded samples in the normal film. AAC is not waveform-identical. All final meshes have positive triangle area; minimum doubled area34.112396. Upper288rows remain pixel-exact to baseline throughout. Consecutive736–743frames and native738/741/742 inspected. No independent listening or continuous-playback acceptance.

## Scope and next work

Source/render tooling only; existing head/scene defaults, main/V3/V4, approved releases/updater and native Moho projects unchanged. No Moho launch. No word/phone boundary edits; all18previous flagged acoustic regions remain visually reviewed with exact boundaries unverified. No new staging or branding changes. Normal/slow prior films stay archived.

Next obtain genuinely complementary upper-face/cheek/neck overlap and smaller, flatter cel lip-roll drawings, using the same registration guide. Keep the jaw source as a rejected assembly reference until those interfaces are designed; do not continue scalar placement or opacity repairs. A character artist/animator redraw and performance review are still needed. The CPU can render this proof; hardware is not the missing artwork. Full polished milestone remains incomplete, automation active.

Sources: evan-character/cartoon-v1/guided-jaw-v1. User deliverables: ../../outputs/evan-cartoon-guided-jaw.
