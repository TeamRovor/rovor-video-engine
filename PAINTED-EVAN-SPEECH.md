Latest implementation: see ACOUSTIC-SPEECH-ALIGNMENT.md. The following describes the earlier duration-prior milestone, preserved for comparison.

# Script and recording driven speech planning

The painted renderer now reads the actual narration script (optional `--script narration.txt`; otherwise the recognized transcript), extracts separate experimental Whisper word timestamps, aligns matching words to the script, and expands CMUdict pronunciations into mouth gestures. Explicit project pronunciations cover favicon and Rovor. P/B/M predict lip closure, F/V predict lower-lip contact, L predicts tongue placement, and vowels predict opening/rounding. Pronunciation priors blend with the existing acoustic Rhubarb cues rather than discarding recording evidence.

The recording is analyzed at 10 ms intervals for RMS energy, with an absolute silence floor and smoothed envelope. Energy modulates vowel opening and silence release; it does not select a consonant. The renderer uses overlapping continuous speech weights and the same registered painted facial anatomy. No new facial crops or geometric mouths were introduced.

Each painted pipeline run saves `words.json`, `speech-plan.json`, and `speech-timeline.png`, alongside its scene and film. The plan contains script indices, source pronunciations, estimated phone positions, measured RMS/energy, acoustic fallback cues, coverage and mismatch warnings. A supplied script participates in the resume fingerprint; renderer version 3 prevents reusing incompatible old frames. Default V3/V4 routes and approval workflow remain unchanged.

To review any portion of the audio graph:

```
python speech_review.py speech-plan.json narration.wav speech-review.png --start 2.5 --duration 2.5
```

Install the optional painted dependencies using requirements-painted.txt in the isolated painted environment. The pipeline runs planning and graph export with the configured painted Python/packages, so the legacy launcher does not import NumPy or CMUdict.

## Validation and honest limits

A fresh 4.8125-second, 231-frame, 48-fps 1080p opening-line sample was rendered using the real recording and the new plan. A separate short MP3 pipeline exercises script input, two transcription passes, pronunciation planning, scene integration and encoding. The waveform review shows the opening and gaps explicitly; native-resolution frames and consecutive mouth sequences are reviewed separately from unit tests. Tests cover contact identities, script mismatches, non-overlapping phone times, silence and temporal continuity.

Word timestamps from whisper.cpp are explicitly experimental (https://github.com/ggml-org/whisper.cpp). CMUdict supplies American English pronunciation alternatives (https://github.com/cmusphinx/cmudict); currently the first pronunciation is selected. Phone positions inside each word are duration-weighted estimates, NOT acoustic forced alignment. Diphthongs currently use a single representative viseme. No claim of phoneme-perfect sync or studio-quality acting is justified yet.

On the full reference script, 65 of 66 script words match the recognition. The recognizer spells Rovor as Rover, so the plan reports that mismatch and uses acoustic fallback there; it does not pretend to have aligned the brand word. Fine coarticulation, context-dependent pronunciations and sound-level alignment remain concrete next steps. Fixed three-quarter artwork and limited expressions/hands still limit acting, independently of timing accuracy. The local renderer works on this CPU; Moho remains untouched after its earlier crash.

Native-resolution comparison around “open” (0.438–0.729 s): the new plan reaches a painted lip contact at about 0.521 s and releases by 0.562 s, where the previous audio-only pass was still closing. This follows the predicted P interval; it is evidence of changed articulation, not proof that the guessed phone boundary is exact. Some blended lip textures remain soft, and the face still lacks emotional acting. All 51 tests pass; these checks do not establish animation quality.
