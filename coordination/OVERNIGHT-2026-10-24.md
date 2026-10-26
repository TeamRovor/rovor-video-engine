# ROVOR — overnight operations handoff (Oct 24–25, 2026)

## No service restart tonight

The live Mac LaunchAgent `com.rovor.ghost-worker.readonly` has previously demonstrated real paced task claims and a fresh status heartbeat. The last verified Mac snapshot on Oct 24 showed 31 claims in its preceding 24-hour window, of which 10 produced review-ready drafts, 12 were model attempts not review-ready and eight were pending/failed review, with one running. The snapshot is **not** a live check at the time of this handoff. Do not say that 31 jobs succeeded, or that nine models are actively running.

The operator configured **nine OmniRoute provider connection entries**. The real October 24 routing audit identified just **three distinct ROVOR-routed model IDs** across four combos, with all eight role packets going through the same two-model fast combo. This handoff does not change their routing, billing, quotas or activation. Historical evidence for each count is in the current `coordination/tasks.json` / PR #137 comments; metrics may change while the Mac is running.

## Work added tonight that the already-installed worker can consume

Four source-grounded public research tasks have been added to the existing **main** GitHub queue with `status=ready`, `priority=1`, explicit separate routing lanes and lexically early IDs:

1. `a-overnight-01-hank-quality-triage`: categorize **code-level**, not guessed provider-specific, causes of incomplete/rejected drafts; propose independently testable changes
2. `a-overnight-02-mike-same-worker-rollout`: reviewed same-service upgrade and rollback acceptance plan preserving STOP, quotas, worker identity, SQLite, active jobs
3. `a-overnight-03-saul-business-draft`: evidence-grounded ROVOR website service offer and lead intake drafts, no fabricated claims or live outreach
4. `a-overnight-04-jane-fcp-handoff`: original-source-first 1080p60 portrait/landscape, caption and narration acceptance package, no live editor action

The installed `omniroute_continuous.py` reads this public main queue at a pinned commit and seeds one **new deduplicated** `research.omniroute` assignment at a time. Each eligible task has four independently identified forms (`plan`, `checklist`, `tests`, `handoff`), so this is **at most 16 distinct potential review-only drafts** over multiple ticks, not 16 guaranteed successes and not four concurrent provider workers. Earlier queued jobs and current global claim spacing/rolling quota take precedence. This is deliberately finite; once exhausted the feeder can continue its existing distinct approved catalogue. Never loop, rerun historic failures or synthesize filler to keep a gauge high.

## Morning acceptance

- **First:** Check Mac actual worker heartbeat and existing SQLite outcomes using the previously validated one-command read-only `tools/omniroute_ops_snapshot.py`; fresh numbers override this historical handoff. One snapshot is enough, not repeated multi-command setup instructions.
- **Second:** Determine which of the overnight **deduplicated public task IDs and forms** produced private `draft_ready_for_human_review` receipts; count nonready, incomplete and stale outcomes separately. Never post private draft text, keys, logs or client data to GitHub. Source branch/PR merge success only proves queue configuration.
- **Third:** Human-review useful drafts, choose at most one evidence-backed highest-value recommendation per task and turn it into a scoped tested code/website/video deliverable. Mark public research as reviewed, **not** executed or approved, until independently verified.
- **Fourth:** Inspect actual account model IDs, eligible $0 entitlements, quotas, context ceilings and usable canary receipts before activating more of the nine configured connections. Do not invoke an unrestricted auto/paid route. Optional source-only proportional router and atomic reservations on PR #137 branch are **not** already installed on Mac.
- **Fifth:** If the Mac slept, lost Wi-Fi, its STOP file exists, or the failure circuit opened, report the truthful state; do not restart/reconfigure automatically without authorization.

**User-friendly overnight posture:** Mac plugged in, Wi-Fi available, and kept awake under normal user settings; an on-disk STOP file and existing circuit still override schedules. ChatGPT in this conversation is not itself an unattended Mac process.
