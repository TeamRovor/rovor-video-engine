# ROVOR proportional public-source context for new jobs

This implementation lives in **the existing PR #137 single LaunchAgent worker development branch**. It is NOT installed or activated by creating this file, and does not add another scheduler, change 144 rolling claims/day or 601-second spacing, create model requests, or retry old job IDs.

## Problem and implemented fix

Existing `omniroute_continuous.execute` asks for a short deliverable (previously **under 650 words**) but its approved v2 workpack may include up to **28,000 characters** of public repository source, irrespective of whether the job is a checklist, handoff, tests or plan. Inference on thinking-capable free models can use considerable output budget on processing this oversized context and produce no usable visible memo. The real Mac's previous sanitized receipt history included one `incomplete_length_stop` and other admission/upstream failures. **Source context is only one possible contributor, not a proven explanation for all failures.**

New tasks instead use the following fixed profiles (source characters; output words are upper-bound instructions, not counted as actual delivered words):

| Deliverable | Public source context cap | Requested output length |
| --- | ---: | ---: |
| Checklist | 9,000 chars | <250 words |
| Handoff | 9,000 chars | <300 words |
| Plan | 11,000 chars | <350 words |
| Tests | 14,500 chars | <450 words |

These are applied to **both** the curated continuous roles and pinned GitHub public task forms, not to generic model calls. Workpack reading remains a fixed allowlist of public source paths and source byte caps. Whenever a source exceeds the profile, the existing deterministic equal-share excerpt algorithm shows explicit `PUBLIC SOURCE EXCERPT` labels, full-file SHA256, included/omitted character totals and a warning **not to claim unseen source was reviewed**. No model chooses or edits excerpts. Full public files remain individually fingerprinted. Each new receipt records `source_budget_chars` in both its metadata and provenance. During private review the same exact budget is reapplied and its fingerprints recomputed. Tampered, unapproved or bool budgets are refused, and changing an old source still produces a stale receipt.

Legacy workpack calls and historical receipts **without** the new source-budget field follow their original unmodified full-source/review behavior; no old incomplete work is reprocessed, reapproved or retried. The earlier PR #154 versioned 4096-token completion-limit review warning is maintained and never used to assert genuine upstream billing, full answer completeness, or human acceptance. Any failed response still needs private review, STOP/failure-circuit guards remain, no paid fallback, and there is no automatic publication.

## Operating priorities

Deploy only through an explicit reviewed same-service Mac rollforward when safe; source merge is not deployment. First compare new receipt output readiness by form and by verified actual responding model under existing 144/day and 601-second global ceilings. If the real check shows quality improved, only then consider modest per-model size adjustments based on **fresh** model context/output capability, actual quota and $0 terms. A `:free` suffix alone is insufficient evidence. Keep one queue, the existing STOP/circuit and no replay rules. No unverified nine-model claim.

CI: `tests/test_omniroute_continuous.py`, `test_omniroute_draft_review.py`, `test_omniroute_workpack_runner.py` and `test_omniroute_workforce_composite.py` run on Ubuntu and macOS for Python 3.9 and 3.11 with mocked model calls.
