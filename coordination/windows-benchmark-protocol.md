# Windows render throughput and cache/resume acceptance protocol

**Status:** source-inspected, reproducible protocol; **not a new benchmark run, Windows laptop verification, or artistic approval**. The benchmark uses 96 synthetic frames at 720×1280/24 fps, not the 1080p60/30-second production gate. Execute from an authorized workstation or a functioning GitHub Actions runner. This file intentionally does not edit the owned rendering/cache implementation.

## Versioned source of truth

- Inspected development branch: [codex/windows-reliability-v3-1](https://github.com/TeamRovor/rovor-video-engine/tree/codex/windows-reliability-v3-1), HEAD **e8ef17c0c5c3f06224d6cc87b587385cf244d3ec** at documentation time.
- Existing runner: evan-engine/benchmark_engine.py (blob **ea9abe86cb8309bc85d7f3c55db83a58fe3610a9**); hosted workflow: .github/workflows/engine-throughput-benchmark.yml (blob **cca31531308f40839358c373a46e90942f9591f1**).
- Existing engine script: evan-engine/animate_evan.py (blob **c2643cf5571676fe74e329d0c39c939e493847e0**); existing Windows reliability tests: evan-engine/test_windows_reliability.py (blob **33e0dfb238ac7339984302b6b9dc40d17b76e34d**).
- Baseline used by the existing workflow: **4e1ef65135aaea8f09bf432e8768e380a8bf0d90**. Prior, separately verified results and trade-offs are in [docs/engine-throughput-benchmark.md](https://github.com/TeamRovor/rovor-video-engine/blob/codex/windows-reliability-v3-1/docs/engine-throughput-benchmark.md) on the Windows branch, with [Actions run 39522990095](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39522990095). Those historical measurements are not fresh laptop benchmarks.
- Active separate ownership: render-cache-file-identity; this document must **not** be used to modify evan-engine/animate_evan.py, tests, frame generation or its active PR without coordination.

## What the current benchmark actually measures

The existing stdlib Python runner creates a **synthetic, invalid-as-media MP3 fixture** and stubs audio conversion, Whisper, Rhubarb and final MP4 encoding. It invokes the **actual Node/Sharp reference-art frame renderer**, and compares two isolated engine trees on the **same operating system/runner**, alternating baseline/after order for **3 repeats**. It measures cold start, full warm resume, an intentionally interrupted render after a persisted frame checkpoint and recovery. The generated final MP4 bytes are synthetic; they must never be published as a real decoded video.

For the default 96-frame run: expected fully reused warm frames = **96**, warm renderer invocations = **0**, and valid frames after the injected failure before recovery = **80** (the first 72 retained plus 8 saved from the partial batch). The runner hashes concatenated frame bytes per run. It exits nonzero if frame hashes differ across all baseline/after repeats.

Machine preflight: record OS/build, CPU/RAM, git revision(s), Python 3.11 (CI's version), Node 24 (CI's version) and the pinned Sharp dependency. No real media or client data are needed. CPU and memory comparisons must be paired on the same host; do not compare Windows timings against macOS timings to assert performance gains.

## Existing GitHub Actions path (preferred if runners resume)

The existing workflow is [engine-throughput-benchmark.yml](https://github.com/TeamRovor/rovor-video-engine/blob/codex/windows-reliability-v3-1/.github/workflows/engine-throughput-benchmark.yml). At GitHub Actions, select **Engine throughput benchmark → Run workflow**, branch **codex/windows-reliability-v3-1**, optional baseline_ref **4e1ef65135aaea8f09bf432e8768e380a8bf0d90**. The workflow runs the Linux, Windows and macOS matrix with Python 3.11 and Node 24, installing the pinned renderer in both trees and saving an engine-throughput-*OS*.json artifact. Its effective comparison command is:

~~~sh
python evan-engine/benchmark_engine.py --frames 96 --baseline-root benchmark-baseline/evan-engine --after-root evan-engine --output engine-throughput-report.json
~~~

**Critical limitation:** recent ROVOR hosted Actions failures have occurred before any job steps and lacked readable logs. A queued/pre-step failure is **not** a benchmark result; no new timing or correctness claim should be made from such a run. Record run URL, runner OS, job/step status and whether the artifact exists. Do not weaken test gates to force green.

## Manual Windows PowerShell path (isolated worktrees)

From a clean, authenticated local clone containing the Windows development branch. These commands deliberately create temporary, detached worktrees, leaving the active development checkout untouched. **Do not run on an unsaved/uncertain clone**; check git status first. Requires Git, Python 3.11, Node 24, npm, network to install pinned Sharp. The exact after revision is printed before measurement.

~~~powershell
git status --short
git fetch origin codex/windows-reliability-v3-1
git cat-file -t 4e1ef65135aaea8f09bf432e8768e380a8bf0d90
py -3.11 --version
node --version
npm --version
$base = Join-Path $env:TEMP ("rovor-bench-base-" + [guid]::NewGuid().ToString("N"))
$after = Join-Path $env:TEMP ("rovor-bench-after-" + [guid]::NewGuid().ToString("N"))
$report = Join-Path $env:TEMP ("rovor-bench-report-" + [guid]::NewGuid().ToString("N") + ".json")
git worktree add --detach $base 4e1ef65135aaea8f09bf432e8768e380a8bf0d90
git worktree add --detach $after origin/codex/windows-reliability-v3-1
git -C $base rev-parse HEAD
git -C $after rev-parse HEAD
npm install --no-audit --no-fund --package-lock=false --prefix (Join-Path $base "evan-engine")
npm install --no-audit --no-fund --package-lock=false --prefix (Join-Path $after "evan-engine")
py -3.11 (Join-Path $after "evan-engine/benchmark_engine.py") --frames 96 --repeats 3 --baseline-root (Join-Path $base "evan-engine") --after-root (Join-Path $after "evan-engine") --output $report
if ($LASTEXITCODE -ne 0) { throw "Benchmark failed; preserve log and investigate." }
$bench = Get-Content -Raw $report | ConvertFrom-Json
if ($bench.repeat_count -ne 3 -or -not $bench.frame_output_identical) { throw "Frame equivalence/repeat-count failure" }
foreach ($side in @("baseline", "after")) {
    foreach ($run in $bench.$side.runs) {
        if ($run.frame_count -ne 96 -or $run.warm_frame_cache_reuse_count -ne 96 -or
            $run.warm_frame_renderer_invocations -ne 0 -or
            $run.recovery_existing_valid_frames -ne 80) {
            throw "Cold/warm/interruption recovery contract failed: $side"
        }
    }
}
$bench | Select-Object baseline_ref, after_ref, frame_output_identical, cold_wall_change_percent
Write-Output "Benchmark report: $report"
~~~

If Git cannot resolve the pinned baseline commit after fetch, fetch that commit explicitly through your authorized remote before proceeding; do **not** silently substitute another baseline. Do not delete or force-reset either checkout on error. Once independently verified, clean up **only the new benchmark worktrees** using git worktree remove with their printed paths, and remove temporary reports intentionally. Do not place reports containing local directory paths, caches, or workstation diagnostics in public GitHub without review.

## Acceptance measurements and failure classification

| Gate | Field / source | Pass / interpretation |
| --- | --- | --- |
| Reproducible input | baseline/after SHA, OS, Python, Node, Sharp, 96 frames, 3 repeats | Both trees execute on same host with same synthetic input and rendering parameters; commit IDs recorded. |
| Identical actual frames | frame_output_identical and every run's frame_bytes_sha256 | Must be true and hashes equal across **all** runs. This does not prove production-scene visual fidelity. |
| Cold wall latency | cold_wall_seconds and cold_stage_seconds.Frame rendering | Compare medians; record absolute delta and percentage, not just a claimed speedup. |
| Resource trade-off | cold_total_process_cpu_seconds and peak_rss_bytes_python_plus_renderer | Record both, including regressions; RSS is sampled every 100 ms and may miss brief peaks. |
| Warm reuse | warm_frame_cache_reuse_count and warm_frame_renderer_invocations | Exactly 96 reused frames and zero frame renderer invocations for each run. |
| Interrupted recovery | failure_attempt_wall_seconds, recovery_wall_seconds, recovery_existing_valid_frames, recovery_frame_renderer_invocations | Failure must be deliberate, 80 valid frames retained before recovery and all final frame hashes equal. This is a checkpoint interruption, **not** power-loss durability. |
| Changes invalidate appropriately | real-engine regression tests below | These are distinct from the synthetic throughput comparison; assess cache correctness separately. |
| Production acceptance | actual original-audio MP4, dimensions, 60 fps, 30+ sec, decoded timing, visible hands/props, creative review | **Not covered by this benchmark**, so cannot be marked pass on this evidence alone. |

If a paired comparison fails, retain raw per-repeat results. If the after branch changes source art or an intentional render algorithm, byte identity may legitimately differ, but this test is then **not** a passing same-output optimization: review output correctness separately, create an explicit new baseline, and do not erase the mismatch. Compare timing only after correctness gates have been met.

## Cache/invalidation regression matrix (separate checks)

Execute the **existing tests** for the exact after revision; do not mutate original narrations, artwork or another session's active checkout.

~~~powershell
Push-Location (Join-Path $after "evan-engine")
py -3.11 -m unittest test_windows_reliability -v
Pop-Location
~~~

The source inspection identifies these existing cases:
- unchanged output resume: test_completed_resume_reuses_all_expensive_stages (no extra expensive stage);
- caption-only change: test_caption_correction_reuses_audio_transcript_and_mouth_timing (redraw and encode, but do not rerun transcription/mouth timing);
- simulated interrupted batch: test_interrupted_frame_batch_resumes_at_saved_checkpoint; truncated JPEG: test_truncated_frame_is_rebuilt_before_encoding;
- altered transcript: test_transcript_dialogue_edit_refreshes_mouth_timing;
- altered audio: test_changed_audio_never_silently_reuses_old_render;
- invalid captions: test_overlapping_captions_rejected_before_frame_work;
- duplicate process: test_render_folder_lock_blocks_second_process_and_releases;
- failed replacement: test_failed_resume_does_not_claim_previous_success.

**Artwork/code identity:** animate_evan.py renderer_fingerprint() enumerates the renderer's code files and the evan-character/v3-assets tree. The active render-cache-file-identity task is separately owned. A meaningful art-change test requires either an already-reviewed regression case or a disposable copy: alter a copy of a referenced art file, confirm invalidation or refusal, and confirm an untouched original. Never edit the approved art. Do not assert this gate passed from the frame-throughput runner or from a code inspection alone.

For **real** MP3 validation later, take a newly authorized input in a disposable workspace, record SHA-256 and file size, render once, resume unchanged, correct a copy of captions.srt and resume, then change only the copied narration and verify a fresh request is forced. Record executed process names, actual MP4 decode, audio identity and original source hashes. The current V3 Windows renderer is documented as a 720×1280/24fps, <=60-second intermediate engine. Production 1080p60, >=30 seconds, real Moho and artist approval must be assessed in their **separate existing** workstreams.

## Handoff checklist

Attach source and baseline exact commits, OS/tool versions, Actions run URLs or local timestamp, unredacted-safe report JSON path, the median cold/warm/recovery metrics, all-run hashes, resource trade-off, regression test output and any missing tools/tests. Mark individually: **source inspected**, **synthetic test executed**, **real input executed**, **laptop verified**, **studio visual approved**, **publication approved**. A draft report or missing hosted runner does not satisfy the subsequent states.

Next eligible engineering work requires a separate queue claim. Do not assign Keona's active render-cache-file-identity work to this document owner.