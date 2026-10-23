# Jane — selected native Final Cut library: read-only acceptance evidence

**Owner / scope:** Mac-runtime lane per [PR #41 parallel handoff](https://github.com/TeamRovor/rovor-video-engine/pull/41#issuecomment-6355619140). The independent iPhone lane is reviewing code/merge conflicts; PR #45 owns bootstrap error handling. This tool neither replaces nor changes those jobs.

**Status:** `tools/fcp_jane_selected_library_probe.py` is implemented for **an existing successful, isolated native library creation**. It has not inspected Final Cut on the owner's actual Intel Mac. It does not run a model, access Open Interpreter, create a library, import XML, edit a timeline, close another library, export, or publish.

## Why filesystem existence isn't enough

October 22's real native XML attempt inserted the exact landscape test marker into the pre-existing `~/Movies/Untitled.fcpbundle` rather than the intended new test library. A later separate File → New → Library attempt failed before the target library was created. Therefore neither an `osascript` zero exit code, a correctly formed FCPXML candidate, nor a new `.fcpbundle` directory constitutes proof Final Cut is editing the intended library.

The selection verifier requires *all* of these at the moment of inspection:
1. An **existing** Jane job under `~/Documents/Rovor/fcp-jane-library-<job-id>`, with the current schema-2 atomic receipt marked `native_library_folder_created_app_selection_unverified` and an exact target `ROVOR-Jane-Isolated-fcp-jane-library-<job-id>.fcpbundle`. The bundle must be an actual directory, not a symlink. Prior failed attempts are not eligible.
2. Final Cut frontmost with no open sheet. A System Events Accessibility **read-only** query must find one matching *AX-selected sidebar outline row* for the uniquely named isolated library. Mere text/window-title occurrence cannot pass.
3. The **same Final Cut process PID** must hold an OS file descriptor for a native `CurrentVersion.flexolibrary` at the root of the exact target bundle or a shallow `CurrentVersion.fcpevent` within its event metadata structure. This is checked using a single PID-specific `lsof` call, never scanning unrelated libraries or media files. Unrelated paths are not printed.

Only then does the output say `selected_library_evidence_observed` with `native_library_app_selected_verified=true`. If native databases are opened only transiently, AX exposes rows differently, Accessibility is denied, Final Cut is not frontmost, or `lsof` is unavailable, it **fails closed** as `selection_unverified`—not as proof the project is absent. This intentionally favors false negatives over importing into another library.

## How a verified Mac executor may use it

For the **same existing job ID already used in the approved one-pass creator**, the following performs only read-only inspection:

```sh
python3 tools/fcp_jane_selected_library_probe.py --job-id <existing-successful-jane-id>
```

No executable shell script or arbitrary project path is accepted. Native GUI inspection requires a foreground logged-in macOS user session with granted System Events Accessibility. It does not request permissions automatically. Raw project titles, unrelated file paths, and raw osascript/lsof stderr are not returned. A positive response reports only the exact Jane job/target, fixed classification fields and booleans.

**Critical boundary:** A successful selection observation is *point-in-time evidence*. It is NOT proof a later FCPXML Open Document event will honor that destination. The known-unsafe `tools/fcp_native_auto_import.py --dispatch` route stays disabled; **do not** use this probe to bypass the separate authorization requirement for a replacement native import/edit/export adapter. Preserve `~/Movies/Untitled.fcpbundle` and all original Evan media unchanged.

## Test evidence and next gate

`tests/test_fcp_jane_selected_library_probe.py` exercises positive mocked proof, incorrect/missing project metadata, wrong PID, unrelated native DB paths, private stderr, symlink escapes, closed UI, and timeouts. The integrated worker CI executes tests without models or native GUI access. `.github/workflows/jane-selection-ax-compile.yml` compiles the AppleScript on Intel macOS with `osacompile` **without executing** it.

**Host acceptance pending:** Open Interpreter/MCP was previously verified for synthetic FCPXML inspection, but this chat has not connected to the user's local process executor. The Mac session must first observe an actual approved one-pass isolated library creation via PR #41, then run this read-only verifier on *that same* job ID, preserving scrubbed output/receipts. If any stage fails, analyze that one failure; never blindly retry or create new job IDs to hide it.
