"""Fixed, review-gated specialist feeder for the EXISTING ROVOR SQLite queue.

One immutable draft job per idle scheduled tick. Seven independent specialist
tracks, 14 checked-in public-only tasks. No new daemon, remote prompts, paid
fallback, command execution, unbounded retries, or self-enqueued model output.
"""
import json
import os
from pathlib import Path

import ghost_worker as worker
import omniroute_workpack_runner as workpack

LEGACY_PLAN = (("unattended-readiness", "rovor-scheduled-unattended-readiness-v1"),)
ROLE_PLAN = (
    ("mike", (("walter-v1-mac-worker-stop-recovery", "walter-public-v1-mac-worker-stop-recovery"), ("walter-v1-omniroute-failure-boundaries", "walter-public-v1-omniroute-failure-boundaries"))),
    ("jane", (("walter-v1-finalcut-source-first-process", "walter-public-v1-finalcut-source-first-process"), ("walter-v1-fcpxml-handoff-acceptance", "walter-public-v1-fcpxml-handoff-acceptance"))),
    ("jesse", (("walter-v1-moho-viseme-review", "walter-public-v1-moho-viseme-review"), ("walter-v1-animation-checkpoints", "walter-public-v1-animation-checkpoints"))),
    ("gale", (("walter-v1-blender-isolation-plan", "walter-public-v1-blender-isolation-plan"), ("walter-v1-render-confidence-rubric", "walter-public-v1-render-confidence-rubric"))),
    ("gus", (("walter-v1-safe-client-intake", "walter-public-v1-safe-client-intake"), ("walter-v1-business-delivery-checkpoints", "walter-public-v1-business-delivery-checkpoints"))),
    ("saul", (("walter-v1-outreach-draft-review", "walter-public-v1-outreach-draft-review"), ("walter-v1-social-content-safety", "walter-public-v1-social-content-safety"))),
    ("hank", (("walter-v1-proof-before-done", "walter-public-v1-proof-before-done"), ("walter-v1-free-route-usage-audit", "walter-public-v1-free-route-usage-audit"))),
)
# Round-robin first-stage release so every role can start independently.
# Only then release each role's second stage after its own first draft is ready.
PLAN = (LEGACY_PLAN + tuple(stages[0] for _role, stages in ROLE_PLAN)
        + tuple(stages[1] for _role, stages in ROLE_PLAN))
DEPENDENCIES = {stages[1][0]: stages[0][1] for _role, stages in ROLE_PLAN}


def _review_ready(conn, dedupe_key):
    row = conn.execute("SELECT status,result FROM jobs WHERE dedupe_key=?",
                       (dedupe_key,)).fetchone()
    if not row or row["status"] != "needs_review" or not row["result"]:
        return False
    try:
        result = json.loads(row["result"])
    except (ValueError, TypeError):
        return False
    return (isinstance(result, dict)
            and result.get("draft_status") == "draft_completed_needs_review"
            and result.get("review_status") == "draft_ready_for_human_review")


def feed(conn, state, root):
    """Enqueue one distinct reviewed public packet; never invoke a provider."""
    if os.path.lexists(Path(state) / "STOP"):
        return {"status": "stopped", "submitted": 0}
    # Do not reorder existing work or increase the existing model claim budget.
    if conn.execute("SELECT 1 FROM jobs WHERE status='running' OR "
                    "(status='queued' AND kind=?)", (worker.OMNI_KIND,)).fetchone():
        return {"status": "existing_work", "submitted": 0}
    blocked = 0
    for packet, key in PLAN:
        if conn.execute("SELECT 1 FROM jobs WHERE dedupe_key=?", (key,)).fetchone():
            continue
        prior = DEPENDENCIES.get(packet)
        if prior and not _review_ready(conn, prior):
            blocked += 1
            continue
        workpack.load_packet(Path(root), packet)
        if os.path.lexists(Path(state) / "STOP"):
            return {"status": "stopped", "submitted": 0}
        job = worker.enqueue(conn, worker.OMNI_KIND, {"packet": packet}, key)
        return {"status": "submitted", "submitted": 1, "job_id": job}
    return {"status": "role_review_blocked" if blocked else "plan_exhausted_review_required",
            "submitted": 0, "blocked_roles": blocked}
