# Evan: an actual independently controlled lower-lip paint plane

A genuinely separate lower-lip drawing now exists and is loaded by an eight-plane review construction. Its thickness can change while the jaw, crown, upper lip and every other plane remain fixed. This is a component milestone in development, not narration-ready character acting or accepted F/V anatomy.

## Source artwork and registration

Built-in image_gen generated two transparent1254-square source plates from the clean jaw underpaint and selected cartoon design sheet. V1 was too plump. A targeted V2 edit reduced thickness while retaining the top curve/endpoints. Full-resolution opaque alpha composites were inspected; original PNGs/alpha and exact prompts/input hashes are saved in evan-character/cartoon-v1/lower-lip-pressure-v1/source. No threshold, color-key or alpha cleanup.

register_lower_lip.py reuses contact_matrix for one uniform2-corner parent:source418,789/768,789→native198,321/274,320.5. Neutral center592,821 maps235.829,327.700; residual .34552px versus the AUTHORED neutral proposal236,328. This is not measured anatomy or a contact-pose accuracy claim. Contact/release geometry deliberately deforms the neutral drawing. Half-alpha crossings measure the native top-edge UV guide only; they never replace source pixels.

Registered Lower-Lip-Candidate.png is actual lower-lip-only paint, with no jaw, cavity, teeth or full-face swap. Source plates, registered candidate and posed working-review material remain explicitly distinct. The simplified jaw underneath retains its separate2.4634px registration limitation.

## Independent component and actual layer assembly

LowerLipPlane accepts nine left-to-right arch points and pressure0..1. Direct source correspondence tracks supplied width/top curvature. Pressure currently compresses thickness from100% to60% below the contact edge. This is an authored pressure PROXY, not designed roll/tuck or calibrated tissue behavior; a shortcut comment records that limit. Invalid/nonfinite arches and pressure reject. No temporal filtering, source recoloring or opacity gating.

render_lower_lip_pressure.py reuses LabiodentalConstruction, substitutes the existing clean jaw and inserts the actual lip plane. Order:neck, drawn skin underlap, cavity, fixed incisors, jaw skin, independent lower lip, upper-lip cap, upper-face/cheek wings. The lip is in front of the crown/lower jaw, with cap and face in front where appropriate. The existing authored outer-arch1.1px ink margin is removed for the lip contact guide. Coordinates/order remain drawing proposals, not accepted contact anatomy.

This is EIGHT actual nonblank painted planes, with jaw skin and lower lip genuinely separate. No blank artist-template promotion, no extra default head/profile and no native Moho bones. Mouth width/cap/crown remain fixed in this restricted mechanical study; it must NOT replace the full continuous narration driver with a two-pose adapter.

## Rendered checks and artistic judgment

outputs/evan-cartoon-lower-lip-pressure contains48normal/192mutedquarter frames at1280x720/48fps, fully decoded. The SILENT authored cycle first changes pressure with jaw locked, holds, releases pressure ahead of jaw opening, then returns. Each of the seven OTHER planes is byte-exact across all48 A/B pairs. Loop native endpoints exact. All48native mouth details, native head samples and full comparison frames were inspected against the selected cartoon sheet. No independent continuous-playback acceptance claimed.

Eight-Plane-Pressure.psd and Eight-Plane-Release.psd contain the eight actual posed pixel planes. Reload premultiplied mean errors .0250850/.0248891 per255; not a fully expressive/native rig. Eight sampled native mouth regions min alpha255; coverage is not lip-anatomy evidence. Two focused tests pass for thickness response, near-fixed top contact(within .5px sampling), unchanged source/arch and bad-input rejection. No studio-quality inference.

Visually, the thin warm rim adds a little lower-lip volume without the rejected heavy second crease. Pressure is subtle at native size and mostly changes thickness; release still reads as a shallow wedge. Upper lip remains straight/hooked, incisors lack convincing lower-lip wrap, face/chin/neck joins remain angular and eyes/brows are static. A convincing entertaining performance still needs coordinated roll/tuck, expressions, staging and animator review. CPU raster is adequate for proofs; source construction/animation design is limiting.

## Next

Use the independent lip with the full continuous oral arch, while cleanly separating upper lip/incisors from the carrier and coordinating F/V-to-vowel release. Keep all original voice/phoneme/alignment uncertainty and prior failed adapters. No narrated integration this pass, no new timing-accuracy claims, no body/staging expansion until the face works. Preserve main/V3/V4, approved releases/updater and native Moho; no merge/deploy or Moho operation.
