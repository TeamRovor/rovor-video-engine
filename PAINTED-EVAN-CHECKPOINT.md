# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photo is loose identity only; realistic painted direction superseded. Preserve dark tousled hair, sunglasses, navy shirt/black tie, official Rovor branding. No photo crops, geometric mouth stickers or flattened character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draftPR#4 https://github.com/TeamRovor/rovor-video-engine/pull/4. Development commits/pushes authorized. NEVER merge/deploy without explicit approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4=27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful review milestone/failure/completion/required action only; disable when actually ready. Routine decisions need no question.

## Latest: sustained and visible W integrated in development

Read CARTOON-EVAN-SUSTAINED-W.md and reviews/sustained-w-v1.json. Shared acoustic_weights now uses the existing sustained vowel envelope and full visible-gesture salience for W. Other phone formulas, explicit silence, P/B/M seals and F/V contacts retained; pronunciation fallback unchanged. No word exception, new profile, art replacement or audio/phone retiming. At18.225 jawF .000264596→.775496735; rawidentityF .943396226, filtered .843055673. W assignment remains unverified; do not call low energy confirmed silence.

Important correction: earlier in-memory W experiment changed speech_planner.acoustic_weights but left rounded_cartoon_head's direct imported alias pointing at the old function. Its render/geometry results were a partial-control trial. Root gate/energy ablations remain valid. Historical doc/JSON corrected. Fresh module imports now assert same jaw/rounding function; final Python AST equals rendered candidate. Corrected envelope-only renders still read weak; pure-F and mixed-F poses show existing art CAN produce small rounded mouth. Deferring redraw while fixing control reach.

outputs/evan-cartoon-w-gesture: allfour W contexts (website twice, way, we),168normal/672mutedslow frames over eight fully decoded movies. Sourceframes24:72,812:848,850:898,924:960. Exact PCM crops and AAC samples16000/12000/16000/12000. All168native mouth pairs inspected, selectedfullheads and originalcartoon direction compared. Pursed W visibly replaces former wide idle line. All168 upper288rows exact. No independent listening/real-time playback acceptance; longway transition and18+3 flags still unresolved for exact sound boundaries.

49 normal-import tests pass, including3 new W regressions (oldplanner fails2). All1307 recordingframe/phone-midpoint geometry samples pass, minjaw27.78942. Widthmax13.84723 unchanged; p95 worsens6.23685→6.73285,53stepsgrow>1px as W gains visibility. LowerYmax14.66776 unchanged; p956.19515→6.10012,7stepsgrow>1px. Chinmax2.30136 unchanged. These do NOT establish smooth acting/studio quality. Functional control change integrated on development only; performance unaccepted. No pending jobs.

NEXT: re-render the coherent five-second Rovor scene696..935 with current W controls (normal/slow), then target vertical release/shortAO pops using original recording and preserved complete seals. Prior staged proof is PRE-W and must not be shown as current. Keep artist-faithful lip/face construction, independent arm/wrist/hand acting and official branding. Independent sound review/human animator or matched redraws may still be needed. Native512/8GiB CPU constrain detail and throughput. No new imagegen artwork this turn; native pose inspection avoided unnecessary generation.

## Retained construction and safeguards

Phonetic corners7d7e7a6 remain opt-in MaterialCapture/SeparatedOralReview:203keys per side from native vowel/diphthong phases,W,contact endpoints/silence; monotone cubic flowing_track changes32oralX. Corner path now receives same evolved W planner as jaw; no imported-alias trial mismatch. Raw audit defaultChanged=False refers to opt-in art assembly, not the shared W planner update. Existing source-plan cached controls were not rewritten; renderer recomputes controls from times, and finalize_plan generates evolved W controls for new exports.

Matching jaw55c58b8 uses same registered construction-skin-v1 working-face-skin as upperface, authored AA mask/SOURCE UVs/jaw_cut, right329 excludesear. Registered generated underpaint plusoriginalskin, not recovered anatomy; sources unchanged. Ten actual oral planes, independent shoulder/elbow/wrist/hand controls, officialstage retained. Prior fullstaged240normal/960slow proof and two6plane/two10plane PSDs remain archived PRE-W; beforeglobalroll/nativecoords, not native Moho bones. Thinclosures, shortvowel/contactpops, limited cheeks/eyes/fingers/legs remain. Earliercontact-context c058a81 remains rejected.

Previous checkpoint PAINTED-EVAN-HISTORY-2026-10-24-A.md; earlier histories retain all artwork/audio trials. PlanSHAaf01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e unchanged. Main/V3/V4/releases/updater/nativeMoho untouched. No Moho probe/merge/deploy. Polished milestone NOT ready; automation ACTIVE. Review-Evidence records final commit/clean/pushed state.
