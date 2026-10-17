# Reference speech timing: 18-word visual audit

The 18 word-anchor disagreement flags have now received waveform/spectrogram visual inspection across six regions. They are **visual-reviewed**, with **exact boundaries unverified**. No listening verification or ground-truth annotation is claimed. No word or phone timing, gesture weights or source plan has been changed. The flags remain available; review does not erase them.

The inspection record `evan-engine/reviews/evan-reference-timing-v1.json` carries the exact audio and plan hashes, both hypotheses per flagged word, six observations and remaining uncertainty. Local review outputs contain native graphs, six context audio clips, an HTML review page, and normal/quarter-speed head diagnostics across the pause and renewed speech onset (8.9583–10.8333 s). These films use the existing layered cartoon head and current acoustic plan; they demonstrate current behavior rather than a new artwork-quality milestone.

## Findings

- Tiny/little: Whisper changes words at 2.36 s inside sustained vowel structure. The acoustic split at 2.65 s fits the visible region better; coarticulated L remains unverified.
- That's/not/some/random/browser: Whisper places that's and not largely in the 4.85–5.35 s pause. Acoustic speech onset near 5.36 s follows the observed structure. Internal boundaries are hypotheses.
- It's/basically/a/tiny/version/of/your: Whisper places it's/basically largely over the pause and low-level broad-band breath. Acoustic onset at 10.19 s fits resumed speech and preserves the pause. All seven exact word splits remain unverified.
- Browser/tabs: Whisper starts tabs at 14.42 s after much of its visible structure; acoustic tabs at 13.95–14.42 s better encloses onset, vowel and final frication.
- Finished: Whisper extends to 19.44 s over later broad-band breath. Acoustic end 19.11 s better fits the structured word. F and the final stop still need phonetic review.
- Digital: Whisper starts at 21.65 s after several visible structures and ends at 22.4 s, beyond the 22.047375 s recording. Acoustic 21.32–21.76 s better encloses the word. Exact phones remain unverified.

Quiet energy does not mean a mouth must always be closed: unvoiced consonants and stop closures are meaningful. The audit reports 20 ms RMS fractions below -40 dBFS as supporting evidence only; it never automatically changes timings. Full listening/phonetic annotation by an experienced reviewer remains the next step for exact boundaries.

## Engine integration

`speech_alignment_audit.py PLAN WAV DIRECTORY` exports a side-by-side audit of every flag, with recording-clock FFT window centers, both word hypotheses, phones and context WAVs. `speech_review.py --audit-dir DIRECTORY` invokes it for acoustic plans. New experimental painted planning runs export this automatically; the shared speech system is reused by the cartoon studies. Existing cached scenes are not automatically rerun. V3/V4, main, approved updater and native Moho are untouched.

The existing spectrogram previously stretched FFT windows to the requested interval endpoints. Both review paths now use actual sample-centered windows, avoiding roughly half-window shifts at the edges. This corrects the evidence display, not the aligner. 75 checks pass, including an impulse-clock regression and evidence-window coverage. The review CLI was also run end-to-end with the actual narration.

Next animation work: improve hidden shoulder/neck surfaces and genuinely distinct hand drawings; continue F/V and expression cleanup. Do not infer studio-quality animation or perfect phoneme timing from this audit.
