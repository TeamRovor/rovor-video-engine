# Workforce integration checkpoint

## Jane library-only durable worker integration (2026-10-22, PR #41)

**Implemented and hosted-tested in source, not yet executed on Amar's Mac.** Source-identical Jane library modules, onepass adapter and offline tests from PR #37 are now included in the existing PR #41 workforce candidate. PR #45 separately owns overlapping bootstrap error handling; reconcile before merging, never overwrite the concurrent branch.

The existing SQLite queue accepts `finalcut.library-create` with only a validated `{ "job_id": "slug" }`. The usual worker, research approval, and legacy `--allow-native-import` cannot select it. An explicit `--approve-jane-library-create` is required, and the action terminates with `needs_review` even if a library folder appears: **native Final Cut application selection is not verified**. Expired, crashed, or interrupted GUI attempts never requeue. STOP is checked before SQLite claim and immediately before native GUI action.

**One supervised Mac command, from a reviewed up-to-date PR #41 checkout:**

```bash
python3 tools/jane_library_worker.py --job-id jane-isolated-001 --create
```

Without `--create`, the command is an inert dry run with no DB setup; `python3 tools/jane_library_worker.py --status` inspects an existing queue in SQLite read-only mode. The launcher enqueues a stable deduped job and executes **only that exact SQLite UUID**. Repeating a job ID reports existing state, never GUI-replays. STOP prevents creating a latent queued GUI action. The generic loop, if used, requires `--approve-jane-library-create --jane-queue-job-id <exact-UUID> --max-jobs 1`; it cannot sweep several GUI tasks with broad approval. No model, XML import, existing library mutation, export or social posting is authorized by this queue kind.

**Acceptance gates:** first actual native library creation in a new uniquely named `.fcpbundle`; then separately prove Final Cut has selected that exact library; then and only then implement/approve a new isolated XML editing and export adapter. The old `fcp_native_auto_import.py --dispatch` remains unconditionally disabled following the proven unintended landscape insertion into pre-existing `~/Movies/Untitled.fcpbundle`. Do not retry prior native job IDs, use an old import command, or edit/delete Untitled.

The ROVOR worker still is **not** a continuously running Mac ghost employee. GitHub and hosted tests do not launch Final Cut on the user's Mac; a one-time approved foreground execution and independent app-selection proof are required.

---

## Current result and next action

**Native import correction:** the latest supplied Mac audit found the landscape
project's exact marker in the pre-existing Untitled library, while the requested
library was absent. Marker presence is not timeline verification. The subsequent
creation-only bootstrap failed at exit 1 without creating its target or importing
XML; the old receipt discarded the precise script error. PR #45 adds redacted
stage/error capture on the existing pilot, without authorizing a retry.

The legacy XML CLI `--dispatch` route is disabled before preparation. The durable
worker also no longer calls the historic importer: explicitly opted-in legacy
native jobs are recorded once as `needs_review`. The loop distinguishes native
import requested from enabled, and the launcher preview reports the reason.
Read-only jobs and separately opted-in Interpreter research remain available.
New native import requires independently verified isolated library creation AND
native app selection, followed by a replacement adapter. Do not re-enable the
historic route or treat tests as permission to import into an existing library.

One review checkout now contains the durable worker, poller, Interpreter research
adapter, native Final Cut diagnostic action, existing FCP status/probe tools,
disabled MCP configuration and their offline regression tests. It is an
integration candidate, not an installed or unattended service.

The newest supplied Mac receipt is from `fcp-jane-auto-20261022-183007`:
`status=native_library_not_observed`, `apple_event_sent=true`,
`library_creation_observed=false`, `last_dispatched=landscape`. The existing
manual status check confirmed the requested library was absent. Portrait was
not dispatched. This supersedes earlier notes saying the command had no result.

The latest supplied Mac UI probe (source `7860ab5d5840b8627c41071b54bec501efe4deee`)
already observed two Final Cut windows, zero sheets, and no recognized import,
library-picker or error title. It did not read UI contents or click controls.
The generic Untitled library was created on October 7, before the October 22
job; its modification time does not attribute it to Jane.

Do not repeat research, MCP registration, DTD preparation, the completed basic
process/window-title probes, or native dispatch. The import outcome is still
unexplained. The next host investigation must capture the actual import result
or application error on the existing disposable attempt, using a verified
Mac-backed session. Window titles and a zero Apple-event return are insufficient
to establish success. Do not create another import as a diagnostic shortcut.

## Consolidated repairs and verification

PRs #42, #43 and #44 are merged into this integration branch. PR #41 remains the
review candidate; these child merges do not deploy a service or merge the full
worker stack into main.

- Native XML diagnosis checks the original receipt hashes, exact orientation,
  linked format and single empty 30-second/60fps gap.
- Diagnosis now includes the durable queue's UUID-named output folders and
  manual attempts. One attempt retains its flat response; multiple attempts
  return a bounded `attempts` array. Missing/corrupt/symlinked evidence stays
  explicit; inspection neither initializes the queue nor retries an import.
- Queue initialization rejects pre-existing symlinked or nonregular database,
  WAL and shared-memory paths before opening SQLite.

All six changed code/test blobs on the consolidated branch match the locally
tested files. Linux Python 3.12.14: **164 offline tests pass** in 6.705 seconds.
Actual hosted [Python 3.9 and 3.11 checks](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39880072286)
both passed on repair head `57da42936b6fb90e45c80b4fb2ae2cced1e7581e`;
the 3.9 log confirms 164 tests in 6.965 seconds. The final merged code is
byte-identical to those tested modules. Earlier queue-diagnosis
[CI](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39879902562)
also passed. No new Mac runtime verification, model turn, native timeline,
installation or unattended operation is claimed.

## One command per purpose

| Command | Effect |
| --- | --- |
| `python3 tools/check_workforce.py` | All integrated offline worker, Interpreter and FCP test families |
| `python3 tools/jane_native_worker.py --status` | Read-only queue and manual-attempt checkpoints |
| `python3 tools/jane_native_worker.py --diagnose` | Existing read-only Mac probe, no native retry |
| `python3 tools/jane_native_worker.py` | Preview candidate selection without queue writes |
| `python3 tools/jane_native_worker.py --execute` | Records a review-required legacy job; native import remains disabled |

The combined suite is stdlib on Python 3.11+. Python 3.9 tests additionally need
the test-only TOML parser `tomli==2.2.1`; runtime adapters remain stdlib. The CI
matrix installs it only in its 3.9 test environment. No model, GUI or package
server is launched by the offline tests; subprocess tests use local fakes.

## Integration order and completion criteria

1. **Integrated source:** PR #41 is the current worker/research/native candidate.
   It reuses PR #39 and the required source modules from PR #37, rather than
   merging animation work or maintaining several importer implementations.
2. **Host verified:** resolve the failed creation-only bootstrap and establish
   isolated library creation plus native app selection before any replacement
   import adapter. The historic worker/CLI import routes remain disabled.
3. **Installed:** select an immutable tested revision and preserve the previous
   working checkout. A branch update must not replace an executing installation.
4. **Unattended:** reuse the existing LaunchAgent work in PR #34 only after
   integrating its prerequisites and verifying the intended job on the host.
   Research/native opt-ins must remain explicit; don't schedule them merely
   because the read-only scheduler exists.

These are release stages, not another development task or ownership queue.
`coordination/tasks.json` remains canonical. Its FCP evidence now records the
completed MCP and basic diagnosis rather than directing repeated setup. Read the
current PR/checkpoint alongside main, as WORK.md requires.

## Source provenance

Required FCP modules/tests were reused from pilot revision
`5ade85f`. The integration preserves the newer native importer checkpoints and
atomic receipts, PR #40 replay/hash checks, and cooperative STOP. The integration
adds the launcher route and accurate Apple-event return-code reporting. Existing
Blender configuration and role definitions are preserved. Both FCP MCP entries
remain disabled, with placeholder local roots and autopush off; copying these
settings neither connects an app nor enables a server.

The source queue/poller, Interpreter shim and process controls come from the
existing PR #39 stack. No second runtime queue, alternative model provider,
bulk skill installation, native GUI driver or public posting is added.
