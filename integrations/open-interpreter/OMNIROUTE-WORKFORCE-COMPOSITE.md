# ROVOR ghost queue + OmniRoute: isolated source composite

**Status: source composite, not a Mac installation or unattended activation.**
This exact integration candidate starts from the existing PR #41 SQLite queue,
STOP control and bounded poller, then copies the reviewed 11 PR #51 inference,
receipt-review, packet manifest and test/CI files **without altering them**.
The existing PR #102 OmniRoute job kind remains off unless independently opted in.

## Why this is the next step

Actual October 23 Mac logs proved OmniRoute authentication, one HTTP 200
cost-reported-zero inference, three attempted public workpack jobs, private
receipts and a read-only on-Mac reviewer invocation. Those are not evidence
of automatic scheduled OmniRoute inference or native app control.

PR #41 now has the job adapter, but until this candidate its source tree did
not contain the `omniroute_workpack_runner`, `omniroute_draft_review`, or
three public packets that the adapter imports. A standalone queue branch
could import neither dependency. This candidate closes that source gap.

## Important compatibility and security boundaries

- The `runner-blocker` manifest expects
  `.github/workflows/rovor-mac-exec-proof.yml`, **absent** from this PR #41
  base. Do **not** restore a public-repository privileged self-hosted runner
  workflow to satisfy it. The existing workpack loader fails closed before
  contacting a model; the real-module integration test confirms this behavior.
  Review or retire this packet separately, rather than silently changing its
  authored source evidence.
- PR #66 / #71 actively own direct-API private receipt path hardening.
  This composite does **not** edit their source files or claim to include
  those pending changes. PR #51's direct API should not be exposed to
  arbitrary import callers until those changes are reviewed and integrated.
  The new queue adapter separately checks its private job destination against
  the checkout ancestors; this is not a general-purpose security audit.
- The gateway uses free-labeled OpenRouter models, but no assertion of
  guaranteed availability, per-account zero charges, or unlimited quota.
  There is a five-job rolling 24h SQLite claim cap, enforced before each
  job in the existing durable queue; a provider may impose a tighter cap.
- Even a successful model request is marked `needs_review` in SQLite; the
  existing receipt reviewer makes no claim to have fact-checked research.
- Every model turn requires the **separate**
  `--approve-omniroute-model-use` flag. The current local five-minute
  LaunchAgent remains unchanged and does **not** implicitly inherit approval.
- No public self-hosted GitHub Actions runner, new persistent agent, model
  install, social posting, filesystem deletion, Moho/Final Cut native GUI,
  paid fallback or silent replays.
- Copying reviewed source into this branch does not mean it has been
  deployed, merged into main, or loaded by the Mac's existing LaunchAgent.

## Hosted evidence

The new `test_omniroute_workforce_composite.py` suite exercises real code
paths with mocked inference and Keychain calls: a queued packet, real workpack
loader, private draft receipt, real reviewer verdict and SQLite
`needs_review` result. It explicitly proves that a removed runner-workflow
source cannot trigger inference. Additional focused queues, packet-security
and receipt-review suites run on Python 3.9 and 3.11.

**Host gates before actual unattended inference:** review source identities,
integrate pending PR #66 / #71 safety changes without overriding their owner,
verify one pinned composite checkout on the Mac, inspect existing LaunchAgent
plist/code snapshot/state/STOP and provider account billing, and run exactly
one newly authorized, bounded **foreground** OmniRoute queue job with private
receipts. Only then consider adding a separate approved model-use flag to
the existing LaunchAgent. Existing October 23 one-shot job receipts must
not be replayed or treated as reusable training data.
