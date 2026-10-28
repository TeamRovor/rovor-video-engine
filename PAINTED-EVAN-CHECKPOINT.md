# Evan cartoon: current checkpoint

## Direction and safeguards
Entertaining expressive 2D CARTOON; photograph is a loose identity reference. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Source plates are not working rig components. No studio-quality claims from tests or flattened figures.

Repo work/engine; development/evan-painted-rig; draft PR4 https://github.com/TeamRovor/rovor-video-engine/pull/4. Development commits only. NEVER merge/deploy without approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62 and V4=27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/approved symlinks/updater/native projects. Do NOT launch, restart or probe Moho unattended. Automation ACTIVE; polished milestone NOT ready. Notify only meaningful review milestone/completion/failure/action.

## Current task: neck-fringe correction motion validation pending
CARTOON-EVAN-COLLAR-MOTION.md / evan-engine/reviews/collar-motion-v1.json. PENDING worker9788: work/collar-motion-review/render.py renders15–17s(source360..407) into outputs/evan-cartoon-collar-motion. Expected48frames/normal2s/slow8s decode48/192; exactPCM240000:27200032000samples. DO NOT restart. Executed Source/ and Launch-Source-Manifest.json frozen.

Actual separated face and existing payoff_controls; opt-in trim_left_neck_stub only. Everyframe defaultfullstage must pixelcalibrate to payoff-continuous, originalframehash match, and newhead retain exact nativeoraljaw/audit plus neck/torso/armlayers. Stage differences confined to head. No new sourceart/actingcue/default/timing change. Previous10neck/payofftests remain passed; newrender guards are perframe assertions, not polishedacceptance.

NEXT: poll9788; require Verification.json and48/192decode. Run work/collar-motion-review/review.py; inspect all48native120x140joinpairs,12overview,4normal+2slow1280x720samples. Verify32000sample exactPCM and source/frame/film hashes. Fullspeech follow-up must evaluate532poses withtrim; preserve20closing/18unresolvedflags. Currentfullfilm stays payoff-continuous. Automation active/polished NOTready.

## Current bounded fix: original neck fringe ownership
CARTOON-EVAN-COLLAR-OWNERSHIP.md / evan-engine/reviews/collar-ownership-v1.json; outputs/evan-cartoon-collar-ownership/Review.html. Frame374held fullstage exactly calibrated; individualhead/neck/torso3xnative sheets identify a dangling ORIGINAL neck edge in headplane x208..213belowjaw. Split ownership formerly starts214. Torso collar is separate, not source of that tail.

Opt-in trim_left_stub extends onlyHEADalpha cut6pxleft, retaining neckmask/RGB/sourceplates. Bodyflag trim_left_neck_stub defaultsfalse. Pilots353/374/396fullbaseline exact; after changes23/38/32stagepixels, allneck/torso/armlayers and nativeoraljaw/audit exact. Inspected3native120x140joinpairs at3xnearest plus1280x720heldcandidate. Lower tail reduced; uppercollar/jaw contour remains.10neck/payofftests passed(1newpreservationtest withopaquefringe fixture,3jawoffsets). No correctedmotion/fullfilm acceptance yet. Frozen work/collar-ownership-review/{trace,candidate}.py and Source-Manifest.json. NO pending jobs.

NEXT: render2s15–17s correction component with actualseparatedface/trimflag/payoff_controls. Require48/192decode, allnativejoinpairs, exactPCM240000:27200032000samples, oraljaw andnecktorsolayer preservation/sourcehashes. Later fullspeech evaluation must cover532frames(allpose trim), notonly60payoff; preserve20closing and18timingflags. No extraacting/art/timing variant. Fullfilm stays payoff-continuous; automation active/polished NOTready.

## Current complete review: small-detail attitude integrated
CARTOON-EVAN-PAYOFF-CONTINUOUS.md / evan-engine/reviews/payoff-continuous-v1.json; outputs/evan-cartoon-payoff-continuous/Review.html. Workers68712(component) and55490(fullintegration)COMPLETED. NO pending jobs. Current branch development/evan-painted-rig only; polished milestone NOT ready.

Existing detail_event43–45now has stronger opt-in head/torso anticipation: extra head+.5/−3.2delay25ms,body−.15/+.85delay70ms; totalhold−4.9/+1.2. Existing14.34/14.64/15.34/15.95/16.78cue retained.13tests previously passed, including3new control/isolation/continuity and positive actualneckmesh/currentjaw trajectory480Hz. Head+registeredneck move, nativeoraljaw targets remain exact; delivery mouth pixels rotate intentionally. Arms/index unchanged before globalbodyrotation. No new art/cue/retiming/default.

Component14–17.25s:78frames/60updated345..404+18offcuePNGcopies, normal3.25s/slow13s decode78/312; exactPCM224000:27600052000samples. All60fullbaseline calibrations, nativeoraljaw/audit/torsoarm guards and brand/browser equality pass. All60nativecollar/jaw before-after pairs,18overview and4normal+2slow1280x720samples inspected; source/frame/film hashes verified. Existing tiny leftcollar nib persists; no broad new opengap/missingneck observed. See CARTOON-EVAN-PAYOFF-LEAN.md / payoff-lean-v1.json; frozen work/payoff-lean-review/{pilot,render,review}.py.

Fullfilm reuses60component frames; other492PNGs byte-exact to definition-continuous including20closing and earlierdefinitionbrows. Normal23s/slow92s decode552/2208. All552hashes, source/film digests and byte-exactfullWAV verified; AAC368000samples16k lossy. All18markers matchcurrent acousticplan,0cleared. Inspected22overview inclcueboundaries/final551, normal345/353/374/404/540 andslow1496/1616at1280x720. Rigidtorso/fixedfingers/sunglasses/limitedface and unaccepted independentlistening/realtimeacting still prevent polishedclaims. Frozen work/payoff-continuous-review/build.py and Source-Manifest.json.

The planned source-ownership trace identified the fringe and opt-in pilot correction above.

## Previous complete candidate: explanatory brows integrated
CARTOON-EVAN-DEFINITION-CONTINUOUS.md / evan-engine/reviews/definition-continuous-v1.json; outputs/evan-cartoon-definition-continuous/Review.html. Worker5341COMPLETED/no pending jobs. Reused114reviewed frame235..348 PNGs from component, other438byte-exact to filtered-continuous including20closing. No rerender, new source art, retiming or default change.

Full23s normal/92s muted slow fully decode552/2208. All552hashes, source snapshots, film digests checked; changed frames preserve outside-head and stage mouth pixels. Original full WAV byte-exact; AAC368000samples16k lossy. All18markers equal CURRENT acoustic plan; no flags cleared. Inspected19overview including235/348/349and551, normal234/248/268/348/540 andslow992/1392at1280x720. Brow lift reads modestly with held palm, no newly observed seam/oral defect. Reference design sheet was compared at full resolution: stronger torso attitude, hand variety and facial range remain missing; real-time/listening acceptance remains unverified. Polished milestone NOT ready.

The planned head/body ownership inspection led to the bounded pilot above. No automatic acceptance from decode checks.

## Latest acting improvement: definition brow component reviewed
CARTOON-EVAN-DEFINITION-BROWS.md / evan-engine/reviews/definition-brows-v1.json. Existing word-anchored palm cue now has opt-in registered brow lift5/7pixels, tilts+1/-2; same9.79prepare/10.31arrive/14.01hold/14.54settle. No new artwork, timing, oral/grin, hand cue or default changes. Ten relevant tests passed previously.

Worker31087 COMPLETED. outputs/evan-cartoon-definition-brows/Review.html: source9.5–14.75s,126frames/114changed+12off-cue copies byte-exact, normal5.25s/slow21s fully decode126/504. All114baseline fullstage calibrations, nativeforehead-only/oraljaw audit/mouth/body/arms/brand guards passed. All126frame hashes, movie digests, launch/finalsource manifests checked. ExactPCM152000:23600084000samples verified; AAC lossy.

Inspected all114native before/after pairs at original195x85,18overview and4normal+2slow1280x720decoded samples. Raised brows support the explanatory palm without observed repair patches, shifted glasses or oral changes. Modest delivery-scale accent; left brow partly hidden by hair. Sunglasses/fixed fingers/restrained torso and lack of independent listening/real-time acceptance still prevent polished claims. Component fullfilm integration is now completed above; no pending jobs.

The planned integration is complete above. Automation remains active.

## Acoustic decisions retained
P→AO review(CARTOON-EVAN-AO-RELEASE-REVIEW.md / outputs/evan-cartoon-ao-release-review/Review.html): retain current continuous release. Low-energy endpoint20.425 is bracketed by24fps490/491, not an accepted vowel onset. Native9.50/27.25px at20.416667/20.458333 projects approx4.52/12.96delivery pixels, excluding small rotations. Existing motion/timing unchanged; no threshold-driven gate. Context20–21.25normal1.25s/slow5s30/120frames/PCM320000:34000020000samples verified;7decoded landmarks inspected,2at1280x720.

Four concerns B184/HH195/W207/AO228 have exactPCM/waveform/spectrogram/current-target traces and16decoded landmarks in outputs/evan-cartoon-low-energy-phone-review/Review.html.1120geometry samples480Hz. B quiet gap0.15px/full contact compatible stop closure; HH retains high-frequency energy; W weak periodic energy/4.61–5.20px gap; AO low-energy prefix opens1.47→13.69native pixels. These do not verify phonetic boundaries or independent listening. All4phone and18word flags remain unresolved. See LOW-ENERGY-PHONE-REVIEW.md/AO-RELEASE-REVIEW.md; no further release variants absent new defect evidence.

## Previous filtered-hand full review
CARTOON-EVAN-FILTERED-CONTINUOUS.md / evan-engine/reviews/filtered-continuous-v1.json; outputs/evan-cartoon-filtered-continuous/Review.html. Full23s normal/92s muted slow movies fully decode552/2208frames. All532speech frames use the filtered registered hand;20closing PNGs byte-exact. Every old hand ROI recalibrates, actual mesh remains positive(minarea2=135.35096197), half-alpha bounds clear. All552frame hashes/532journal rows verified. Additional all552frame comparison to prior heavier-ink film exact outside hand ROI(face/left/official brand). H264 is lossy; PNG-only equality claim. Original narration/postroll WAV byte-exact; AAC368000samples16kHz lossy. No retiming or new acting cues.

Inspected100native samples,37stage overview poses incl final551, decoded normal69/276/374/540 and slow276/1496 at1280x720. Stippling substantially reduced; slightly softer/heavier contour remains. No new open wrist seam observed. Fixed fingers, dense cuff folds, restrained face/body acting and lack of independent real-time/listening acceptance still prevent polished milestone claims. Source and final frame digests checked; all18markers and six exact context/waveform/spectrogram links retained. All18marker acoustic intervals equal CURRENT plan words; anchor intervals are obsolete estimates, NOT current playback intervals.

Workers94355/66980 COMPLETED. NO pending jobs. Executed local tools work/filtered-continuous-review/{render,review}.py; frozen Source/ plus Launch-Source-Manifest.json/Source-Manifest.json. Previous full films and2s filtered shot preserved. This is the preceding filtered-hand opt-in review; no scene default, approved release, branch main or updater changed.

The four-phone acoustic/target audit is now complete above; no flags cleared or interval changes. Current full candidate is the explanatory brow integration above.

## Registered artwork and sampling
open-palm-filtered-v1 uses SAME raw generated source-v1.png1402x1122RGBA SHA c717b774eb0f1ad82a68287c0b6c756365b358a7ff5823aea08708f1ac6c6d0f; raw bytes/alpha untouched. Generated geometry was not exact(source silhouette IoU.90010); five digits/no finger bands retained. Separate filtered working right-skin SHA eee0f4bca7935860a789229daee96ed77e7af38ceb2a1b10ea28559038014df2. Wrist551,510->810,762,15deg/scale.192 and original proximal pixels<=-36 exact. Source .16 pilot rejected for undersizing; do not return to it.

build_relaxed_cartoon_hand.build(source_antialias=True) filters associated RGBA with sigma2.55571595source pixels before minification. Derivative alpha intentionally resampled; no raw cleanup. Defaults unchanged.12tests passed in preceding change: default3planes+manifest exact, invalid-input preservation, prior fixtures, filtered fullspeech48Hz positive mesh/rigid distal parent/proportions within5%, temporary rebuild exact to independent filtering probe. All48native15–17s component frames plus source69/374 A/B inspected before full integration; component normal2s/slow8s48/192frames/PCM240000:27200032000samples verified. See CARTOON-EVAN-FILTERED-OPEN-PALM.md. No generated artwork this turn.

Prior source ink proxy RGB80 was2.908right vs2.294left/depth95=4.20vs3.60px, not exact artist match across differing silhouettes. Five-pose rigid distal sampling trace s>=70: actual mesh vs same analytic parent/cubic map differs only3–9alpha pixels,max1/255,zero missing opaque pixels. No evidence of large triangle-mask holes there; wrist transition not covered. Filtering addressed the registration minification instead. Prior checkpoints HISTORY-2026-10-27-F.md/E.md/D.md preserve earlier details.

## Retained rig/acting and timing
Skeptical brows5.14–7.37s, left negation sweep (1.5/28/-6,35/70ms followthrough), right definition palm(-3/-38/-5,9.79–14.54s) unchanged. Independent arms and separated oral11planes; fixed fingers are not articulated. No in-speech grin: preserve P/B/M/FV contacts. Source-X jaw/uncut upper cap/carrier above310/original ear;80ms P/B/M->AO prep; causal jaw mean min20.83ms/10%AO; seals/FV exact. Do not stack frozen capture classes or repeat strong cheek pulls. Editable PSDs are pixel planes, not native Moho bones.

Closing24fps first532=22.166667; preserve CuffRegisteredForearm/actual ElbowArcReview parent,20px underlap and ownership plane. No old hinge FK(88.33655pxerror). Grinband upper55%lumen+1px burial,240ms material blend u independent .35u shape, postroll only. Original waist140%2050x2150 offset-450,+40/right-5/-135/wrist-6->9->0. See GRIN-BAND/CLOSING-WAIST/CUFF-REGISTRATION docs; no more ending variants.

All18acoustic flags were visually reviewed against six waveform/spectrogram regions and exact PCM contexts. Exact boundaries/listening remain UNVERIFIED, no flags cleared. Four phone concerns: but/B184,whole/HH195,way/W207,all/AO228(lowenergy20.38–20.425). Coverage/thresholds are not accuracy. See evan-reference-timing-v1.json and outputs/evan-speech-exact-review-audio/Timing-Review.html. Voice PCM16mono16k352758samples/22.047375s SHA28487eb9c730c3d6a9613a4d419d8d590aa3a72c7816de7fb9183d9a7e552f96; planSHAaf01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e. Prior checkpoints HISTORY-2026-10-27-E.md and D.md.
