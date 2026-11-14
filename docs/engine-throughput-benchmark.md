# Engine throughput benchmark

## Result

GitHub Actions run [39522990095](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39522990095) compared the sequential renderer at baseline commit `4e1ef65135aaea8f09bf432e8768e380a8bf0d90` with bounded two-frame rendering at commit `da7c412206ec20b74aa642a16cfb31fc6bd78df5`. Each value is the median of three runs on the same hosted operating system.

| Hosted OS | Cold wall time, baseline → after | Cold frame stage, baseline → after | Total process CPU, baseline → after | Peak sampled RSS, baseline → after | Interrupted recovery, baseline → after |
| --- | ---: | ---: | ---: | ---: | ---: |
| Linux | 4.1766 s → 3.4398 s (17.64% faster) | 4.1586 s → 3.4219 s | 4.8422 s → 6.4113 s (+32.4%) | 216.2 MiB → 256.9 MiB (+40.7 MiB) | 1.4623 s → 1.2663 s |
| macOS | 2.2608 s → 1.6359 s (27.64% faster) | 2.2470 s → 1.6220 s | 3.7258 s → 4.1049 s (+10.2%) | 193.0 MiB → 245.6 MiB (+52.6 MiB) | 1.0448 s → 0.8272 s |
| Windows | 7.0930 s → 4.9840 s (29.73% faster) | 7.0000 s → 4.8750 s | 8.2346 s → 8.6724 s (+5.3%) | 118.1 MiB → 138.5 MiB (+20.2 MiB) | 1.9850 s → 1.8900 s |

Baseline and updated frames had identical byte hashes on each operating system. A warm resume reused all 96 cached frames and started no frame-renderer process. The interrupted recovery reused the 80 valid frames already present before finishing the last 16.

The renderer uses two concurrent frame jobs. This improves cold wall time on all three hosted systems, with higher process CPU and peak memory. The result is a throughput improvement with an explicit resource trade-off; it is not evidence that every resource cost fell.

The regular cross-platform regression run also passed on the updated branch: [39522990037](https://github.com/TeamRovor/rovor-video-engine/actions/runs/39522990037).

## Benchmark boundaries

The benchmark renders 96 frames (4 seconds) through the production Node/Sharp reference-art renderer at the existing 720×1280, 24 fps, JPEG quality 92 settings. It uses a synthetic MP3 fixture. Audio conversion, Whisper transcription, Rhubarb timing, and final video encoding are deterministic synthetic stages; their timings and CPU do not represent the real external tools. It does not assess speech accuracy or a complete narration render.

CPU reports sum the Python engine process and the child Node renderer. Node reports its user and system CPU time for the render process. Peak RSS is sampled every 100 ms across the Python and renderer processes, so it is an estimate of their maximum combined resident memory. The interrupted-resume measurement injects a stop after the renderer has returned a saved frame checkpoint; it does not simulate power loss.

The benchmark is reproducible from `.github/workflows/engine-throughput-benchmark.yml`. It compares against the commit immediately before two-frame rendering by default; `workflow_dispatch` can select a different baseline commit.

