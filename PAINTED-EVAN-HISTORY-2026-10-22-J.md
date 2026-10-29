# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive 2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photo is loose identity only; realistic painted direction superseded. Dark tousled hair, sunglasses, navy shirt/black tie, official Rovor branding. No facial photo crops, geometric mouth stickers or flattened whole-character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draft PR#4 https://github.com/TeamRovor/rovor-video-engine/pull/4. Commit/push development work authorized. NEVER merge/deploy without explicit approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4=27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful review milestones/failure/completion/required action only; disable when actually ready. Routine decisions need no question.

## Latest: actual six-plane controlled contact/release assembly

Read CARTOON-EVAN-SIX-PLANE-CONSTRUCTION.md. New review-only labiodental_construction.py uses six actual painted planes:neck,cavity,fixedFVincisors,combinedjaw/lowerlip,upperlipcapV2,cleanupperface/cheeks. No wholehead frame swaps, guide paint substitution, new generated art or default profile changes. Actual V2 cap now consumed by standalone construction; earlier source metadata updated to distinguish that from approved runtime. Nine ART layers in drawing templates remain BLANK, not auto-promoted.

First cap-on-top pilot showed a philtrum skin patch and was rejected. Final cap UNDERLAPS cleanface; central carrier boundary uses upperlip guide. Crown behind lowerjaw/lip, not blanket crown restoration. Native guide lowerlip325→332/chin393→394, upperlip/teethfixed. Artist-authored, not measured speech anatomy. Sourcepixels/alpha unchanged. Silent authored48normal/192mutedquarter frames1280x720/48fps fullydecode; held/quintic contact-release-contact, NOT narration/phoneme alignment. All48native mouth details, contact/release heads and selected design sheet inspected. No continuous-playback acceptance claim.

outputs/evan-cartoon-contact-construction includes films and two SIX-ACTUAL-PLANE posed PSDs; reloadmean .022726/.023745 per255, notnativebones. Two focused tests pass for fixedincisors/cap with movingjaw, endpoint positive meshes/identity, capunderlap/source immutability. Native six samples retain ONE lowalpha pixel at198,321 (alpha228–237): faint corner joint, no cleanup. Staticeyes/brows, straightupperlip/dark wedge-shaped release/heavyfold lack concept appeal; contact pressure NOT accepted. Combinedjaw/lowerlip limits independent roll. This is construction tooling, NOT polished actor or release candidate. CPU adequate; art/animation design still limiting. No pending jobs. Prior checkpoint HISTORY-2026-10-22-I.

## Retained: separate labiodental contract and upper-lip candidate

Read CARTOON-EVAN-LABIODENTAL-GUIDE.md. Added Labiodental/LabiodentalRelease to face_art_contract.py, keeping existing3poses unchanged. Upperlip235,319 and incisor tips225/245,325 stay fixed; lowerlip235,325→235,332 on release. Artist-authored proposal, NOT measured anatomy. New family requires upper-teeth paint (old bilabial Contact can omit it). Five import/guide tests pass. Builder overview now supports5poses/2rows. All5PSDs reopened with exact reference/guide pixels;9ARTplanes remain BLANK and imports reject them. Templates are scaffolds, not new artwork/rigs.

Built-in image_gen generated isolated upperlip/philtrum cap V1 and targetedV2. Source originals/alpha/prompts preserved under labiodental-guide-v1/source. Genuine upperlip-only paint, no lowerlip/teeth/head. V1's triangle/hooked corners too strong; V2 shadow softer but hooks remain. V1 uniform2corner fit:held-outcenter residual.868px. Preferred Upper-Lip-Candidate-v2.png inherits same parent; V2 center NOT independently measured. Bothnativebounds pass. No alpha cleanup. V2 faint source-alpha bounds wider but zero native outside-envelope alpha after normal projection; do not call it failed validation. No cap loaded into runtime or approvedART, no new voiced film until pairedjaw/incisor occlusion review. Ghost placement image is NOT assembled output. outputs/evan-cartoon-labiodental-guide has all templates, sources/prompts and registration. No pending jobs.

Primary phonetics references (MIT lecture5 slides3–4; Glasgow Seeing Speech IPA chart) support bilabial vs labiodental distinction only. Pixel guides/shape/front-back order remain authored proposals requiring artist judgment. Sources linked in doc/review; no copied diagnostic movies or scientific anatomy claims.

## Retained: measured contact-incisor ownership, unapproved ablation

Read CARTOON-EVAN-CROWN-OWNERSHIP.md. Existing fv-rig-v3 already has lip-contact and upper-teeth planes. Current four-plane jaw stack bakes them into the upper-face carrier before the ownership cut. New contact_crown_audit.py captures actual rigid/windowed crown material; render remains byte-exact. Three tests pass: fractional coverage, complementary source partition, unchanged mixed/full rendering. No new artwork/alpha cleanup/phone timing/default changes.

19active samples848–898: carrier removes0–48.455% of crown alpha area;851 before/after105.960/54.617 native pixel equivalents(103/54opaque pixels),892 removes42.906%,855 removes0. This measures ONE carrier mask, NOT final visible teeth or proof of a bug. Lower-lip occlusion can be anatomically necessary; do not turn this into a blanket show-all-teeth fix.

Counterfactual render_crown_ownership.py exposes only removed source crown material in front, weighted by existingFV. Uses previous fitted jaw candidate, not a new head sprite. outputs/evan-cartoon-upper-contact:48normal/192mutedquarter frames1280x720/48fps, source840–887(17.5–18.5s);16,000original/decoded16k samples280000:296000; bothfilms fully decode. Ten activeFVframes; all38zeroFV pairs exact. Baseline851 byte-exact to prior jaw-candidate film. Upper288rows exact. Native851/855/856 and848–857 inspected. No independent listening/continuous-playback acceptance. No pending jobs.

Crown looks less like a hairline but pressure/wrap remains unconvincing. Ablation may violate lower-lip occlusion; NOT accepted anatomy or a release candidate. Need native upper-lip/incisor/lower-lip front/back construction and coordinated release, not more isolated seam generation or opacity patches. Human character-art/animation review still needed. CPU can produce proofs; art/anatomy remains limiting.

## Retained art and systems

Read CARTOON-EVAN-FV-REDRAW.md. fv-redraw-v1/source has built-in image_gen full-headv1/v2 sources + isolatedcontact-jawv1, exact prompts/hashes. Full heads UNREGISTERED SOURCE ONLY; never replacementframes. Contact-Jaw-Candidate.png is a registered candidate only, not default. Fixedcanvasplacement rejected(longchin/doubledcheek);3attachment/chin anchors fit previous source. Held-out loweroutline558samples median0/p95=max1px. Four actualposedplanesPSD851 reassembly .023247/255, not Moho bones. Lip fold adds volume but heavy/glossy and can look like second crease. One contact jaw across vowels is not a coordinated rig. Prior104normal/416slow proof retained,34,667original/decoded samples. Do not repeat same full-head prompts.

Read CURRENT-CONTACT and LIP-CORRESPONDENCE docs. current_contact_exposure.py uses fresh oral controls includingpureFV; old experiments retain fullFV guards. Same painted cavity backing atfullFV fixes9→2/255 endpoint discontinuity. Source-edge UV correspondence/cavity backing reduced oral lowalpha events but56partialalpha events remain; not perfect anatomy. Default profiles unchanged.

Speech plan ../../outputs/evan-speech-alignment/Aligned-Speech-Plan.json:66words/248phones/39ARPABET; two-pass acoustic alignment, coarticulation/contact/silence gating. All18flagged word regions have VISUAL waveform/spectrogram review in evan-engine/reviews/evan-reference-timing-v1.json; exact boundaries UNVERIFIED. Do not equate coverage with accuracy or retime to hide art issues.

Retained relaxed hand/forearm, wrist-axis articulation, authored detail/finished-thought staging and official Rovor mark. Body has six actual posed pixel planes, not native Moho rig; fingers share wrist, legs static, eyes/blinks unrigged. No staging expansion until facial construction is convincing. narrated_export.py muxes finite silent video and COMPLETE source WAV without -shortest/-frames:v; exact decoded samplecount is required. Preserve this fix.

## Next concrete work

1. Six-plane native assembly now exists. Next artist-review/redraw leftcorner interface, upperlip curvature, lowerlip pressure/roll and curved release aperture; combinedjaw/lip still restricts acting. Then test a controlled voiced transition using unchanged alignment, without treating this two-pose study as a full narration profile. No full-head generation, blank-template promotion or blanket crown restoration.
2. Retain original voice/alignment uncertainty, source pixels/alpha and regression films. No numeric seam cleanup, full-thought integration, default promotion or unattended Moho use.

## Runtime/history

Python /Users/amarhavic/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3; from repo PYTHONPATH=../painted/deps:evan-engine, OPENBLAS_NUM_THREADS=1, cv2.setNumThreads(1).8GiB/8logicalCPU, CPU raster. Temporary caffeinate scoped to render/encode only. FFmpeg and16k narration in sibling referenced-chatgpt-conversation-this-is-an/work/{media-tools/ffmpeg,evan-narration.wav}. No scipy; acoustic plots use numpy/matplotlib. User artifacts outputs/; latest source/guide artifacts outputs/evan-cartoon-labiodental-guide; prior scratch work/cartoon-crown-ownership. No pending jobs. Detailed prior checkpoint archived PAINTED-EVAN-HISTORY-2026-10-22-H.md; G/ F/E/D and earlier archives preserve all source failures, geometry, anatomy and render evidence.
