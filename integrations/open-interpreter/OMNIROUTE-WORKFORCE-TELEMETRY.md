# ROVOR HUD — real OmniRoute workforce telemetry (read-only)

The main operator dashboard must not label a successful scheduler tick, SQLite claim or `needs_review` job as an approved deliverable. The Mac worker can place either a valid review-ready draft or a failed inference attempt into `needs_review`. A provider-model reservation is not proof of a completed upstream model POST. The user explicitly wants 24/7 useful production, proportional task sizing and maximized eligible model usage. This tool supplies auditable counts without inventing any outcomes.

## Read-only host usage

From a reviewed checkout of PR #137 that includes this module and its existing dependencies:

```bash
python3 tools/omniroute_workforce_telemetry.py --state "$HOME/Documents/Codex/2026-10-22/new-chat/jane-worker-state"
```

The probe uses `omniroute_dispatch_pacing.snapshot` for a stable copy of the existing SQLite/WAL database (no live DB writes), reads only the exact `continuous-status.json` heartbeat, and emits one JSON aggregate with `schema_version=1`. It **never** reads private draft files, receipt contents, provider configs, credentials, raw job prompts or stored job errors. The HUD can use this exact local JSON as its workforce workload-distribution data source; send it over an authenticated local/private channel only. The module uses no OmniRoute CLI, gateway, external network, arbitrary script or model call.

## Definitions

- `claims_last_24h`: count of internal SQLite `claimed` event records, not proved upstream provider POSTs.
- `distinct_claimed_jobs_last_24h`: unique claimed research jobs (shows duplicates separately).
- `review_ready_drafts_total`: job is `needs_review`, draft status `draft_completed_needs_review`, review status `draft_ready_for_human_review`; means ready **for** human review, not accepted or factually verified.
- `model_attempt_not_review_ready`: failed/no-auto-retry results. `pending_or_failed_review` includes unclassified or rejected draft reviews; never count those as successfully delivered.
- `human_accepted_outputs_verified=false` and `provider_http_completions_verified_by_this_probe=false`: this probe cannot prove either, so it refuses to invent those metrics.
- `models_with_reservation_evidence`: if the new optional atomic reservation table exists, group reservation counts by configured selected model ID; never assert it equals actual response provider or the number of configured OmniRoute connections.
- `claims_without_model_reservation_last_24h`: old/legacy route claims have no exact selected model evidence. Do not allocate them evenly across nine models.
- `heartbeat.recent`: whether most recent recorded scheduler heartbeat is within 20 minutes; an old heartbeat is a **visibility gap**, not definitive machine-down proof.
- `heartbeat.last_tick_dispatch_reason=no_queued_work` + `last_tick_executed_claim_or_job=1` is often simply the moment immediately after the worker consumes its only queued job. It does **not** establish a stalled feeder.

## Integration and safety

The prior terminal transcript after activating PR #137 showed 22 claims / 24 hours, 22 `needs_review`, 0 queued after a tick, but did not distinguish successful draft output from failure. This probe does; do not publish redacted-private data outside the owner HUD.

The current installed Mac worker is pinned at `b736610...`, which predates the optional fleet routing integration in PR #147 and this module. Source CI success **does not deploy telemetry on Mac**. Run the probe in read-only mode from an up-to-date reviewed checkout; **do not rerun the installer, reset SQLite, or reboot the service**. Feed results into the existing branded ROVOR workload distribution tab later, replacing simulated gauges with literal counters and unknown where evidence is absent. For a 9-resource fleet, per-model quota reset, current cost and eligibility need a separate trusted read-only OmniRoute host-source adapter (e.g. documented quota/status/usage views) and should remain unknown otherwise.
