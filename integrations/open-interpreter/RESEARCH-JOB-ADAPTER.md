# Open Interpreter research job — bounded local adapter

**Status (2026-10-22): source committed for review, NOT deployed to Amar's Mac.** The existing Open Interpreter v0.0.56 background daemon had a platform error. This script is an isolated foreground Interpreter exec adapter that can run a single approved research job only after manual double opt-in. It is not a 24/7 ghost employee, a Final Cut connection, or an integration into the SQLite worker PRs #32–34.

Source: tools/interpreter_research_job.py. Offline tests: tests/test_interpreter_research_job.py. Example packet: integrations/open-interpreter/research-jobs/fcp-intro.example.json.

## Grounded interface

The current [Open Interpreter exec documentation](https://github.com/openinterpreter/openinterpreter/blob/main/docs/exec.md) describes interpreter exec - (prompt from stdin), --sandbox read-only, --ask-for-approval, --ephemeral and bounded one-off use. The wrapper launches exactly one local child process with no shell interpolation:

    interpreter exec --sandbox read-only --ask-for-approval untrusted --ephemeral -

Actual behavior on the user's Intel Mac remains unverified. Open Interpreter is the primary local ROVOR runtime; this does not substitute Codex. The repo's project-configured Jane and disabled FCPXML MCP are in [PR #37](https://github.com/TeamRovor/rovor-video-engine/pull/37), separate from this branch.

## Safe no-model dry run

From the repository checkout containing this branch:

~~~sh
python3 tools/interpreter_research_job.py \
  --workspace "$PWD" \
  --packet integrations/open-interpreter/research-jobs/fcp-intro.example.json
~~~

This validates exact packet fields and prepares a limited research prompt. It prints a packet SHA-256, prompt size and dry_run=true; **no model, MCP server, application or external service is started**. A packet must contain only version=1, a safe job_id, an allowed topic (final-cut-pro, moho-pro or blender), 1–6 short questions, and 0–4 local approved source files (.md/.txt/.json, each no larger than 12 KiB). Paths cannot escape the workspace through traversal or symlinks. Source text is marked as untrusted reference data; it is not an instruction.

Test without a model:

~~~sh
python3 -m unittest discover -s tests -p test_interpreter_research_job.py -v
~~~

## OPTIONAL one-shot real process (inference may cost money)

**Only after verifying the actual Mac's local Open Interpreter CLI/model, provider quota, effective MCP tool list and read-only sandbox behavior.** A command prompt cannot force a third-party MCP tool to obey read-only local shell permissions. Do not give this wrapper broad home directory access and do not launch it with unintended paid fallback. It deliberately does not install or configure a provider.

First prepare an existing private state directory outside the repository:

~~~sh
mkdir -m 700 "$HOME/.rovor-research-pilot"
~~~

Then, only with explicit approval to use that provider/model:

~~~sh
python3 tools/interpreter_research_job.py \
  --workspace "$PWD" \
  --packet integrations/open-interpreter/research-jobs/fcp-intro.example.json \
  --state "$HOME/.rovor-research-pilot" \
  --execute --approve-model-use --timeout 120
~~~

There is no automatic model billing cap here; the approval flag is a human confirmation, not provider enforcement. By default neither execution flag is passed. The tool records a private exclusive job_id.reserved marker before invocation, and private job_id.answer.txt and job_id.receipt.json after execution. Reusing a job ID is refused even after errors instead of replaying possibly billable work. A crash between reservation and receipt requires manual reconciliation.

The receipt records packet/prompt/answer hashes, exit code, elapsed time, status and verification flags. completed_unverified means only that a process returned exit 0 with a nonempty answer; it never means the cited facts or application actions were actually verified. needs_review, failed and timeout are not successes. On POSIX, the wrapper starts a new process session and kills its process group on timeout, output overflow, wrapper exceptions, and normal completion so ordinary descendants cannot keep running after the parent exits. Output is drained through pipes with a fixed 128 KiB limit per stream; overflow stops the group immediately, stdout retention never exceeds 128 KiB, and stderr is discarded. Child output is never spooled to disk. The bounded prompt alone uses a private temporary file. This is process cleanup, not an OS containment boundary: a process that deliberately creates another session or uses an external service can escape the group. Windows execution is refused before reserving a job; packet dry-run remains portable. No macOS runtime verification has occurred.

**Keep receipts and research answers local/private, out of GitHub.** Do not publish private client files, API keys or machine paths. This is an adapter experiment, not permission to reach websites, send email, post content or operate Final Cut.

## Why this improves ROVOR

The next milestone is one real, bounded Jane research attempt from Open Interpreter with an auditable result and no unauthorized side effects. Dry-run can be verified without inference. A verified local test does not imply an unattended agent.

Only after host-successful supervised trials should a new owner claim integration with existing SQLite queue/loop/launchd PRs #32–34. That later work needs durable at-most-once model dispatch, process-tree cancellation, STOP behavior, budgets, and a real schedule. A separate FCP read-only MCP proof must follow before editing and 1080p60 exports.

## Validation recorded

On 2026-10-22, the exact PR #38 base revision 0547e2586b46cc9677463597f1efbaa98137d75a passed all 17 offline tests on Linux. The process-bounds revision passes 22 offline tests, including continuous stdout/stderr floods, descendants after timeout and successful parent exit, and unsupported-platform refusal before reservation. Tests use a fake executable, with no model calls. The example packet dry-run also passes. No live Mac/Interpreter command, provider spend, MCP or FCP access was run; Mac host checks and unattended scheduling remain unverified.
