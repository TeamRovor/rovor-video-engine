# ROVOR Workload Distribution — telemetry contract v1 (read-only)

Status: **integration contract / not connected / not evidence of running workers**. Applies to the existing native v8.9 Workload Distribution popup in draft PR #148. This does not authorize model calls, spending, dispatch, social publishing, Mac access, or creation of a second scheduler.

## Existing sources

- `tools/omniroute_model_fleet.py`: reads Mac-local OmniRoute **configured** route membership with `rovor-...` combos. Its `routed_model_ids` are configuration, **not successful inference or free quota**.
- Named employees are Walter, Mike, Jane, Jesse, Gale, Gus, Saul and Hank; their identity is independent of the model that routes their work.
- `coordination/tasks.json` is a GitHub **development** queue. Never turn task claims into inference calls or worker time.
- Existing private Mac SQLite worker / STOP are to be reused; their runtime receipts are separate from the GitHub development queue.

## Snapshot schema for the future private authenticated backend

The authenticated, read-only controller should return a small bounded JSON response:

```json
{
  "schema_version": 1,
  "source": "authenticated_mac_controller",
  "snapshot_at": "2026-10-24T00:00:00Z",
  "host_last_seen_at": null,
  "inventory": {
    "checked_at": null,
    "expected_models": 9,
    "actual_models": null,
    "model_ids": []
  },
  "usage": {
    "state": "unknown",
    "completeness": "unknown",
    "windows": {
      "1h": null,
      "24h": null,
      "7d": null
    }
  }
}
```

When and only when event coverage is complete, each non-null `windows[period]` contains `request_count`, `model_counts` (exact inventory IDs mapped to nonnegative integers), and `employee_model_counts` (eight employee IDs mapped to exact-model counts). Include `request_count` even when it is verified zero; `null` means unavailable and must never render as 0. Required window boundaries are explicit UTC timestamps. Include a stable but opaque per-attempt receipt identifier in the private database for deduplication; never include raw prompt text or job payloads in the UI.

### Never confuse these measurements

- **Share:** requests for a model / all measured requests in the chosen complete window, not share of capacity.
- **Quota:** an independently verified provider allowance, if available. Unknown allowance remains null.
- **Tokens:** separate measured input/output token totals only if the provider supplies credible usage receipts. Do not infer tokens from requests.
- **Availability:** fresh authenticated provider/worker check; configured route presence is not online.
- **Worker load:** current leased/running runtime jobs with heartbeat, not GitHub task claims.
- **Source freshness:** expired controller/host snapshots must downgrade to UNKNOWN/OFFLINE.
- **Cost:** explicit provider billing evidence; a model name ending with `:free` does not prove zero cost.

## Transport trust boundary

This repo's GitHub Pages HUD is public static code. It must never fetch Mac localhost directly, hold private tokens in JavaScript, or expose user/client content. The future flow is Mac-initiated authenticated outbound updates to a private controller; the browser authenticates separately over HTTPS. The controller validates signed/integrity-protected host receipts, access control, freshness, model IDs, source timestamps and deduplication **before** claiming a live measurement.

Do not show demo values as real telemetry. The current popup's sample mode is synthetic and explicitly labeled. Keep the existing home screen, reactor, navigation, portrait/landscape geometry, and compact Workload panel layout unchanged except for scoped internal contents.

## Next implementation prerequisites

1. Produce a redacted Mac-local `omniroute_model_fleet.py` inventory report. Distinguish actual distinct routed IDs from provider connection entries.
2. Agree to the existing worker's **real** settled request receipt schema. Verify events correspond to unique actual inference attempts; do not infer missing job history.
3. Use the offline `tools/hud_workload_export.py` reducer only with reviewed sanitized data to test the count formulas. Its output is **not authenticated live telemetry** and must never be published as a live source.
4. Implement a private, authenticated read-only snapshot service, then integrate a vetted read-only viewer adapter without changing job dispatch.
5. Test zero vs unknown, duplicate receipts, stale host, interrupted worker, partial inventory, nine-model mismatch, mobile scroll and zero-cost protection.
