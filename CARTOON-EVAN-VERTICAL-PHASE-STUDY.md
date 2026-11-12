# Rejecting smoother numbers with invalid lip geometry

The vertical-phase experiment is **not integrated**. It reduced the largest lower-lip step but folded the mouth's internal mesh elsewhere in the recording. The development rig now explicitly rejects non-finite or inverted oral geometry before returning a final layered image. The numeric audit uses the same check. Valid current artwork/motion is unchanged.

## What was tried

The first isolated prototype sampled actual current inner-mouth gaps at existing vowel/diphthong/W/contact phase targets, contact boundaries and sustained-silence settle points:288 keys. It reused the existing monotone cubic interpolator. Between assigned contact spans, the inner lower arch was scaled toward the interpolated gap; corresponding outer lower points followed, retaining their original vertical ink depth. Assigned P/B/M/F/V spans, all oral X, upper arch, skin and independent chin stayed unchanged. No source artwork, audio samples, phoneme durations or planner weights were edited.

Jaw-only checks passed all1307 recording frames/phone midpoints. LowerY maximum step fell14.66776→12.09052px and p95 fell6.10012→4.96342, but64 individual steps grew by more than1px. The `up/all` rise became less abrupt while retaining its peak. The `more` peak shortened/shifted and other vowel poses changed; smaller aggregate jumps do not prove better acting or timing.

Rendered voiced current/trial comparisons for source864:912 and960:1008, plus muted quarter-speed versions. All four movies fully decode:96 normal and384 slow frames total. Original PCM crops288000:304000 and320000:336000 are copied directly; both AAC decodes return16000samples. All96 native mouth pairs and selected full heads were inspected. These clips do **not** cover every changed region.

The original waveform/spectrogram and actual frame trajectories were compared in `More-Audio-Trajectory.png` and `Up-All-Audio-Trajectory.png`. Periodic energy continues inside assigned more/M; amplitude alone cannot justify opening that closed-lip sound. The up/P interval includes a long quiet segment before strong vowel energy returns. Boundaries and midpoint keys remain hypotheses, not independently verified sound timing. No independent listening or real-time playback acceptance.

## Why it failed

The old geometry audit checked the jaw mesh, but not the separate oral annulus/fan triangles used for mouth warping. A full oral check found **12 failed samples**, including14.2708–14.4167s,19.5/19.5208s and21.7708s plus one phone midpoint. Minimum oral signed area was−13.67194; corresponding current baseline areas were positive. A native raster at frame687 looked superficially plausible and reported zero rounded fallbacks despite the inverted oral mesh. Those counters were insufficient evidence.

Two further geometry-only trials were rejected. Applying the outer displacement at matching X rather than matching point index produced88 failed samples. Reusing the existing oral builder with an independently interpolated aperture produced65. Neither was rendered as an accepted comparison or promoted. These failures show that arbitrary gap/aperture changes cannot be assumed compatible with the existing pose/annulus topology. A mathematical minimum-step improvement is not an acceptable trade for distorted lip surfaces.

The shared `check_oral_mesh` now checks finite points and strictly positive signed areas for all native oral triangles. Both `SeparatedOralReview.assemble` and `audit_separated_geometry.capture` call it. Invalid targets raise a clear error instead of returning a plausible-looking corrupted final frame; no clamp or silent fallback hides the defect. Regression tests deliberately invert an oral triangle while the jaw reports valid geometry, check non-finite coordinates, and verify that the actual final assembly rejects a folded mouth.

The unchanged current recording passes all1307 combined oral/jaw checks, with minima0.04441152 oral and27.78942 jaw. Fifteen focused face/audit tests pass. Re-rendered current full staged frame868 remains pixel-exact against the previous proof. Running the real rejected prototype at687 now raises before returning pixels. These are geometry/export safeguards, **not studio-quality or lip-sync acceptance**.

## Next bounded work

Test phase pacing through the existing geometry-weight path, starting with rounded AO releases, rather than moving lower contour points or changing aperture independently of the pose. Preserve complete contact slots, current W articulation, the independent chin and original recording boundaries. Test failed regions685–692,936–937 and1045 before broader shots. Any claimed smoother motion must retain positive oral and jaw meshes over the full recording, then pass native-resolution and normal/slow visual review. Do not force extra opening into quiet/resting shapes just to make a curve smooth.

`outputs/evan-cartoon-vertical-phase` preserves all source prototypes, original checker used by the first renders, actual failures, current baseline audit, sound/trajectory figures and rejected comparisons. The latest voiced visual proof remains `outputs/evan-cartoon-w-staged`; the new gate leaves that valid shot unchanged. Cheek/eye/hand acting, source-alpha cleanup and some mouth shapes remain unfinished; human animator or matched redraws may still be necessary. Main, V3/V4, releases/updater and native Moho projects are untouched. No Moho probe, merge or deployment. Polished milestone incomplete; automation stays active.
