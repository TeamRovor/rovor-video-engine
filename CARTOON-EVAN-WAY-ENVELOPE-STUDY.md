# Assigned W: isolate the control loss before changing timing

Historical partial-control trial. CORRECTION: the old in-memory patch did not replace the function already imported by rounded_cartoon_head. See CARTOON-EVAN-SUSTAINED-W.md for corrected fresh-import renders, the full-control follow-up and current development behavior. Measurements below belong to the earlier partial trial, not the complete archived source patch.

The near-rest mouth inside the assigned `way/W` interval is primarily caused by the capped midpoint consonant pulse. It is **not caused by a silence gate** in this recording window. The assigned W boundary itself remains unverified. This finding rules out removing silence protection as a fix.

At 18.225s, current rounded F weight is 0.000264596 and rest X is 0.999735404. Removing all explicit silence intervals changes no weight anywhere 17.7–18.5s; none intersects that window. Disabling energy modulation leaves F at 0.000321883. The non-vowel kernel uses a radius capped at 140ms, centered 18ms early; it has almost expired here despite the assigned W continuing until 18.27s. W salience is also 0.4, so even its peak retains substantial rest. The existing waveform/spectrogram shows weak periodic energy rather than proving a silent pause. Neither amplitude nor these ablations establishes an exact sound boundary.

## Bounded trial and decision

Reused the existing sustained vowel envelope for W only in an isolated in-memory trial. No phoneme/word/audio/energy/source art edits; original contact, silence and salience rules retained. At 18.225s trial F is 0.328810616. Exact patch saved as `evan-engine/reviews/unaccepted-sustained-w-v 1.patch`, against 7d 7e 7a 6. **Patch is NOT applied to production.** All engine Python files remain identical to that commit.

Rendered the actual ten-plane review face with current phonetic corners and matched jaw, comparing current/trial for source frames 850..897 (one second). `outputs/evan-cartoon-way-envelope` contains voiced 48-frame normal and muted 192-frame quarter-speed films, all 48 native mouth pairs, and full-resolution native heads. All pairs and native 875 were inspected. The trial makes the line fuller and opens earlier around 861, but 875 remains a thin horizontal smile rather than a convincing pursed W. It also changes the anticipatory transition into EY. This is an unaccepted experiment, **not a lip-sync improvement ready to ship**. Other three W occurrences were not rendered. No independent listening or real-time playback acceptance.

Original PCM sample range 283333:299333 is copied verbatim; full normal AAC decode returns exactly 16000 samples. Both movies fully decode,48/192frames. Current oral/chin pixels at 882 match the frozen previous proof; all 48 current/trial upper 288rows are exact. No new PSD export was needed: the existing source planes and registration did not change.

All 1307 full-recording frame/phone-midpoint geometry checks pass with min jaw area 28.09090. These checks include all four W occurrences. Width max step 13.84723 unchanged, p 956.23685→6.30439 (worse), four individual steps grow>1px. LowerY max 14.66776 unchanged, p 956.19515→6.10012; one step grows>1px. Chin max 2.30136 unchanged. Seven focused self-checks confirm unchanged P/M/F/V/AO/EY weights and retained explicit-silence rest. These checks validate isolation, not performance quality.

## Next concrete work

Keep the current planner and 7d 7e 7a 6 review face. Build a convincing authored pursed/rounded near-closed lip pose, with upper/lower lip volume and corners that read as a rounded approximant at native size; compare pure F and mixed/rest poses before adjusting envelopes. Continue the unresolved vertical release/short-AO work separately. Do not retime or remove silence guards merely to conceal inadequate drawings. Verify W/EY against independent listening before accepting a sustained assigned span. Human animator judgment or matched lip redraws may still be necessary.

The 18 original flagged regions and three quiet-phone warnings remain unresolved for exact listening/boundaries. No Moho launch/probe, merge, deployment or updater/release changes. Polished cartoon milestone incomplete; automation stays active.
