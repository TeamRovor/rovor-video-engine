# Private MP3 job transport — implemented, Moho renderer pending

2026-10-19 America/Chicago. Inspected main 996f8948, open PRs #2/#4/#5/#7/#12, Issue #6 comments and existing read-queue runner code. Preserve those branches and Evan artwork. This change adds transport only; it does not substitute the V3 sprite engine for Moho.

## Verified boundaries

The native command-line compiler/render path is independently verified against a disposable tutorial archive. An early MCP preflight timed out; the existing live bridge later answered after its Mac viewport wake sequence. That wake flow is interactive and is not part of the headless compiler or CLI renderer. The V4 Evan status tool explicitly says it is not Moho. No approved Evan rig mapping or MP3-to-Moho production adapter is verified.

The existing `.github/scripts/rovor_moho_read_queue.py` accepts only two read methods. Its workflow uses the interactive viewport-wake bridge and is read-only; it is separate from the verified CLI render path. Keep it out of the headless production job path. PR #7 owns Windows reliability; #4/#5 own art/acting and acoustic alignment. No experimental branches are merged here.

## Smallest usable transport

`tools/render_jobs.py` uses a private local spool with four commands. Use an absolute spool path; FFprobe must be on PATH for intake and output verification.

```sh
python3 tools/render_jobs.py --root /private/job-spool submit /private/incoming/narration.mp3
python3 tools/render_jobs.py --root /private/job-spool status JOB_ID
python3 tools/render_jobs.py --root /private/job-spool run JOB_ID
python3 tools/render_jobs.py --root /private/job-spool artifact JOB_ID /private/returned/render.mp4
```

Without an administrator adapter, `run` changes queued to blocked; no Moho mutation occurs. When verified, supply `run JOB_ID --adapter /private/config/adapter.json`. That configuration is a host-owned JSON argv array, never uploaded job content. The trusted adapter receives the job directory as its last argument. No arbitrary URL fetch, incoming shell command, automatic paid service or render retry is supported.

State: queued → running → review_required or failed; missing adapter → blocked. Jobs cannot be replayed. New attempts get a new ID, preserving previous output. One worker lock serializes all jobs; if killed, inspect the process/Moho state before manually removing the stale lock. Never automatically retry an uncertain native write. Initial limits: 25 MiB, 60 seconds input, 30 minute adapter timeout, 512 MiB output. No truncation, audio stretching or automatic portrait second render. Under 30 seconds is explicitly diagnostic. There is no dedup/cache claim; integrate existing content-hash stage caches in the adapter.

## Remaining headless integration steps

1. The native Moho Pro 14 command-line renderer is verified on this Mac with a disposable archive (Moho -r project.moho ...). It needs the Pro command-line renderer entitlement and working source-asset paths. The current production job workflow has not been installed as a runner-backed compiler adapter. Establish the worker as a trusted service under the Mac account that owns Moho licensing and private project assets. Keep its spool and credentials private; do not expose Moho's temporary IPC directory to the network.
2. Obtain the approved native Evan Moho archive and all linked art assets from their owner. Use tools/moho_compile.py inspect to read actual layer UUIDs, bone names and mouth switch children. Confirm archive hash/schema and dependencies. Current proven tutorial rig has generic B1…B11 bones, not Evan. No source artwork is rebuilt by the compiler.
3. A trusted adapter must decode the original MP3 without changing it, create a source-derived 16kHz mono PCM16 WAV, preserve or review its English transcript, forced-align actual spoken phones, run tools/speech_plan_gate.py with the exact WAV, and provide an explicit map to existing switch children. It must compile into a disposable copy, render with the native CLI at 1920×1080/60fps, mux the unchanged narration, and verify duration, stream metadata, source provenance and hashes before marking an artifact ready. The current native compiler and transport are separate tested components; this adapter is still unimplemented.
4. Implement an authenticated upload/action connector that accepts a ChatGPT attachment, transfers MP3 bytes privately to the Mac worker, invokes only the fixed adapter, polls the job state, and returns the verified MP4 as an attachment. Repository access alone does not provide those bytes or a Mac shell. Do not place audio or credentials in public Actions artifacts, logs, or Git history. Until this connector exists, user MP3 intake remains local spool CLI only.
5. Add deterministic checks for source/rig hashes, forced-alignment completeness, frame-zero preservation, render dimensions/fps/frame count, audio stream and unchanged narration, output hash, and bounded resource use. Keep diagnostic renders clearly marked; automated technical acceptance does not certify acting quality or production finish.

## Evidence and recovery

Seven local standard-library tests passed on macOS using synthetic inputs and mocked media/adapter boundaries: transport roundtrip, missing-adapter blocking, mutation refusal, job traversal, duration cap, serial lock and estimated-speech refusal. They do not verify real MP3 decoding, native Moho rendering, SSH or a live runner. CI workflow runs hosted transport tests only; it never executes PR code on the personal Mac. No external service costs or real media processing incurred.

Adapter timeout does not guarantee termination of Moho or child processes; inspect and stop them before another job. Logs remain private and currently have no size cap. Retention/cleanup is manual; preserve inputs and previous success until explicit deletion. Use only a trusted local spool owner; this is not a hostile multi-user service or sandbox for arbitrary adapter code.
