# Jane — one-pass native Final Cut library job

**Owner:** ROVOR Jane specialist (coordinated by Walter). **Current state:** CLI adapter and CI complete; no successful native-library creation or FCP app selection has yet been observed on the actual Intel Mac. The old Oct 22 XML import entered a preexisting `~/Movies/Untitled.fcpbundle`; do not touch, delete, rename, repair, or use that library as Jane's destination.

## The one safe execution surface

`tools/fcp_jane_library_onepass.py` is the integration point for Jane's Mac executor. Unlike earlier ad-hoc scripts, it does not depend on the historical failed job and does not accept raw XML, arbitrary paths, App Store libraries, or client media.

An authorized local operator or approved local agent may call this from the **same PR checkout**, in a foreground GUI session with Final Cut installed:

```bash
python3 tools/fcp_jane_library_onepass.py --job-id jane-native-bootstrap-001 --create
```

The command calls only the trusted in-repo modules `fcp_jane_library_bootstrap.py` and `fcp_jane_library_failure_probe.py`; no package installs or model requests. **Run once per job ID.** The ID is stable and non-secret; re-running that ID returns its receipt without touching Final Cut, even if the first attempt failed or was interrupted. Do not use a different ID merely to bypass a failed one. The same CLI **without** `--create` is read-only dry-run and prepares nothing.

## One-shot state machine

| Gate | Action | Evidence / restriction |
| --- | --- | --- |
| 0: job identity | Validate bounded ID and local ROVOR root. Check any prior receipt | Existing job never replays; untrusted symlinks/outputs rejected |
| 1: native readiness | Read-only System Events check for FCP running, visible window, no existing sheets, File/New menu | No new directory or GUI action if unsafe; closed `Library` submenu is not mistaken for absent command |
| 2: isolate | Make one new private `fcp-jane-library-<job-id>` directory | Library basename embeds full unique job name; cannot confuse prior trials |
| 3: native library | Activate FCP with bounded wait; File → New → Library using lazy submenus; navigate Save panel to exact unique job folder | Only this explicit native UI action; rejects uncertain Save destination; no XML or media transfer |
| 4: evidence | Save atomic receipt per stage; capture only allowlisted stage/error/Apple errno; compare known Untitled folder mtime before/after | No private window/project titles; modified legacy mtime is unattributed, not declared unchanged |
| 5: verify result | Check expected `.fcpbundle` path; read-only post-UI snapshot | `library_created_app_selection_unverified` means only package creation was seen |
| 6: future FCP acceptance | **Not implemented/authorized yet**: verify exact library selected *inside* FCP, then import one synthetic 30s landscape timeline into that library and inspect actual project. Next, portrait and export | No XML import or project edit until native-library selection is independently proven; legacy `fcp_native_auto_import.py --dispatch` unconditionally disabled |

**Implementation:** `tools/fcp_jane_library_onepass.py`, `tools/fcp_jane_library_bootstrap.py`, `tools/fcp_jane_library_failure_probe.py`. Automated regression tests: `tests/test_fcp_jane_library_onepass.py`, `tests/test_fcp_jane_library_bootstrap.py`. macOS AppleScript compile gate: `.github/workflows/fcp-native-dtd-validation.yml`.

## Safety and reporting contract

A code commit, CI pass, or `osascript` return code is NOT a successful FCP edit. Confirm the actual native library directory; separately prove FCP's selected library, timeline duration/resolution/frame rate, export existence, decoded frame count and audio; then obtain creative approval. Never attribute an unrelated FCP library's modification solely to Jane based on timestamp. Never automatically retry failed UI interaction because a Save sheet may remain open. Do not close another person's libraries or dismiss unknown dialogs to clear the way. A worker may use `--create` only for an approved disposable native-library creation task, not as broad permission to operate user projects.

**Known host blocker:** Previous user Mac UI diagnostics (October 22) saw FCP RUNNING, two windows, zero sheets, File/New available, but Library submenu false while closed and FCP not frontmost at the later observation. The code now waits for activation and expands menus before checking; this fix is hypothesis-driven and only syntax/CI tested. The prior standalone attempt exit 1 had no detailed error. One-pass future receipts include the last recognized UI step and sanitized error class for efficient fault isolation.

## Current boundaries

The user's Mac does NOT automatically run code simply because a GitHub branch was updated. The existing Open Interpreter research worker has run read-only jobs, but no persistent callable native Jane worker has been verified. This onepass is a callable adapter for that next integration. It does not connect ChatGPT to the Mac, create a launchd agent, run while the computer is away, access social platforms, post content, use paid providers or render a video. These are later, separately gated capabilities.
