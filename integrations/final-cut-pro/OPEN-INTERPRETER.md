# Open Interpreter-first Final Cut Pro connection (Jane)

**Primary local executor: Open Interpreter.** Codex is an optional fallback client, not the ROVOR workforce's primary runtime. Walter coordinates Jane and other existing specialist roles, Open Interpreter supplies local agent sessions/MCP/tool permissions, and GitHub holds source/version/task evidence. None of this alone starts an always-on process or tunnels cloud ChatGPT to the Mac.

## Real Mac isolated library bootstrap FAILED — 2026-10-22 20:08 CDT

**New host evidence:** The user's subsequent Terminal paste shows one execution of `tools/fcp_jane_library_bootstrap.py --create` from commit `64d6e388abcab82326d66059dd0cef9f59a88475`, job `~/Documents/Rovor/fcp-jane-library-20261022-200846`. Terminal emitted `JANE LIBRARY ui_create_attempt_started` followed by `ui_create_failed_unverified`, AppleScript subprocess return code **1**. Receipt confirms `native_library_created=false`, `native_library_directory_observed=false`, `native_library_app_selected_verified=false`, `xml_import_attempted=false`, `model_turn_started=false`. This **does NOT** establish whether Accessibility permission was denied, File/New/Library was inaccessible, an existing sheet interfered, or the Save panel layout failed: legacy receipt only said `error_class=applescript_or_accessibility` and did not retain native error details.

**Important: DO NOT replay the prior --create command or retry XML import.** Do not delete or rename `Untitled.fcpbundle`. New code `tools/fcp_jane_library_failure_probe.py` is read-only: it accepts the exact previous `fcp-jane-library-20261022-200846` job, checks its receipt and expected native bundle, and asks System Events only for Final Cut's frontmost flag, count of windows/sheets, and existence of File/New/Library menu entries. It does not activate Final Cut, type, click, issue Open Document Apple events, read personal project titles/media, write files or retry creation. Unknown nested menu accessibility may be reported as false while menus are closed; **do not infer definitely missing action from a false result**. It returns only constrained booleans and safe native error code, if available. CI validates AppleScript syntax on Intel macOS and tests privacy + no replay.

**Improved future receipts:** `tools/fcp_jane_library_bootstrap.py` now retains an allowlisted `error_class` and Apple-native `apple_error_number`, replacing the prior uninformative class without recording sensitive raw stderr. This applies to future operations ONLY; it cannot reconstruct the uncaptured prior failure. An isolated library's filesystem presence alone never proves that Final Cut selected it, and XML import remains disabled.

## Wrong-library import PROVEN by native markers — 2026-10-22, 19:54 CDT

**Supersedes earlier speculation.** User's real Mac output from `tools/fcp_jane_import_audit.py` on existing job `~/Documents/Rovor/fcp-jane-auto-20261022-183007`:
- `status=read_only_targeted_marker_audit`
- `existing_untitled_library_scanned=true`
- `marker_presence.landscape.found=true`, evidence types **`directory_name` AND `native_database_byte_match`** for exact `ROVOR NATIVE IMPORT TEST landscape` identifier inside pre-existing `~/Movies/Untitled.fcpbundle`.
- `marker_presence.portrait.found=false`, consistent with `last_dispatched=landscape` and portrait withholding.
- `database_search_limit_hit=false`; 17 package entries inspected, five metadata files read (507,904 bytes). No media read, imported or copied; no unrelated names returned. No second import attempted.
- Intended disposable `ROVOR-Jane-Test.fcpbundle` was NOT created, and native timeline *properties* have not been verified. Existing `Untitled.fcpbundle` predates the run (October 7) and its mtime changed near the October 22 import. **Conclusion: strong dual native-marker proof the FCPXML landscape project landed in the wrong pre-existing library.** No longer state destination unknown, though the precise reason `import-options library location` was bypassed remains unverified.
- **Do not delete, rename, repair, or modify `Untitled` or its contents.** User has not authorized changing or cleaning up existing projects. Do not repeat the old import command.

**Production safety correction (2026-10-22):** The user-facing `tools/fcp_native_auto_import.py --dispatch` route is now **disabled unconditionally before preparation or any Apple event**, regardless of whether the prior `Untitled` library still exists. This prevents an accidental duplicate or misdirected import on another machine. The old Python function remains only as legacy test infrastructure and MUST NOT be wired into Jane's worker queue. CI explicitly verifies CLI refusal without disk or app side effects. The native library bootstrap is a separate creation-only gate: it has no XML import capability, requires exact Save dialog folder confirmation, and leaves `native_library_app_selected_verified=false` even when the new package appears. Do not re-enable native import until the app is proven to have the intended library selected.

**Root cause mitigation:** Apple documents that FCPXML's `library location` option can target a new library, but our live Mac test demonstrates that this is NOT a reliable isolation boundary on its own. Therefore any "open FCPXML" call without a proven isolated native destination is now considered unsafe. In `tools/fcp_native_auto_import.py` there is already a guard that forbids future import if pre-existing `~/Movies/Untitled.fcpbundle` exists. It remains in place.

**New implementation in PR #37:** `tools/fcp_jane_library_bootstrap.py` contains a separate native **File → New → Library** GUI automation using macOS System Events. It prepares a previously nonexistent, uniquely named folder `~/Documents/Rovor/fcp-jane-library-*`, and has an explicit `--create` path that opens the native Save dialog, navigates to the unique folder and creates a dedicated `ROVOR-Jane-Isolated.fcpbundle`. It does **not** import XML, edit, export, publish, or operate on `Untitled`. It records an atomic state receipt; even if its filesystem creation succeeds, it explicitly records `native_library_app_selected_verified=false`. No automatic import is enabled until **native library creation AND FCP app selection** are independently observed. All UI execution still requires actual Mac host verification. Local GUI app permission may be needed once. The repository's macOS CI compiles the AppleScript source and regression tests enforce no XML import, fail-closed behavior, and no repeat. Continue improving GUI-specific confirmation before enabling anything more.

**Product direction:** stop making the human manually create FCP libraries; Jane's orchestration should perform this within an isolated job. The macOS host bridge currently needs a one-time launcher due to this chat having no live local-execution connection. The system is not yet a continuously running ghost employee.

## Mac GUI diagnostic resolved, existing library changed during test — 2026-10-22

Real user Mac output from `tools/fcp_jane_ui_probe.py` (not a hypothetical):
- Job `~/Documents/Rovor/fcp-jane-auto-20261022-183007` was created **2026-10-22 23:30:07.652604 UTC**.
- `~/Movies/Untitled.fcpbundle` **predates** the test: creation **2026-10-07 19:11:13.840812 UTC**. Its modification timestamp is **2026-10-22 23:30:16.813371 UTC**, about **9.2 seconds after the Jane job directory was created**. This time correlation is NOT proof Jane imported into it; Final Cut or another process may have autosaved it.
- Final Cut is running. System Events read-only GUI inspection succeeded: **2 windows, 0 sheets**, no windows categorized as import dialog, library picker or error dialog. This excludes a *currently visible categorized dialog at observation time*, not all possible app-level errors.
- Intended new `ROVOR-Jane-Test.fcpbundle` **still does not exist**; portrait not dispatched; native timeline still NOT verified. Do not claim that source media were modified, nor that other existing library metadata were untouched.

**New isolation protection:** `tools/fcp_native_auto_import.py` now refuses further native import dispatch while the pre-existing `~/Movies/Untitled.fcpbundle` is present. This is a deliberate fail-closed guard, NOT a request for the user to delete/move the existing library. The adapter also marks any app-driven writes to existing libraries as `not_assessed`; no longer asserts they are untouched. This protects the original user's editing work against silent repeat imports.

**Next single targeted read-only investigation:** `tools/fcp_jane_import_audit.py --job ~/Documents/Rovor/fcp-jane-auto-20261022-183007`. It scans ONLY known native metadata/database files and directory names in the existing `Untitled.fcpbundle`, within fixed byte/entry/depth budgets, for exact identifiers `ROVOR NATIVE IMPORT TEST landscape` and `ROVOR NATIVE IMPORT TEST portrait`. It deliberately excludes Original/Optimized/Proxy Media, render files, unrelated project data, network, app commands, and exports. Only yes/no marker-presence flags leave the Mac; no unrelated project names or contents are printed. **A positive match indicates the test's marker exists in the wrong library, but a negative result is inconclusive** because Final Cut metadata may be encoded or stored elsewhere. It cannot verify project properties or timeline.

After this evidence, plan native UI library creation using a new isolated disposable target and verified Accessibility capabilities, then import only after the native library exists, and require app-level project verification. Do NOT replay the old `osascript open` sequence or ask the user to create a library manually.

## Native import gate: Final Cut running; UNATTRIBUTED Untitled library; UI diagnosis next (2026-10-22)

The user's **latest** real Mac read-only `tools/fcp_jane_native_probe.py` output from exact job `~/Documents/Rovor/fcp-jane-auto-20261022-183007` shows:
- `original_job_status=native_library_not_observed`, `apple_event_returned_zero=true`, `last_dispatched=landscape`, `portrait_dispatched=false`.
- Both XML files parse and retain their intended **30-second, 60fps, empty** timelines and exact destination URL `file:///Users/amarhavic/Documents/Rovor/fcp-jane-auto-20261022-183007/ROVOR-Jane-Test.fcpbundle`.
- Final Cut Pro app installed and **its process was observed running** on the host; `osascript_process_present=false` by the later read-only snapshot.
- **The expected ROVOR test library is not present**, and `native_timeline_verified=false`.
- `~/Movies/Untitled.fcpbundle` is present but **may predate the attempt or have an entirely unrelated origin**. Merely seeing it is NOT evidence of imported projects, app success, or an alternate import destination.

**Next tool** `tools/fcp_jane_ui_probe.py` is a safe diagnostic to narrow this root cause without launching Final Cut, clicking buttons, reading actual media or opening libraries. It reads only metadata for the known `~/Movies/Untitled.fcpbundle` (creation/mtime versus job start) and optionally uses *read-only* macOS System Events Accessibility scripting to categorize Final Cut's window titles and count blocking sheets. Title strings are redacted; not logged to GitHub. If Accessibility permission is unavailable, it returns `accessibility_or_automation_denied` rather than implying app success. A native macOS `osacompile` job validates the AppleScript syntax without execution; unit tests cover permission errors, blocked GUI, missing app and metadata-only privacy. **DO NOT REPEAT** the existing `--dispatch` attempt or ask user to create/import FCP projects manually.

Native Apple docs: [Send FCPXML via Open Document](https://developer.apple.com/documentation/professional-video-applications/sending-data-programmatically-to-final-cut-pro), [library location import-option example](https://developer.apple.com/documentation/professional-video-applications/describing-final-cut-pro-items-in-fcpxml), [read-only System Events inspection](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AutomatetheUserInterface.html).

## Real Mac native auto-import result: NO LIBRARY OBSERVED — 2026-10-22

**Update from the user's second, complete Terminal paste (the earlier log was truncated):** first `--dispatch` at 2026-10-22 18:30:07 CDT, job `~/Documents/Rovor/fcp-jane-auto-20261022-183007`, **COMPLETED** with status `native_library_not_observed`. `osascript` returned exit code **0**, so script's `apple_event_sent=true`, but **the expected library package does not exist**, `library_creation_observed=false`, `native_timeline_verified=false`, `last_dispatched=landscape`, and `portrait` was NOT dispatched. The read-only `fcp_jane_status.py` independently observed the same result: `native_library_exists=false`, `xml_candidates_present=true`. The dispatch generated 30s DTD-valid landscape and portrait XML hashes, did not edit original media, and did not run a model. No native project creation has been verified.

**Critical next action: DO NOT rerun original `--dispatch`.** A successful AppleScript return does not prove Final Cut accepted/imported XML. Apple documents `import-options` `library location` and Open Document Apple event; this is not enough to establish actual behavior on the user's specific Mac. We need to check whether Final Cut was active, whether another default library appeared, whether the XML target matches exactly, and whether Final Cut remains blocked on a dialog or Documents-folder permission. The last two are *possibilities*, not proven causes.

**Code action committed:** `tools/fcp_jane_native_probe.py` reads only that exact existing disposable job and selected read-only process names and library file-system metadata in bounded scopes; no `osascript`, app launch, UI controls, network or secondary import. Tests: `tests/test_fcp_jane_native_probe.py`, in FCP smoke CI. This preserves both cases: first import returned success, yet no output; false positive "project created" remains explicitly impossible. The PR's later native adapter has per-step crash-safe receipt checkpoints but was not the version invoked in the already-completed Mac run.

## Historical note: earlier Mac paste ended before result — superseded by verified failure above

The user's latest full Terminal paste ends after invoking **exactly once** the original `tools/fcp_native_auto_import.py` at commit `0aee0cd30e4c4715611f54917943d0317cbbebab` with `--dispatch`, `--candidates ~/Documents/Rovor/fcp-native-import-20261022-172131` and a newly time-stamped `--output ~/Documents/Rovor/fcp-jane-auto-<timestamp>`. There was **no subsequent stdout/stderr or terminal prompt** in the paste. It does NOT establish success, failure, an active process, actual native FCP import, or a new library; the process may have been waiting on AppleScript or may simply have been copied before completion.

**Do NOT ask the user to run the import a second time.** Inspect the existing private `native-auto-import-receipt.json` and `.fcpbundle` presence first using `tools/fcp_jane_status.py` (read-only); it selects the most recent `fcp-jane-auto-*` folder, never launches/edits/retries Final Cut, and never claims native timeline verification from a directory alone. `no_receipt_yet_preparing_or_interrupted` means unknown, not failed.

**Observed bug in original script and fix:** The command produced no incremental visible output and wrote its completion receipt only once `osascript` returned; an Automation permission dialog or blocked app could appear hung. New GitHub code records crash-safe atomic checkpoints BEFORE subprocess dispatch (`sending_landscape_apple_event`, etc.), flushes progress to Terminal, separates `apple_event_dispatch_attempted` from actual `apple_event_sent`, and preserves a final receipt on subprocess denial or timeout. Regression tests include an explicitly blocked Apple event and stale receipt temporary file; CI passed. These improvements apply to **future** invocations; they cannot retroactively instrument the already running `0aee...` script. A separate status inspector can read its prior result without dispatching again.

No manual Final Cut library creation or XML menu walkthrough is appropriate; those operations belong to the Jane automation. Actual native app and timeline verification still await Mac evidence.

## Jane's NEW automatic native Final Cut integration (no manual library/XML import)

**Why:** The operator explicitly rejected the previous manual File → New → Library and File → Import → XML directions. Those defeat the ghost-employee design; do not direct the operator through them again as the default workflow. Native Final Cut operation should be the **automation's job**, not the user's job.

**Official Apple mechanism:** [Send FCPXML through the Open Document Apple event](https://developer.apple.com/documentation/professional-video_applications/sending_data_programmatically_to_final_cut_pro) and use the `<import-options><option key="library location" value="file:///.../ROVOR-Jane-Test.fcpbundle"/></import-options>` field. Apple states a nonexistent target location can cause Final Cut to create a library; this avoids the manual chooser. Do not confuse this with the `location` attribute on the `library` element, which is ignored for importing. Apple's reference: [import-options](https://developer.apple.com/documentation/professional-video-applications/import-options).

**New native adapter:** `tools/fcp_native_auto_import.py` (same PR #37) operates only on the *existing* already DTD-validated Mac candidate folder `~/Documents/Rovor/fcp-native-import-20261022-172131`. It checks SHA-256 against the candidate receipt, 30s geometry and 60fps timing, no media references, then creates a **new disposable** output folder and injects `import-options` into COPIES of the two FCPXML files. The copies must pass the actual installed 1.13 DTD before any app event. It sends `osascript` to Final Cut with the XML path as a separate argument, waits to observe a new `.fcpbundle` directory, and dispatches portrait only after landscape's package path appears. No File→Import or manual library creation. Errors, no target and timeouts fail closed; no retries/duplicate output paths. Private JSON receipt distinguishes `apple_events_sent_timeline_unverified` from **actual** timeline verification, which is still pending. No model inference. No original media writes. Users may need to grant the one-time Apple/macOS Automation permission; a blocking modal should be reported, NOT clicked blindly.

**Actual app native test:** pending on the user's Mac. GitHub tests with mocked AppleScript do NOT prove GUI/native package creation. The proper next step for the user is a *single* bounded `--dispatch` call on the Mac, **not** a manual FCP library operation. It must run in the interactive logged-in Mac user session with macOS GUI access. If it fails, inspect the private receipt and exact error, adapt without asking the user to do Jane's editing job. Once verified, adapt this Python entrypoint into the `finalcut.native_import_demo` Jane job queue; later implement export QA and editable timeline operations. Never enable arbitrary production-library access or publishing based only on a synthetic test.

## Mac proof: Native import candidate PREPARED, native FCP import NOT YET TESTED — 2026-10-22

The operator executed the corrected `tools/fcp_native_import_candidate.py` (commit `3c8da2c4f72eaaed571105df7ba487812ad2ddba`) on their Intel Mac with the existing, confirmed stage. **Actual Mac stdout passed:**

- status `candidate_prepared_native_not_imported`;
- private output `~/Documents/Rovor/fcp-native-import-20261022-172131`;
- Apple DTD checksum `5afbc7ca1001bbc2190fb3b21d4d440ce061d94f5a5f583074e982b4745cd04d` (same installed DTD as prior passing MCP smoke and verified Intel CI);
- 30s at 60fps, *no media*; `native_final_cut_import_verified=false`, `native_final_cut_operated=false`, `model_turn_started=false`, `media_modified=false`;
- landscape `ROVOR-NATIVE-IMPORT-landscape-30s-60fps.fcpxml` SHA-256 `d64e2ae8f19909996fa85ed2e439e7803407bd266f5e6cd35cbe187fc5532c72`;
- portrait `ROVOR-NATIVE-IMPORT-portrait-30s-60fps.fcpxml` SHA-256 `46b743638de34254a8c57bb647709c1a82a477ecc7ed0984053e2acc3e001833`.

**Do NOT rerun any setup, MCP registration, MCP connection, or XML generator on this Mac.** Both original candidate files now exist. The next gate is a **user-authorized native Final Cut import into a brand new empty, throwaway library**. Apple documents `File > Import > XML` ([support](https://support.apple.com/en-is/guide/final-cut-pro/verdbd66ae/mac)) and also documents `Open Document` Apple event delivery ([developer](https://developer.apple.com/documentation/professional-video-applications/sending-data-programmatically-to-final-cut-pro)). For now, choose the manual GUI import into a known disposable library; do not silently select an existing library. Document actual FCP UI, project presence, timeline duration, frame rate/resolution and any warnings. Successful DTD validation is **NOT** proof of native import. These are blank test timelines, not media/video deliverables.

## Mac proof: Open Interpreter MCP CONNECTED — 2026-10-22

**Do not repeat setup, wheel repair, FCP DTD validation, stage generation, CLI registration, or app-server connection tests on this Mac. These gates passed.** The owner supplied the final Mac stdout from `tools/fcp_interpreter_appserver_smoke.py`, using the existing disposable `~/Documents/Rovor/fcp-interpreter-stage-20261022-160459`. The complete end-to-end, **locally executed** Open Interpreter app-server → third-party FCP MCP test returned:

- `status=passed_interpreter_appserver_mcp_tool_call`, `open_interpreter_connected=true`, `server=fcpxml`;
- **actual tool invocations** `mcpServer/tool/call` of `inspect` succeeded on synthetic `1920x1080 @ 60fps` and `1080x1920 @ 60fps`;
- `outside_root_refused=true` on synthetic sentinel outside `FCP_PROJECTS_DIRS`;
- response digest landscape `917fa862ee2bf2da8fcfa882caf2fa4a322d239ae2e8f69db0a07799148ceb05`; portrait `c27ce12aa10bb336dd916c5f59520f1c0da8e787b86820af1a58a5b874ee1f3b`;
- `native_final_cut_operated=false`, `model_turn_started=false`, `media_modified=false`.

**Established:** Open Interpreter v0.0.56 talks to pinned FCP MCP v0.27.2 on the user's Intel Mac through its own app-server, with a real read-only tool response and denied unsafe test path. This is more than just registering an MCP server; it is **host-verified client MCP communication**. It does NOT show control of the native Final Cut Pro application, FCPXML GUI import, interactive editing, export, background service or agent execution of a model-originated tool call.

**Current actionable next gate:** native Final Cut Pro integration with a **brand-new, isolated, empty test library** and a DTD-validated synthetic FCPXML import candidate. Do not open any existing media, projects, libraries or original ROVOR recordings; do not enable edit/generate/publish tools yet. For the initial import gate, use a controlled operator-approved GUI import into the new test library; separately observe native app effects and save a result record. Do not claim native editing from FCPXML inspection alone.

**Actual Mac native-candidate attempt failed closed (2026-10-22):** the user's Terminal invocation of `tools/fcp_native_import_candidate.py --stage ~/Documents/Rovor/fcp-interpreter-stage-20261022-160459 --output ~/Documents/Rovor/fcp-native-import-<timestamp>` returned `ValueError: Installed Apple DTD rejected 30s landscape FCPXML`. It did **not** create an importable output or open/edit Final Cut. The original script discarded `xmllint` stderr and exit code, so the precise local failure cause is unknown; do not claim malformed XML.

**Independent proof narrowing the failure:** a real Intel macOS GitHub runner validated the exact generator's output (landscape AND portrait) using the public Apple FCPXML 1.13 DTD mirror. Its **SHA-256 was exactly** `5afbc7ca1001bbc2190fb3b21d4d440ce061d94f5a5f583074e982b4745cd04d`, matching the user's installed Final Cut DTD previously captured in their direct MCP smoke receipt. [GitHub real DTD run 39861918217](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39861918217) passed. Therefore a structural schema error is not demonstrated. Improved local diagnostics now show bounded `xmllint` stderr, status and no-output failure; an additional real full prepare test with Python 3.9 and Python 3.11 checks the full path. Continue from this point; do NOT reset known working MCP plumbing. **Repair committed:** the native candidate generator now copies the *installed* DTD into a private temporary folder before running `xmllint`, exactly mirroring the earlier successful Mac direct-MCP smoke, rather than validating against a path inside the `.app` bundle. On failure it prints bounded actual `xmllint` stderr and numeric exit status while leaving no import candidate. Real full-process DTD validation on Intel macOS with matching DTD hash and Python **3.9** and **3.11** passed [matrix run 39862828263](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39862828263); **user Mac remains to be rechecked**. The cause of the previous Mac rejection is not conclusively identified; do not call it solved until the actual Mac validation passes.

**Next gate prepared in GitHub and regression-tested, NOT executed on user's Mac:** `tools/fcp_native_import_candidate.py` takes the existing verified `--stage` root and a completely NEW `--output` directory. It derives two media-free, 30-second 60fps FCPXML test timelines from the Mac-verified 1.13 fixture format; checks project geometry, exact frame durations, no asset/file references; requires `xmllint --nonet --dtdvalid` against the owner's INSTALLED Apple Final Cut 1.13 DTD. It fails closed if there is no real DTD or output already exists. It writes an owner-only candidate directory, README and `candidate_prepared_native_not_imported` receipt; **it does not run Final Cut, import anything, request AI, or read/modify existing media**. The blank test timelines are diagnostic imports only, *not* deliverable animations or a video. CI validates its parser/duration/geometry/failure behavior; the user's Mac must separately validate with the installed DTD. Later, the operator may approve File > Import > XML into a brand-new empty library. Apple's [official import guide](https://support.apple.com/en-is/guide/final-cut-pro/verdbd66ae/mac) documents this supported workflow; Apple's [Open Document Apple event guide](https://developer.apple.com/documentation/professional-video-applications/sending-data-programmatically-to-final-cut-pro) is a possible future automation route, but it is **not yet enabled or tested**.

**Related independently executed Intel CI:** [run 39858034351](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39858034351) passed equivalent app-server real MCP calls without inference. Source: `tools/fcp_interpreter_appserver_smoke.py`.

> **Legacy procedures below are retained as history of earlier setup gates.** "Not verified" statements about the local MCP connection in these historical sections were accurate *at that earlier stage* but are superseded by the Mac proof above. Do not direct anyone to rerun those gates unless a new Mac, changed installed versions or regression failure requires it.

## Sources and supported commands (reviewed 2026-10-22)

- [Open Interpreter MCP](https://github.com/openinterpreter/openinterpreter/blob/main/docs/mcp.md): project or user configurations under [mcp_servers.*], CLI commands interpreter mcp list/get/add/remove, in-TUI /mcp and /mcp verbose. Supports enabled_tools, default_tools_approval_mode, enabled and required. A registered server is NOT a connected server.
- [Configuration](https://github.com/openinterpreter/openinterpreter/blob/main/docs/config.md): trusted project settings in .openinterpreter/config.toml, a DIFFERENT file from .codex/config.toml; /debug-config shows loaded layers.
- [CLI reference](https://github.com/openinterpreter/openinterpreter/blob/main/docs/cli-reference.md): interpreter foreground, interpreter exec for one-off noninteractive tasks, interpreter mcp, interpreter mcp-server, and interactive sessions. Do not assume local command works before running it.
- [Daemon documentation](https://www.openinterpreter.com/docs/terminal/daemon): normal foreground operation does not require a daemon; shared background daemon is optional. But the user's Intel Mac v0.0.56 had a persistent package/platform mismatch on daemon start. Foreground agent/skills/MCP still need separate proof.
- [Third-party FCPXML MCP](https://github.com/DareDev256/fcp-mcp-server): source-inspected v0.27.2 and now **direct-MCP host-verified** on the user's Intel Mac against synthetic timelines, but **not yet Open Interpreter client-verified or native Final Cut GUI-verified**. FCP_PROJECTS_DIRS restricts reads through the server API; legacy FCP_PROJECTS_DIR only controls listing. These variables must BOTH point to a disposable root; an MCP tool allowlist is not a full OS sandbox.

**Repository state:** this PR adds an explicitly disabled FCPXML entry to .openinterpreter/config.toml (primary), beside a separately disabled .codex/config.toml entry (fallback). Neither file authorizes private media reads or installs the server.

## Observed first direct MCP smoke attempt — 2026-10-22

Amar ran the pinned `tools/fcp_host_smoke.py` on the Intel Mac. The installed Final Cut Pro FCPXML 1.13 DTD was found and both 60 fps synthetic fixtures passed `xmllint` before `uvx` was started. The attempted MCP handshake **FAILED** at stage `verify_mcp`: `MCP exited before replying`. No direct MCP tool reply, Interpreter MCP registration/handshake, or native Final Cut control was verified. The relevant stdout report stores `status=failed`, `native_final_cut_operated=false`, and `interpreter_mcp_client_verified=false`.

**2026-10-22 root cause confirmed from the Mac's private stderr:** `uvx` resolved `cryptography==50.0.2` and attempted to build its source distribution, but `openssl-sys` could not locate development OpenSSL. `cryptography` 49.0.0 removed Intel macOS wheels, so this is a dependency compatibility issue, **not** a Final Cut app failure or an MCP protocol failure. `cryptography==46.0.5` still ships a CPython 3.11 `macosx_10_9_universal2` wheel. The FCP pilot now adds `--with cryptography==46.0.5` and `--no-build` to the `uvx` command in `tools/fcp_host_smoke.py`, `.openinterpreter/config.toml` (primary) and `.codex/config.toml` (fallback). The `--no-build` flag fails closed rather than compiling unknown source packages. Sources: [cryptography changelog](https://cryptography.io/en/50.0.2/changelog/), [cryptography 46.0.5 wheels](https://pypi.org/project/cryptography/46.0.5/) and [uv tool guide](https://docs.astral.sh/uv/concepts/tools/).

A subsequent diagnostic improvement on this branch saves the **pre-cleanup child exit code**, retained stderr length and SHA-256 in `receipt.json` without printing raw stderr. A dedicated `macos-15-intel` GitHub Actions [run 39852393294](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39852393294) **PASSED** on a genuine Intel x86_64 GitHub runner (2026-10-22). It installed wheels without source compilation, started MCP server v0.27.2, inspected synthetic 1080p60 landscape/portrait timelines, and refused a synthetic outside-root path. The CI result deliberately reports `final_cut_operated=false` and `interpreter_connected=false`. **The user's own Mac subsequently passed the patched tester (see local direct-MCP proof below).** The GitHub-only diagnostic unit test suite passed **9/9** on commit `d9ba5f7`; that is a synthetic transport test, **not** a Mac MCP pass. Do not claim that Final Cut has been connected until an actual inspect response and rejected out-of-root read have been captured.

## Proven on user's Intel Mac — 2026-10-22 (local direct MCP)

The operator executed the **patched** pinned smoke script and provided the full stdout receipt. Latest PRIVATE Mac evidence folder: `~/Documents/Rovor/fcp-mcp-check-20261022-155558`.

- Status: `passed_direct_mcp`, stage `complete`; MCP server name `fcp-mcp-server`, version `0.27.2`
- Installed Apple FCPXML 1.13 DTD copied and synthetic fixtures validated locally
- Real MCP initialize, tools/list and `inspect:analyze_timeline` succeeded for `1920x1080 @ 60fps` landscape and `1080x1920 @ 60fps` portrait
- An explicit synthetic sentinel outside `FCP_PROJECTS_DIRS` was refused with `Validation error: File path escapes the allowed roots`
- `native_final_cut_operated=false` and `interpreter_mcp_client_verified=false`; both are STILL pending

**Next stage is prepared in code, NOT executed on the user's Mac:** `tools/fcp_interpreter_stage.py` validates the prior passing receipt and its two real fixture files, then generates a NEW private one-use Open Interpreter project. Only `inspect` is enabled; the sandbox/approval mode is read-only/on-request and MCP is marked required. The new root has its own synthetic files and outside-root sentinel; it contains no private media or provider settings. No model process or Final Cut app is invoked during staging.

Use a fresh new output path and the actual proof directory:

~~~sh
python3 tools/fcp_interpreter_stage.py \
  --evidence "$HOME/Documents/Rovor/fcp-mcp-check-20261022-155558" \
  --output "$HOME/Documents/Rovor/fcp-interpreter-stage-$(date +%Y%m%d-%H%M%S)"
~~~

The stage script prints its PRIVATE project path, but **do not run bare `interpreter mcp list`** in an untrusted stage; that was the observed failure. Run `tools/fcp_interpreter_registration.py --stage <existing-stage-root>` to prove the ephemeral CLI registration and get the generated wrapper. Invoking the wrapper's `mcp list` or `mcp get` still verifies **registration only**, NOT an MCP handshake. Operator can then opt into a single foreground `interpreter` session, inspect `/debug-config` and `/mcp`, approve one real `inspect` call for each synthetic file and a rejected outside-root sentinel. Preserve local reports as private evidence. The stage does not invoke a model or authorize spending automatically.

## Observed failure: project-local MCP config was ignored (2026-10-22)

The user's first staged project completed successfully, then **bare** `interpreter mcp list` printed `No MCP servers configured yet` and `interpreter mcp get fcpxml` printed `No MCP server named 'fcpxml' found`. No model was invoked. This is a **failed Open Interpreter registration**, NOT failure of the already confirmed direct FCP MCP transport.

**Actual root cause in pinned Open Interpreter v0.0.56's loader:** project-local `.openinterpreter/config.toml` is loaded as a *disabled* layer for an untrusted project. This one-use folder is outside an explicitly trusted project. The CLI source `codex-rs/config/src/loader/mod.rs` says project-local configs are disabled if untrusted; `codex-rs/cli/src/mcp_cmd.rs` obtains the effective config, not all disabled layers. The old script wrongly assumed the directory alone was sufficient.

**Corrected no-global-change gate:** `tools/fcp_interpreter_registration.py --stage <existing-stage-root>` validates the previous stage, supplies the exact restricted FCP MCP entry using Open Interpreter's global per-run `-c` TOML inline-table override, and checks the actual `interpreter mcp list --json` response. It refuses empty/mismatched entries, wrong paths, changed stage files, disabled servers and failed CLI responses. It creates an owner-only `run-interpreter-fcp.sh` ONLY after successful registration. This neither writes `~/.openinterpreter/config.toml` nor adds any permanent trust or starts a model. The wrapper must be used for subsequent TUI registration, because bare `interpreter` still won't consume the project-local layer when untrusted.

**Actual Open Interpreter v0.0.56 integration CI PASSED:** [Intel macOS run 39855908281](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39855908281) downloaded the pinned release, loaded the ephemeral `-c` MCP entry while the project was untrusted, and exercised the complete synthetic stage → `fcp_interpreter_registration.verify_cli()` path, including creation of a private wrapper. Zero model inference, no MCP server transport, no native Final Cut. The same separate diagnostic/test suite passed **25/25** offline tests. **Mac local registration is still pending**; do not mark Jane connected from CI alone.

**Confirmed on user's Intel Mac:** `tools/fcp_interpreter_registration.py --stage ~/Documents/Rovor/fcp-interpreter-stage-20261022-160459` returned `passed_interpreter_registration_only`, MCP server `fcpxml`, tool allowlist `["inspect"]`, private launcher `.../project/run-interpreter-fcp.sh`, and `cli_registration_sha256=0b1b29338af9e74131b4142a56d311d7cd80355b0401651d7f9e412b711ebe2d`. No model or MCP server launched. This is **real Mac CLI registration proof** and should not be re-run unnecessarily.

**CI proof of Open Interpreter MCP client (not user's Mac yet):** `tools/fcp_interpreter_appserver_smoke.py` calls the actual `interpreter app-server` JSON-RPC (`initialize`, ephemeral `thread/start`, `mcpServerStatus/list`, `mcpServer/tool/call`) WITHOUT `turn/start` or any model. It calls the pinned real `fcp-mcp-server==0.27.2` `inspect` tool against two 60fps synthetic timelines and verifies the outside-root sentinel is rejected. [Intel macOS CI run 39858034351](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39858034351) passed, with `open_interpreter_connected=true`, `model_turn_started=false` and `native_final_cut_operated=false`. This is a genuine MCP tool call **through Open Interpreter**, not direct MCP masquerading as a client. The user's Mac still needs this single app-server proof; do not claim Jane's host-level editing or FCP GUI access.

**Do not mistake registration for a handshake:** `mcp list` reads effective configuration but does not initialize the third-party server. Only an actual Interpreter-enabled MCP tool response proves the subsequent gate. Running the wrapper in foreground and invoking a model/tool remains explicitly opt-in. The registered tool list is restricted to `inspect`, with individual approval prompts, on a new synthetic folder. This is application-level scoping, not proof of OS-level filesystem confinement.

## First read-only host checks (normal macOS Terminal)

Use a clean local checkout/worktree containing PR #37; preserve changes in the existing interpreter pilot and do not update dirty branches blindly.

~~~sh
cd "$HOME/Documents/Rovor/rovor-fcp-pilot" || exit 1
git status --short
sh integrations/final-cut-pro/preflight-mac.sh
interpreter --version
interpreter mcp list
interpreter mcp get fcpxml
~~~

These are inspections, not proof of an MCP handshake. The fcpxml MCP must still be disabled. If the CLI does not recognize a command, capture interpreter --help/version, and report the mismatch instead of trying guessed flags.

Start foreground:

~~~sh
interpreter
~~~

INSIDE its TUI, inspect /debug-config, /mcp and /agent. Verify project config, Walter/Jane roles and that FCPXML remains disabled. If daemon mismatch warning appears, it does not alone prove foreground execution is broken or operational. Ask ONE small read-only question with the configured provider; avoid spawning all specialists on a low quota. Keep model/billing unchanged.

## Manual opt-in MCP connection (requires Mac operator approval)

1. Review upstream code and the pinned external package before download or installation; verify installed versions of Python/uvx/FCP.
2. Create a NEW EMPTY directory such as ~/Movies/ROVOR-FCP-Sandbox with only synthetic demo media/XML. Do not reuse a personal folder or import original Evan assets, client files or 4:23 narration.
3. Edit ONLY the local copy of .openinterpreter/config.toml: replace BOTH intentionally invalid FCP path placeholders with the SAME absolute demo folder; retain FCP_PROJECTS_DIRS, FCP_MCP_AUTOPUSH=0, required=false and the inspect/diagnose/view tool allowlist. After explicit authorization, set enabled=true.
4. Restart local Open Interpreter foreground; use interpreter mcp list and /mcp to confirm the actual registered tool list/handshake. Call a real read-only inspect on the synthetic XML. Try a safe known XML path outside the root; it MUST be rejected. Do NOT search a private disk for an outside file. Capture versions, observed result, hashes and errors.
5. Only after review, approve one generated/edited disposable XML copy; inspect it and separately authorize importing into a new test Final Cut library. Check real video exports using normal playback/ffprobe when available. Never modify approved projects.
6. Rollback: stop the agent, set enabled=false, restart; leave original libraries intact. Never commit local paths/provider credentials/permissions to GitHub.

Codex can be used as a fallback for the SAME scoped read-only experiment only if Interpreter is demonstrably blocked. Mark results Codex-only rather than claiming Open Interpreter works. Do not abandon Open Interpreter.

## Turning Jane into an actual ghost employee

The ghost workforce has demonstrated a separate **read-only Jane research** queue job on the user's Mac (one executed, one succeeded, with a receipt and source work). That research job does NOT demonstrate Final Cut MCP use, native editing, GUI control, email/social publishing, or continuous unattended employment. The registry has no enabled Final Cut edit adapter, and all durable local execution must remain approval-gated.

After a verified foreground connection, add a separately claimed **Interpreter research adapter** that runs ONE authorized read-only task via the documented interpreter exec interface and returns a file/receipt with sources, exact tool/model/version, time/budget, input and output hashes. Validate cancellation, crash restart, duplicate submissions, unattended approval behavior and quota exhaustion before connecting to a scheduler. Next add a supervised FCP read/analysis adapter; later add reversible timeline edits with explicit approvals and normal-speed video QA. Keep software install, personal file access, social posting, emails, spending and original project mutation approval-gated.

A role configuration + MCP declaration is not a scheduled worker, and the present GitHub-only work does NOT imply the cloud chat can operate the Mac or that any local FCP work has run.

## First research request to Walter after host verification

"Read current ROVOR AGENTS.md/WORK.md and task queue, then Jane's RESEARCH-PACKET.md. Jane should study the latest official Final Cut Pro documentation and how to assemble professional YouTube/Reels from real motion, original narration, music and SFX. Mike should inventory installed FCP, uvx, FFmpeg and the real available MCP tools. Claim a non-overlapping bounded task, save sources and actual test receipts, and stop if provider/runtime/permission evidence is missing. Do not install software, read private libraries, generate paid inference, send email or post without authorization."
