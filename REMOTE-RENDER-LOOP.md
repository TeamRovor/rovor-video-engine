# Private MP3 job transport — implemented, Moho renderer pending

2026-10-19 America/Chicago. Inspected main 996f8948, open PRs #2/#4/#5/#7/#12, Issue #6 comments and existing read-queue runner code. Preserve those branches and Evan artwork. This change adds transport only; it does not substitute the V3 sprite engine for Moho.

## Verified boundaries

Issue #6 records Mac runner reads of document metadata/layers, a native-template inventory and a checksum-matched disposable tutorial copy. The last recorded document read was unsaved Untitled at 1280x720/24fps, not an approved Evan production project. This session's direct Moho preflight timed out after 10 seconds. The V4 Evan status tool reports ready but explicitly says it is not Moho. Current runner online status, Moho writes/export, and native Evan rig readiness are unverified.

Existing main `.github/scripts/rovor_moho_read_queue.py` accepts only two read methods. Its workflow targets `[self-hosted, macOS, X64, rovor-video]`, uses the exact main commit, and wakes the viewport after IPC arrives. Do not widen that read allowlist to execute render commands. Do not reinstall the already documented bridge. PR #7 owns Windows reliability; #4/#5 own art/acting and acoustic alignment. No experimental branches are merged here.

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

## Exact remaining Mac/access steps

1. On the intended Mac, confirm the existing runner identity and labels in repository Settings → Actions → Runners; verify it runs in the logged-in user's GUI session. Inspect the existing manual read-only workflow and Issue #6, then run that check from trusted main. A successful runner job alone is insufficient: require a fresh Moho document/layer response. Current chat tools have no workflow dispatch capability verified here.
2. Keep the Mac awake and Moho Pro 14 licensed/open. Check the existing Lua poller and Node bridge use the same user's IPC temporary directory. Use the prior viewport wake strategy. Grant macOS Automation permission for the runner's activation of Moho only if prompted; do not grant broad access speculatively.
3. Confirm the exact active disposable native project path, copied-source hash, layer IDs and bone names. Preserve originals and frame zero. Dry-run a supported named-bone pose and inspect it before a permitted write. The tutorial copy is only a diagnostic, not Evan's rig. Obtain the real approved native Evan project and linked assets from its owner; do not rebuild the character from this transport task.
4. Implement/review a host-owned adapter against actual installed Moho capabilities: source-derived WAV, corrected English transcript, existing forced-aligned word/ARPABET phone pipeline, strict `tools/speech_plan_gate.py`, existing scene metadata, approved rig mapping, disposable-copy animation and native export. Do not use letters, word-length timing or Rhubarb shapes as phoneme evidence. Resolve review flags before expensive work. Test native 1920x1080/60 export and unchanged narration muxing; do not assume a command-line export API exists.
5. Adapter must write `render.mp4`, `speech-audit.json` from the real source-WAV gate, and `moho-evidence.json` with renderer=`Moho Pro 14`, sourceSha256, disposableProjectVerified=true and rigSha256. These are trusted adapter attestations, not independent proof of pronunciation or artwork. The wrapper checks acoustic QA, media dimensions/fps/audio/duration and artifact hash. Duration agreement cannot prove narration identity: adapter must verify source provenance through muxing. Human listening and visual review remain mandatory.
6. For remote access choose the existing trusted runner or an authenticated private SSH connection to this Mac. An administrator must authorize the exact account, directories and trusted worker executable. Do not expose unauthenticated Moho IPC publicly. Stage the MP3 privately on the Mac, invoke the four commands above through that authorized channel, and copy only the verified artifact back. Windows can submit/inspect the same contract after authenticated transport setup; GitHub connector access does not supply Windows desktop or Mac shell access.
7. For **single-upload ChatGPT** delivery a connected authenticated tool still must accept the uploaded file bytes, privately transfer them, invoke the fixed worker, poll status and return the verified MP4 as an attachment. No such upload-to-Mac connector is implemented here. This spool CLI is its tested backend boundary, not a registered ChatGPT remote render action. Do not put private MP3s, host paths or credentials in workflow inputs/logs. Existing audio import remains owned separately.
8. Render a 30+ second original narration sample, inspect pronunciation/contacts/body acting/scene purpose at normal speed, and obtain Amar's visual approval. `review_required` never means polished/approved/published.

## Evidence and recovery

Seven local standard-library tests passed on macOS using synthetic inputs and mocked media/adapter boundaries: transport roundtrip, missing-adapter blocking, mutation refusal, job traversal, duration cap, serial lock and estimated-speech refusal. They do not verify real MP3 decoding, native Moho rendering, SSH or a live runner. CI workflow runs hosted transport tests only; it never executes PR code on the personal Mac. No external service costs or real media processing incurred.

Adapter timeout does not guarantee termination of Moho or child processes; inspect and stop them before another job. Logs remain private and currently have no size cap. Retention/cleanup is manual; preserve inputs and previous success until explicit deletion. Use only a trusted local spool owner; this is not a hostile multi-user service or sandbox for arbitrary adapter code.
