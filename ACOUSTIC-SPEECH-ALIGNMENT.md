# English sound alignment and cartoon mouth controls

This revision replaces within-word duration guesses with a two-pass local acoustic alignment when usable. PocketSphinx first aligns the script words, then locates their phones against the recording with its English acoustic model. It runs on this CPU, with no speech API or GPU dependency. The existing word transcript remains an independent audit. Script agreement below 85%, missing dictionary entries, invalid/zero intervals or backend failure produce an explicit estimated fallback; strict CLI mode rejects fallback.

`english_articulation.py` describes all 39 base General American English ARPABET phones. Word pronunciations handle silent letters, digraphs and alternate pronunciations; a letter is not assigned an invented individual timestamp. Aligned words carry original script character spans. Sound intervals carry script indices and raw acoustic scores. These scores are diagnostic numbers, not calibrated probabilities; confidence is null rather than a fabricated percentage. Word-boundary disagreement over 250 ms is flagged for inspection.

Diphthongs AW/AY/EY/OW/OY now move through two targets within the same aligned phone. Overlapping kernels, consonant salience, eased contact/release and sustained-silence easing drive the mouth continuously. Silent bilabial contacts survive energy dips; F/V use their own lower-lip contact. A 70 ms smoothed energy curve modulates opening without deciding consonant identity. Sustained aligned silence settles to rest instead of letting low-level breathing or individual waveform fluctuations chatter the jaw.

The rig-independent control contract exports normalized jawOpen, lipSeal, lipRound, lipSpread, lowerLipContact and tongueVisible at the requested frame rate. These are animation targets, not measurements of this speaker's anatomy. Current registered mesh rendering consumes the same acoustic gesture weights; the new cartoon rig can consume those controls without changing alignment. The cartoon design remains the target; no new realistic character film is presented as progress on that design.

Every painted pipeline run now attempts alignment, saves the complete speech plan and exports a waveform/spectrogram/word/phone/control graph. Renderer fingerprint 4 prevents reuse of previous frames. Legacy V3/V4 default routes and the approved main updater are unchanged.

## Reproduction

Install requirements-painted.txt in the isolated painted environment, then run the existing animate_evan.py --character painted --script narration.txt route. Speech planning and plotting run using configured painted_python and painted_packages. To require an acoustic result directly:

```
python speech_planner.py narration.txt words.json narration.wav mouth.json speech-plan.json --require-alignment --fps 48
python speech_review.py speech-plan.json narration.wav timeline.png --start 8.4 --duration 2.5
```

Audio input to the aligner must be 16 kHz mono PCM16. `words.json` is the experimental word-level Whisper transcript; `mouth.json` holds Rhubarb acoustic cues. Unavailable alignment is reported as fallback, never labeled forced-aligned. `estimatedWords`, `estimatedPhonemes` and `recognitionWarnings` preserve the previous evidence separately.

## Review milestone

Real Evan recording: 66 script words, 248 acoustic phone intervals and 1,059 control samples at 48 fps over 22.05 seconds of analysis. All intervals are finite; 18 words are flagged for word-anchor disagreement. The P in “open” is acoustically placed at 0.60–0.65 s, compared with the earlier duration estimate around 0.52 s. The waveform and spectrogram show a pause/breath after “favicon” around 9.15–10.19 s; the new controls settle through it instead of generating vowel opening from that quiet breath.

Native-resolution waveform/spectrogram exports for the opening and pause were inspected. A fresh short MP3 pipeline verifies planning, graph generation, renderer consumption and encoding. The complete test suite has 59 passing tests, including inventory completeness, diphthong phases, contact timing, sustained long vowels, silent closures, bounded controls, continuity and explicit rejection/fallback. A high-rate sweep finds no nonfinite weights. Fast sound transitions remain fast: these tests do not prove perceptual smoothness or precise timing at every phone.

Limits: this is an older acoustic model with imperfect boundaries, not a ground-truth annotation system. All 66 words being assigned intervals does not mean all intervals are correct. Eighteen disagreements require audio/visual review, especially longer words and sentence boundaries. The inventory targets General American English, not every accent, language, nonverbal sound or possible spelling. Cartoon expression, asymmetry and lip/jaw art still require a proper layered rig and visual iteration; alignment alone cannot establish studio quality. Native Moho remains untouched.

Primary implementation reference: https://pocketsphinx.readthedocs.io/en/stable/pocketsphinx.html (two-pass set_align_text / set_alignment / get_alignment).

## Follow-up visual audit

See SPEECH-TIMING-REVIEW.md. All 18 flags received waveform/spectrogram visual review; current acoustic regions are better supported than multiple pause/tail errors in Whisper. Exact word/phone boundaries remain unverified; no timings changed. New experimental planning runs export a side-by-side audit and context clips. Spectrogram centers now use the actual recording sample clock.
