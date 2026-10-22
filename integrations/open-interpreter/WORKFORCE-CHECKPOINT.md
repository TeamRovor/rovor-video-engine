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

Do not repeat research, MCP registration, DTD preparation or native dispatch to
address that receipt. The next host action is the existing read-only diagnosis:

```sh
python3 tools/jane_native_worker.py --diagnose
```

This observes process names, the known receipt, XML target and bounded nearby
library locations. It does not launch an app or read an application dialog.
Finding an existing default Untitled library does not attribute it to this job.
The probe cannot establish a live timeline, resolve a modal dialog or infer the
cause from a missing folder. Actual app observation is still required if the
read-only evidence cannot locate the import outcome.

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
`coordination/tasks.json` remains canonical. Its older FCP next-action text must
be reconciled with this Mac receipt when the shared task update is authorized.
Until then, read the current PR/checkpoint alongside main, as WORK.md requires.

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
