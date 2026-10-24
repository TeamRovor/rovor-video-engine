# OmniRoute — one-command operations snapshot, ROVOR HUD-ready

No new launchd service, scheduler, worker, model inference call, model route change, SQLite mutation, or reinstall. The inspector itself never opens credentials; the installed OmniRoute CLI may load its own private environment while servicing metadata commands. All CLI output is captured and filtered, never copied raw.

## The one safe Mac command

From an existing ROVOR git clone, without checking out a new runtime:

```bash
ROOT="$HOME/Documents/Rovor/OmniRoute-Continuous-137"
git -C "$ROOT" fetch --quiet origin main &&
git -C "$ROOT" show "FETCH_HEAD:tools/omniroute_ops_snapshot.py" |
    python3 -
```

This script is **standalone** and needs only system Python3.9+ and the already-installed OmniRoute executable. It reads the existing local SQLite state using a read-only connection and consistent in-memory backup, the fixed-name bounded scheduler heartbeat, and runs only these **read-only** OmniRoute CLI inventory/status commands:
`--version`, `providers list --json`, `combo list --json`, `models --json`, `quota status --json` (fallback `quota --json` if needed). Every child command uses bounded timeout and captures stdout/stderr without echoing it. It outputs one JSON record that the ROVOR HUD workload distribution view can consume.

Strict interpretation:
- Claim events are not evidence of provider HTTP POSTs, accepted business deliverables, or per-model inference.
- `draft_ready_for_human_review` means a draft exists for review, not that its claims are fact-checked or approved.
- 9 provider connection entries are NOT 9 verified active model IDs. The current user Mac audit on 2026-10-24 showed 9 entries, **3 distinct ROVOR-routed model IDs**, four combos, and all 8 roles pointing to the fast combo.
- `:free` model suffix and `quota status` existing are NOT a proof of actual $0 billing entitlements, healthy provider, fresh remaining limit, or accepted response. The report's entitlement and full nine-model flags remain false; no automatic paid failover.
- The output exposes only sanitized known provider types, regex-bounded routed model IDs, recognized ROVOR combo names, bounded status counters and safe fixed heartbeat fields; it doesn't reproduce account IDs, keys, raw errors, prompts, stored receipts, or private content.
- If CLI evidence is inaccessible, the relevant status is unavailable. The worker may still be running.
- It chooses one **next priority**, based on actual review-ready percentage and model coverage, so repeated chats stop rediscovering the same issue.

Follow-up integration is to feed this one JSON object into the existing ROVOR HUD *Workload Distribution* view. The optional capacity selector, shared-pool SQLite reservation and single-model routing are already reviewed as PR #147 and remain deliberately disabled on the actual installed worker pending trusted quota/cost/canary evidence. No additional setup loops, simulator jobs, second service or automatically replayed failed tasks are warranted.

The existing production Mac LaunchAgent label `com.rovor.ghost-worker.readonly` stays untouched. This is a read-only operator observability utility, **not a replacement for live nine-model utilization**.
