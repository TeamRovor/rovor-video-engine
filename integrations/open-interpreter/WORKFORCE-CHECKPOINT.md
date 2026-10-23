# Workforce integration checkpoint

## Current result and next action

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
| `python3 tools/jane_native_worker.py --execute` | Explicit single native job; blocked while prior manual attempt is unresolved |

The combined suite is stdlib on Python 3.11+. Python 3.9 tests additionally need
the test-only TOML parser `tomli==2.2.1`; runtime adapters remain stdlib. The CI
matrix installs it only in its 3.9 test environment. No model, GUI or package
server is launched by the offline tests; subprocess tests use local fakes.

## Integration order and completion criteria

1. **Integrated source:** PR #41 is the current worker/research/native candidate.
   It reuses PR #39 and the required source modules from PR #37, rather than
   merging animation work or maintaining several importer implementations.
2. **Host verified:** explain the already-observed missing-library outcome and
   establish one actual disposable import before enabling further native work.
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
