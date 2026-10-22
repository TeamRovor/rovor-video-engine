# Open Interpreter research job — bounded local adapter

**Status (2026-10-22): source committed for review, NOT deployed to Amar's Mac.** The existing Open Interpreter v0.0.56 background daemon had a platform error. This script is an isolated foreground Interpreter exec adapter that can run a single approved research job only after manual double opt-in. It is not a 24/7 ghost employee, a Final Cut connection, or an integration into the SQLite worker PRs #32–34.

Source: tools/interpreter_research_job.py. Offline tests: tests/test_interpreter_research_job.py. Example packet: integrations/open-interpreter/research-jobs/fcp-intro.example.json.

## Grounded interface

The current [Open Interpreter exec documentation](https://github.com/openinterpreter/openinterpreter/blob/main/docs/exec.md) describes interpreter exec - (prompt from stdin), --sandbox read-only, --ask-for-approval, --ephemeral and bounded one-off use. The wrapper launches exactly one local child process with no shell interpolation:

    interpreter exec --sandbox read-only --ask-for-approval untrusted --ephemeral -

Actual behavior on the user's Intel Mac remains unverified. Open Interpreter is the primary local ROVOR runtime; this does not substitute Codex. The repo's project-configured Jane and disabled FCPXML MCP are in [PR #37](https://github.com/TeamRovor/rovor-video-engine/pull/37), separate from this branch.

## One-command local diagnostic

From this reviewed branch checkout, run:

~~~sh
bash integrations/open-interpreter/research-preflight.sh
~~~

This prints the checkout commit, tracked-file cleanliness and tested source blob identities; runs the offline fake-Interpreter tests and example packet dry-run; then inspects the host and runs only `interpreter --version` and `interpreter exec --help`. Each CLI probe has a 10-second timeout and POSIX process-group cleanup. Raw CLI diagnostics and config contents are omitted. No installs, provider selection, inference, MCP calls or persistent report files are requested. Tests use temporary fixtures; Python bytecode writes are disabled.

Exit 0 means these prerequisite checks passed on a Mac. It does **not** verify effective project settings, provider budget, foreground `/agent`, `/mcp`, FCP access or a real research job. Exit 2 reports a non-Mac host, missing/incompatible CLI, missing project config or failed CLI probe; test/packet failures stop earlier with their own nonzero status. Modified tracked files are prominently labeled rather than represented as an exact committed checkout. Inspect untracked config locally as well; it is not assessed by the cleanliness check.

Use an isolated checkout/worktree containing PR #38; do not paste this command into the Interpreter conversational prompt or reset another working directory to obtain it. Share the diagnostic text if host checks are blocked; it contains no requested account/config dump. Real CLI startup may still create its own caches or contact its update service: the diagnostic does not override third-party startup behavior.

## Real Mac test failure and correction (2026-10-22)

Amar ran the exact PR #38 preflight on his Mac from a clean detached worktree at commit 800f1de. The script and source retrieval **worked**, but the 26-test suite stopped before CLI probes: **20 tests errored with** `Source must be an existing regular file inside the authorized workspace`. Affected tests called `read_packet` directly with a macOS temporary-directory spelling (commonly `/var/...`); `Path.resolve()` canonicalizes the child as `/private/var/...`, while the original root remained unresolved. This was **not evidence that Interpreter was missing or unable to start**.

The follow-up branch normalizes the validated workspace before candidate comparison and before private state/workspace overlap checks. Added regression tests for a symlink alias in an *ancestor* (allowed after canonicalization), a symlink at the workspace root (still denied), and disjoint-state checks across alias spellings. **The full 29-test suite and the Mac's actual Interpreter CLI still require re-execution on the corrected branch.** Never treat the earlier Linux 26/26 report as a passing Mac result.

From the already-created **rovor-pr38-check** worktree, first inspect any local edits, then fetch the refreshed PR head and switch the detached test worktree only if it is clean:

~~~sh
cd "$HOME/Documents/Rovor/rovor-pr38-check" || exit 1
git status --short
git fetch origin pull/38/head
git switch --detach FETCH_HEAD
bash integrations/open-interpreter/research-preflight.sh
~~~

This still does **not request inference or enable FCP MCP**. If the tests pass, the diagnostic will proceed to version/help-only probes of the installed `interpreter`. If errors persist, report their **first traceback and final test summary**, rather than retrying installations.

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

## Stop or cancel a foreground job

Create `STOP` inside the same private state directory used for execution:

~~~sh
touch "$HOME/.rovor-research-pilot/STOP"
~~~

If present before dispatch, no process starts and no job reservation is created. While a job runs, the wrapper checks for STOP during its polling loop (normally every 50 ms), stops the POSIX process group, and writes a `cancelled` receipt with the exit code and any partial answer. Any directory entry named STOP, including a broken symlink, blocks execution; its contents are never read. All jobs using that state directory observe the same stop request.

Ctrl-C while the child is running also stops its group and writes a cancelled receipt. Cancellation returns a nonzero CLI status. It does not undo prior external actions, terminate deliberately detached processes, or guarantee interruption of an in-flight provider request or its billing. SIGKILL, machine failure and external SIGTERM are not receipt-preserving shutdown mechanisms. A STOP request is polled, so dispatch and STOP creation are not an atomic transaction.

After inspecting the receipt and any possible external effects, remove only the STOP marker to permit future distinct job IDs:

~~~sh
rm "$HOME/.rovor-research-pilot/STOP"
~~~

Keep the cancelled job's reservation and receipt. Removing STOP does not permit replaying that job ID. Dry-run does not inspect private state and remains a no-model validation, even when execution would be stopped.

## Why this improves ROVOR

The next milestone is one real, bounded Jane research attempt from Open Interpreter with an auditable result and no unauthorized side effects. Dry-run can be verified without inference. A verified local test does not imply an unattended agent.

Only after host-successful supervised trials should a new owner claim integration with existing SQLite queue/loop/launchd PRs #32–34. That later work needs durable at-most-once model dispatch, process-tree cancellation, STOP behavior, budgets, and a real schedule. A separate FCP read-only MCP proof must follow before editing and 1080p60 exports.

## Validation recorded

On 2026-10-22, the exact PR #38 base revision 0547e2586b46cc9677463597f1efbaa98137d75a passed all 17 offline tests on Linux. The process-bounds revision passes 26 offline tests, including continuous stdout/stderr floods, descendants after timeout and successful parent exit, unsupported-platform refusal before reservation, STOP before/during dispatch, broken STOP symlink and Ctrl-C cancellation receipts. Tests use a fake executable, with no model calls. The example packet dry-run also passes. No live Mac/Interpreter command, provider spend, MCP or FCP access was run; Mac host checks and unattended scheduling remain unverified.
