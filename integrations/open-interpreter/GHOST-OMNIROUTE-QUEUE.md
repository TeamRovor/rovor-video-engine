# ROVOR — opt-in OmniRoute drafts in the existing ghost queue

**Scope:** Source-only adapter layered on PR #41's SQLite worker. This is not another
scheduler or agent. It does not activate existing Mac launchd, access Final Cut,
send emails, post social media, edit media, run shell commands from a model, or
complete a GitHub project task.

The job kind `research.omniroute` takes **only** `{"packet": "<known-packet>"}`.
Allowed packets are `runner-blocker`, `supervisor-resilience`, and
`provider-efficiency`. They are the fixed public-repository workpacks already
specified in OmniRoute PR #51. No private documents, media, arbitrary task
prompts, URLs, uploaded content, or extra job arguments are forwarded.

## Fail-closed prerequisites

1. A reviewed, coherent local source tree must contain PR #41 ghost worker code
   **and** PR #51's `tools/omniroute_workpack_runner.py`,
   `tools/omniroute_draft_review.py`, and three fixed packet manifests.
   This feature branch alone intentionally does **not** vendor or overwrite
   the separate OmniRoute owner’s files. Integration remains blocked until
   these code streams are intentionally combined and tested.
2. The local OmniRoute CLI must provide `omniroute combo list --json` and
   match the October 23 ROVOR free-only OpenRouter combos exactly in model
   identity and priority order. Extra/paid model fallbacks fail the job.
3. The local gateway and saved inference Keychain entry must be working.
   The configured `:free` variants do not guarantee a particular provider
   rate limit, continued free-tier eligibility, or third-party spending
   controls. Verify account/provider billing policy separately.
4. Existing SQLite queue state remains private and *outside* public Git
   checkouts. Use the preexisting LaunchAgent and STOP control; this patch
   neither installs nor reconfigures them.

## Deliberate opt-in

The existing worker does not claim OmniRoute jobs by default. Its prior
`--approve-model-use` flag continues to authorize *only* the Open Interpreter
research adapter, **not OmniRoute**.

A reviewed Mac runtime could explicitly enable a bounded run using
`ghost_worker.py run-once --approve-omniroute-model-use` or
`ghost_worker_loop.py run --approve-omniroute-model-use`, with their usual
`--state` and `--workspace` arguments. The currently installed LaunchAgent
must **not** be modified or activated by this source PR. Only after the
co-located code is host-tested, a separate approved Mac change may add the
flag to the trusted existing schedule.

A transactionally enforced **maximum five OmniRoute job claims in a rolling
24-hour period** applies to this SQLite state directory, independent of
available provider quota. Extra jobs remain queued (not retried) until the
window passes. Every AI job uses one immutable SQLite dedupe key, can execute
once, and cannot be automatically replayed after crash, timeout, or rejection.
STOP prevents job claiming and is checked again before inference, but does
not interrupt an already running provider request.

## Output and approval

The reviewed workpack writes private per-SQLite-job receipts inside
`<state>/omniroute-drafts/<job_uuid>/<packet>.receipt.json`.
Only a small receipt path and review status enter the SQLite result. Every
model request transitions to `needs_review` — never `succeeded`. Even an
HTTP 200 or `draft_ready_for_human_review` is not factual verification or
production readiness. A failure keeps a generic, nonsecret error in SQLite;
provider diagnostics and answer text are never posted to the public repo.
The implementation has **no auto-enqueue**, no remote jobs, no automatic
approval and no command execution based on generated text.

## Verification

`python3 -m unittest discover -s tests -p 'test_ghost_omniroute_job.py' -v`
runs offline with mocked model and review modules. It tests separate approval,
payload confinement, route drift, STOP, SQLite at-most-once, bounded rolling
quota, and redacted failures. Hosted Linux tests validate source only — not
a real Mac, installed LaunchAgent, OpenRouter costs, or app control.

**Next host checkpoint:** after a reviewed composite code revision exists, run
the offline suite and read-only `omniroute combo list --json` on the Mac;
verify the existing LaunchAgent's exact pinned runtime and state before
approving one new queued OmniRoute job. Do not replay any of the three
October 23 receipts or automatically continue the failed runner packet.
