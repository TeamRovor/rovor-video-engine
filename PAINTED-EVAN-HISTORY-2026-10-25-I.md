# Evan cartoon: current checkpoint

## Direction and safeguards

Entertaining expressive2D CARTOON. Follow CARTOON-EVAN-DIRECTION.md and evan-character/cartoon-v1/source/design-sheet-v1.png. Photo is loose identity only; realistic painted direction superseded. Preserve dark tousled hair, sunglasses, navy shirt/black tie, official Rovor branding. No photo crops, geometric mouth stickers or flattened character swaps.

Repo work/engine; development/evan-painted-rig (legacy name), draftPR#4 https://github.com/TeamRovor/rovor-video-engine/pull/4. Development commits/pushes authorized. NEVER merge/deploy without explicit approval. Preserve main4e099b5f1a30661c952358f49e1e2d70a5fe2a62, V4=27b664b9daa924ff17d3b874264bc4cef7131196, V3/V4/releases/symlinks/updater/native projects. Do NOT launch/restart/probe Moho unattended after its crash.

Automation develop-evan-painted-animation ACTIVE. Full polished milestone NOT ready. Notify meaningful review milestone/failure/completion/required action only; disable when actually ready. Routine decisions need no question.

## Latest: complementary face/jaw ownership integrated in development review rig

Read CARTOON-EVAN-FACE-OWNERSHIP.md and evan-engine/reviews/face-ownership-v1.json. Contour jaw skin X now stays SOURCE; existing lip/independent chin Y stay unchanged. Cheek carrier is behind jaw. NEW11th plane restores protected upper face from ORIGINAL OWNED carrier above310 and covers upper cap from UNCUT face paint near the actual upper lip. Both inputs are required: clipped mouth paint leaves fragments; unowned upper-face paint creates an ear step. Behind-jaw face excludes protected rows to avoid duplicate alpha. No original artwork/alpha, speech times or anticipation changed.

Final revision25 tests pass.1307 geometry/analytic-mask samples retain recorded lip controls, all skin X SOURCE, minOral.04441152/minJaw45.5;248 closed samples zero interior. Actual native More/Up-All before/after:96normal/384slow frames, complete originalPCM/AAC16000 each; all four films decode. All96 native mouth pairs and full980/983/985 inspected. All oral coordinates/upstream skin/upper288 exact; ear-region pixel comparison EXACT96. Final proof: outputs/evan-cartoon-face-ownership. Final983 PSDs contain6body/11oral native planes and reopen successfully; NOT Moho bones.

Earlier intermediate revisions are retained under Revision1..3, NOT promoted: first caused nose27/255 differences; second left cap gaps; third restored uncut upper face and stepped ear ownership. Final guard must use uncut face ONLY near mouth and owned carrier for protected upper rows. Do not reuse prototype.py/keys.py as the current renderer; render_final.py uses the actual production class plus frozen before modules. Artwork margins remain authored, not approved anatomy. Rapid M→AO opening and remaining lip-corner/rim ink still need acting/art review; exact listening acceptance absent.

NEXT: rebuild branded five-second shot with this11-plane ownership, then compare closed-M/P AO preparation on this corrected layout. Previous full staged outputs/evan-cartoon-occlusion-staged is PRE-OWNERSHIP (core19c7326), not the current face render. Preserve W/chin/arms/original sound/brand and uncertain phone boundaries. Source redraw/human animator may still be needed; masks/test counts do not establish studio quality. No pending jobs after final packaging.

## Retained animation and limits

442a4dc sustained/full-visible W remains in shared acoustic planner, source audio/plan unchanged. Historical partial W monkeypatch alias error corrected; latest W proofs used fresh imports. Prior staged voiced proof (before current inner-matte fix) is outputs/evan-cartoon-w-staged (runtime442a4dc, reviewe1da3f7):240normal/960slow source696:936, PCM232000:312000/AAC80000; upper288exact240/nose0,minJaw27.79054,arms494.61584/135.35149,allfallback0. All240native staged mouths/full828/868/888/935 inspected;6body/10oral PSD868 reopen .00712015/.00317382 error per255. Pre-globalroll/nativecoords, NOT Moho bones. The earlier oral-mesh gate left valid geometry/pixels unchanged; current matte correction changes oral interiors only. Older corner-phase scene is PRE-W.

Selected cartoon design-sheet identity/palette retained. Eleven current oral planes, independent shoulders/elbows/wrists/hands and official Rovor stage retained. Jaw55c58b8 uses registered original/generated construction skin, not recovered anatomy. Phonetic corner trajectories7d7e7a6 remain opt-in; source annulus/alpha unchanged. No new imagegen artwork this turn. Thin closures, vertical pops, limited cheeks/eyes/fingers/legs and isolated native neck alpha specks remain. Artist cleanup/animator acting may still be needed; faster hardware cannot fix drawings/acting. Native512/8GiB CPU limit detail/throughput.

49 prior full-control tests and25 current focused tests are engineering checks, NOT performance acceptance. Original18 flagged regions plus3 quiet-phone warnings remain unverified for exact listening/boundaries; waveform/spectrogram evidence retained. Previous checkpoint PAINTED-EVAN-HISTORY-2026-10-24-H.md. PlanSHAaf01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e unchanged. Main/V3/V4/releases/updater/nativeMoho preserved. No Moho probe/merge/deploy. Polished milestone NOT ready; automation ACTIVE. Review-Evidence records final clean/pushed commit.
