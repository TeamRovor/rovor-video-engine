# Rovor Evan animation engine — tested continuity checkpoint

Repository: TeamRovor/rovor-video-engine.
Development branch: development/evan-1080p60-acting-77a9561.
Draft PR: https://github.com/TeamRovor/rovor-video-engine/pull/5
Base: development/evan-painted-rig. DO NOT change main or replace source artwork.

## Creative contract
Use original Evan: dark tousled hair, sunglasses, navy shirt, black tie.
Goal: genuinely entertaining original illustrated cartoon filmmaking, not a
talking-head video, looping hand gesture, slideshow, unlicensed stock video
or generic replacement AI character. Real scene blocking, performance,
prop interactions, pacing, camera coverage, visual jokes and phoneme-accurate
English dialogue are important. No invented business customers.

Minimum user-facing finished video: 30 seconds of actual narration.
Never pad, loop or falsely extend shorter clips. Target complete actual
8–9-minute audio at 1080p60 in landscape AND portrait. Spend $0 extra.

## Implemented and tested
- Private Mac GitHub runner Rovor-Mac; safe isolated dev checks.
- rovor-production/audio_intake.py: allowlisted original MP3 inventory,
  waveform/spectrogram and optional draft ASR.
- longform_chapters.py: original 8:27 audio has 30,473 expected frames,
  nine balanced preproduction work units; cuts need listening.
- original_art_story_gate.py and scene_audio_schedule.py: real SHA-matched
  illustration sources and 60fps scene/voice coverage.
- audio_library.py, original Foley/music generators, soundtrack_editor.py
  and mix_audio_review.py: local private sound catalog, original audition
  scores, selected SFX, voice-preserving editorial mixes; no auto publishing.
- evan-engine/performance_tracks.py: bounded, individually authored
  original real-body joint tracks and existing hand plates.
- evan-engine/directed_scene.py: keyframed ORIGINAL art props, stage depth,
  purposeful original character/camera staging, independent portrait and
  landscape composition and rejection of inert/poorly framed scenes.
- evan-engine/visible_sound_sync.py: SFX may only match a physically
  moving original illustrated prop or existing rig actuator in BOTH views,
  not a keyword in a transcript.
- evan-engine/choreograph_story_beats.py: original Evan story moments
  become anticipation, action, hold and recovery poses without perpetual
  random arm waves; actually controls his current layered rig.
- evan-engine/render_acting_video.py: opt-in directed-scene mode, authored
  actor performance, optional audio-cue timing proof, original-Evan
  compositing and longform efficiency improvements. Supports preflight-only
  (NO rendered output), and auto-disables heavy per-frame PNG disk caches
  for videos of 30 seconds or longer. Reuses loaded art/rig in each Mac
  worker across verified MP4 chunks.

## Receipts — these are engineering tests, NOT finished videos
- Mac scene/compositing/audio/disk/preflight tests: 34 passed:
  https://github.com/TeamRovor/rovor-video-engine/actions/runs/39099022818
  A 40-second synthetic voice source and corresponding original art fixture
  were accepted for preflight. NO 40-second cartoon was exported.
- Real original Evan layered image tested with authored 8:27 choreography:
  21 tests passed, substantial pixel movement:
  https://github.com/TeamRovor/rovor-video-engine/actions/runs/39099253137
- Original audio chapter tests and first source-art checks:
  https://github.com/TeamRovor/rovor-video-engine/actions/runs/39093530236
- Streaming synthetic WAV mixing test:
  https://github.com/TeamRovor/rovor-video-engine/actions/runs/39095887493

## Blockers that must not be concealed
1. The actual 8:27 Rovor MP3 was verified in connected Google Drive, but
   direct Mac access through authenticated Drive Desktop must be checked;
   do not assume cloud audio is local to Mac.
2. Correct full 8-minute English transcription and pronunciation-based
   forced alignment are NOT certified. Existing 22sec speech plan is
   unrelated to that 8-minute file.
3. Original Evan body manifest still says animationReady:false, with static
   legs, missing independently posed fingers and alternate camera angles;
   no independently verified native Moho full-character project.
4. A complete genuine illustrated 8-minute screenplay and original
   prop/background assets have NOT been produced for that narration.
5. Rendered 30+ second 1080p60 original Evan cartoon, finished edited music,
   and human artistic-quality approval have NOT happened in this checkpoint.

## Next concrete autonomous work
1. Resolve Mac access to real chosen 8-minute original MP3; transcribe and
   verify real English words, pauses and phonetic timecodes against sound.
2. Design and paint original source-faithful missing acting poses and real
   story scenes. Actually verify rigged art in motion.
3. Director/story moment binding: narrative action, existing rig control,
   registered scene asset, camera staging, relevant sound only when visible.
4. Use the existing 40s+ full-source preflight before allocating video jobs.
5. Run resumable chapter renders, fully decode verify both aspect ratios
   and voice, inspect artistic details; preserve source files. No release
   approval based only on tests.
6. Deliver genuine >=30-second videos into chat and the user's private
   Review Library. Do not send short demo videos as user-facing deliverables.

Keep using original artwork and source audio, zero paid add-ons, and the
current draft branch. Never restart work from scratch.


## October 18 — source-audio acoustic articulation milestone (verified)

Previous 22-second reference was used ONLY for DEVELOPMENT TESTS, not a
customer-facing video. The original Mac local tool configuration has
installed free Whisper-base and Rhubarb executables/models.

New/updated repository source:
- rovor-production/speech_draft_audit.py: verifies Whisper English transcript
  segment ordering, duration, gaps, repeated/hallucinated text and boundaries
  that intersect preproduction chapters. Does NOT fabricate words, script,
  word alignment or phones.
- rovor-production/lip_cue_audit.py: validates Rhubarb A-H/X mouth shape timing
  directly against the decoded WAV end; no false claims that shape classes
  are certified phonemes or word pronunciations.
- evan-engine/build_acoustic_fallback_plan.py: deterministic original
  Evan painted-face fallback from Rhubarb, 10ms waveform and SHA-locked
  original narration; old mouth rig/source plates remain unchanged.
- rovor-production/audio_intake.py: automatic protected Whisper+Rhubarb
  source audio analysis, source matched transcript and acoustic review files,
  and original-Evan paint-face fallback plan. Keeps speech transcript and
  local model logs PRIVATE on Mac, out of GitHub logs and artifacts.
- Added tests across all components. The fallback can be passed to the
  preexisting CartoonBody mouth renderer and verify_audio_plan without
  pretending the phoneme alignment is certified.

Verified Mac runs:
- 39100163634: 13 English machine draft timing tests PASS. Diagnosed
  real whisper.cpp padding: reference WAV ends at 22.047s but an ASR
  segment reported end 22.400s; now the machine endpoint is clipped to
  measured source and explicitly flagged. Never extend animation/audio.
- 39100377557: 22 transcript/Rhubarb timing tests PASS and real
  audio-based Rhubarb mouth draft created.
- 39100684553: 7 original-Evan acoustic fallback tests PASS. Rendered
  two different real layered painted Evan mouth poses using acoustic
  evidence, mean absolute pixel difference ~0.608. 22sec = development-only.
- 39100869528: 25 full-intake tests PASS. The original rendered Evan
  mouth fallback now appears automatically in its private source-hash
  analysis folder.

Important verified blocker:
- Mac audio catalog COUNT=1, just the short reference WAV.
- Google Drive Desktop app was NOT INSTALLED in the capability audit
  on macOS 15.8.1 and Mac cloud mount is still FALSE in the latest
  integrated audio-intake run.
- Selected real 8m27s ElevenLabs original from connected Google Drive
  is NOT locally available to the Mac renderer as of that check.
- It is incorrect to claim the 8-minute film or 8-minute phonetic
  transcript is rendered just because a 22-second source test passes.

Immediate owner-side setup needed for long-form engine:
- Authenticate Google Drive for Desktop on the Mac into the same
  connected Rovor Drive account and let the MP3 folder appear under
  ~/Library/CloudStorage, OR put the real original 8min MP3 file under
  ~/Movies/RovorAudioInbox. Do not provide login credentials to ChatGPT
  or upload source media to public GitHub.
- Run a fresh local audio catalog job, choose that long-form ID and run
  the existing approved audio analysis workflow. It will now produce
  machine draft transcript, waveform, nine chapters, Rhubarb acoustic
  mouth cues and an original-Evan-render-compatible speech fallback.
- Then review the words and pronunciations, design original story
  scenes, run exact-rig preflight and resumable 1080p60 full renders.

NONE of these lip fallback outputs is a completed cartoon, certified
English phone alignment, artist-approved acting, or final sound mix.
