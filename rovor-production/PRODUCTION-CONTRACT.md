# Rovor Original Cartoon Production Contract — development

## Character and creative identity
Preserve the actual Evan layered art (dark tousled hair, sunglasses, navy shirt,
black tie). No generic stock video, substitute AI character, invented clients or
static talking puppet presented as a finished entertaining cartoon.

## Required production stages
1. Source choice: choose one audio file by Drive file ID or Mac catalog ID.
   Do not commit private media to the repo. Preserve source SHA-256.
2. Analyze: decode selected MP3 into 16k mono PCM16 WAV, measure RMS/peaks in
   10ms windows, draw waveform overview and readable one-minute spectrograms.
   Waveforms reveal energy, never what English words were spoken.
3. Transcribe: locally configured Whisper generates draft English words.
   Correct transcript and punctuation against audio; isolate non-speech sounds.
4. Align: dictionary and acoustic alignment of actual English phonemes, not
   letters. Check bilabials P/B/M, F/V labiodental contact, TH and L tongue,
   vowel stress/diphthongs, consonant anticipation, coarticulation, connected
   speech, silence, breath, and expressive speech. Flag uncertainty, don't
   manufacture perfect phoneme accuracy. Current 22-sec review has 18 flags.
5. Direct: hook, illustrated visual narrative, original backgrounds and props,
   object transformations, camera staging, character acting, animated
   demonstrations, useful jokes/reactions, thoughtful transitions and a
   branded outro. Avoid shot-after-shot static hands/head movement.
6. Produce: every storyboard asset and character action must exist as actual
   layers with timed animation; approving a JSON plan alone is not enough.
7. Render: landscape 1920x1080 and portrait 1080x1920 at 60 fps with verified
   original narration. Eight to nine minutes is 28,800 to 32,400 frames per
   orientation. Chapter-based incremental caches and resume are mandatory.
8. Verify: every decoded video frame, continuous timestamps, dimensions,
   audio onset, correlation, visible composition/gesture transitions, and
   inspect specific visemes by listening and slow playback.
9. Review: publication requires separate human art, performance, story,
   humor, pacing, lip-sync and entertainment approval. Structural gates
   never certify Hollywood/studio quality.
10. Deliver: copy approved review to private Google Drive folder from its
    authenticated Desktop app, then separately verify cloud sync and inspect
    the delivered output via connected Drive. No media Actions artifacts.

## Implemented now
- rovor-production/audio_intake.py inventories allowlisted MP3/WAV files,
  analyzes a selected file, graphs audio and optionally runs local Whisper.
- rovor-production/quality_gate.py validates storyboard structure and
  rejects static talking-head scripts.
- rovor-production/private_delivery.py verifies old 22-second reference
  samples and copies to an authorized Google Drive Desktop sync folder.
- .github/workflows/rovor-mac-production.yml supports separately approved
  catalog, selected-audio analysis, quality selftest, reference render and
  private delivery jobs.

## Known blockers
- Google Drive Desktop is not currently mounted on the Mac, so recordings
  listed in ChatGPT's connected Drive are not yet readable by the Mac runner.
- Existing local Whisper, model, Rhubarb and FFmpeg were found in previous
  Mac local_tools.json configs. They are not on PATH, but can be invoked by
  absolute path. The selected-audio analysis is *draft*, not phoneme proof.
- The Mac render venv lacks cmudict and pocketsphinx; phoneme forced-alignment
  for new recordings is not implemented.
- The 22-second renderer is not a general 8-9-minute illustrated story engine.
  This must be developed with scene, asset, shot and performance direction,
  then tested end-to-end on representative narration.

Do not describe blocked stages as completed.
