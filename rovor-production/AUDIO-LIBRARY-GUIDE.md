# Rovor animation sound library

## Local folders (Mac)

- ~/Movies/RovorProduction/AudioLibrary/SoundEffects
- ~/Movies/RovorProduction/AudioLibrary/BackgroundMusic
- ~/Movies/RovorProduction/AudioLibrary/catalog.json
- ~/Movies/RovorProduction/AudioLibrary/_SFX-SIDECAR-TEMPLATE.json
- ~/Movies/RovorProduction/AudioLibrary/_MUSIC-SIDECAR-TEMPLATE.json

Audio itself stays on the Mac, out of GitHub. Existing files are not deleted
or overwritten. Catalog and original source recordings are private.

## How to add a new sound or music file

Place an actual WAV, MP3, FLAC, AIFF, M4A, or OGG under the correct category.
Create a matching sidecar JSON adjacent to it, with the complete audio filename
plus .asset.json, for example "browser-click.wav.asset.json". Use the templates
copied into the AudioLibrary root by audio_library.py init.

Record the EXACT source, what is audible, timing/action tags, and commercial
use rights. Do not infer permission from a "free download" label. For
third-party or CC0 music/effects, record actual licensing proof and attribution
requirements. Set license.ownerConfirmedRights=true only when permission was
verified for Rovor's intended use. Optional sourceSha256 locks license notes
to exact source bytes. Vocal status and loopability are mandatory for music.

Run: python3 rovor-production/audio_library.py scan
Rejected/unprobed/unlicensed recordings are never selected.

## Local Foley sound starter kit

Run: python3 rovor-production/generate_original_sfx.py

This builds seven original procedural UI/prop SFX with no third-party samples,
deterministic WAV hashes, non-overwriting sidecars, and clear NOT-APPROVED
listening status. They are audition materials, not a finished sound design.
Do not call them production-quality without normal-speed listening.

## Context-based editing — where to place audio

soundtrack_editor.py takes a real narration-timed storyboard and local catalog.
It places suggested effects only at actual annotated physical animation events.
An example shot sound direction:

    "soundDirection": {
      "musicMood": "curious",
      "physicalEvents": [{
        "atSec": 18.35,
        "eventTag": "browser-click",
        "visualAction": "Evan visibly taps the browser icon",
        "overDialogue": "quiet-underlay"
      }]
    }

To preserve a dramatic pause:
    "soundDirection": {"intentionalSilence": true}

If a shot contains no physical event, the default is NO effect. If a shot
contains no music mood, the default is NO music. Do not add a whoosh to every
cut or a click to every word. Avoid layering effects within 1.5s. Vocal music
is not selected underneath spoken dialogue. If spoken-word intervals are
not confirmed by human review, all narration time is treated as dialogue.
Starting suggestions: SFX -24 dB under voice; music -30 dB under voice,
with actual mix loudness, ducking and licensing subject to listening review.
Those numbers are starting fader estimates, NOT mastered loudness.

Run:
    python3 rovor-production/soundtrack_editor.py STORYBOARD.json \
      "$HOME/Movies/RovorProduction/AudioLibrary/catalog.json" \
      --out sound-cue-proposals.json

The proposal lists selected asset IDs, scene events and frame-accurate
timestamps, missing assets, music intervals and refused placements.
It never modifies narration, uploads audio or claims creative approval.

## Current stage

- Local SFX and background music folders: created.
- Private license-aware catalog: functioning.
- Seven procedural original SFX: development-only and require listening.
- Background music: curate genuinely licensed instrumental tracks separately.
- Director event cue selection and silence protection: functioning.
- Professional music editing/mixing, ducking and mastering: NEXT stage, not
  silently claimed completed.
- 30-second actual-audio minimum and 1080p60 animated storytelling requirement
  are unchanged. Long-form Evan speech/rig animation remains in development.
