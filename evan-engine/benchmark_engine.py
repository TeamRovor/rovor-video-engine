"""Measure the pipeline on synthetic narration; never reads private audio.

Run this through --compare to measure two engine trees on the same hosted
machine. Non-render stages are deterministic stubs. Frame rendering uses the
real Node/Sharp renderer and production output settings.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import wave


def _rss_bytes(pid: int) -> int:
    """Return a process's current resident memory using only OS facilities."""
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            handle = kernel32.OpenProcess(0x0400 | 0x0010, False, pid)
            if not handle:
                return 0
            try:
                counters = Counters()
                counters.cb = ctypes.sizeof(counters)
                if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                    return int(counters.WorkingSetSize)
            finally:
                kernel32.CloseHandle(handle)
            return 0
        if sys.platform.startswith("linux"):
            fields = Path(f"/proc/{pid}/statm").read_text().split()
            return int(fields[1]) * os.sysconf("SC_PAGE_SIZE")
        result = subprocess.run(
            ["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True,
            check=False, timeout=2,
        )
        return int(result.stdout.strip().splitlines()[0]) * 1024 if result.stdout.strip() else 0
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return 0


class MemorySampler:
    def __init__(self) -> None:
        self.pids = {os.getpid()}
        self.lock = threading.Lock()
        self.peak_bytes = 0
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def track(self, pid: int):
        sampler = self

        class Tracked:
            def __enter__(self):
                with sampler.lock:
                    sampler.pids.add(pid)

            def __exit__(self, *_):
                with sampler.lock:
                    sampler.pids.discard(pid)

        return Tracked()

    def _sample(self) -> None:
        while not self.stopped.is_set():
            with self.lock:
                pids = tuple(self.pids)
            total = sum(_rss_bytes(pid) for pid in pids)
            self.peak_bytes = max(self.peak_bytes, total)
            self.stopped.wait(0.1)

    def stop(self) -> int:
        self.stopped.set()
        self.thread.join()
        return self.peak_bytes


def _synthetic_transcript(duration: float) -> dict:
    count = max(1, int(duration // 2) + 1)
    phrases = ("A clear message helps.", "Your website matters.", "Rovor Digital builds better stories.")
    rows = []
    for i in range(count):
        start = i * duration / count
        end = min(duration, (i + 1) * duration / count)
        rows.append({"offsets": {"from": round(start * 1000), "to": round(end * 1000)},
                     "text": phrases[i % len(phrases)]})
    return {"transcription": rows}


def _run_engine(engine_root: Path, frames: int, output_root: Path) -> dict:
    sys.path.insert(0, str(engine_root))
    import animate_evan as engine
    import local_tools
    from unittest.mock import patch

    node = shutil.which("node")
    sharp = engine.HERE / "node_modules" / "sharp"
    if not node or not sharp.is_dir():
        raise RuntimeError("This benchmark needs Node.js and the installed pinned Sharp dependency.")

    duration = frames / 24
    fixture_root = output_root / "fixture"
    fixture_root.mkdir(parents=True)
    audio = fixture_root / "synthetic-narration.mp3"
    audio.write_bytes(b"SYNTHETIC BENCHMARK AUDIO\0" * 512)
    config_path = fixture_root / "local_tools.json"
    config_path.write_text("{}", encoding="utf-8")
    cfg = {name: "synthetic-" + name for name in local_tools.REQUIRED}
    cfg.update({"node": node, "sharp": str(sharp.resolve())})
    transcript = _synthetic_transcript(duration)
    cues = {"mouthCues": [
        {"start": i / 24, "end": (i + 1) / 24, "value": ("B", "E", "D", "X")[i % 4]}
        for i in range(frames)
    ]}
    memory = MemorySampler()
    memory.start()
    callbacks = []
    runner = {"phase": "cold", "frame_calls": 0, "failure_after_calls": None,
              "max_frames_per_call": None, "cold_invocations": 0, "recovery_invocations": 0}

    def perform_stage(args, env=None, timeout=180, stage="local step"):
        args = [str(arg) for arg in args]
        started = time.monotonic()
        if stage == "Audio conversion":
            with wave.open(args[-1], "wb") as out:
                out.setnchannels(1)
                out.setsampwidth(2)
                out.setframerate(16000)
                out.writeframes(b"\0\0" * (int(16000 * duration)))
            return ""
        if stage == "Speech transcription":
            Path(args[-1] + ".json").write_text(json.dumps(transcript), encoding="utf-8")
            return ""
        if stage == "Mouth timing":
            Path(args[args.index("-o") + 1]).write_text(json.dumps(cues), encoding="utf-8")
            return ""
        if stage == "Video encoding":
            Path(args[-1]).write_bytes(b"SYNTHETIC-MP4\0" * 8192)
            return ""
        if stage != "Frame rendering":
            raise RuntimeError("Unexpected benchmark pipeline stage: " + stage)

        runner["frame_calls"] += 1
        if (runner["phase"] == "failure" and runner["failure_after_calls"] is not None and
                runner["frame_calls"] > runner["failure_after_calls"]):
            raise RuntimeError("Synthetic interruption after a persisted frame checkpoint.")
        if runner["phase"] == "cold":
            runner["cold_invocations"] += 1
        elif runner["phase"] == "recovery":
            runner["recovery_invocations"] += 1

        render_args = args[:]
        if runner["max_frames_per_call"] is not None:
            start, end = int(render_args[-2]), int(render_args[-1])
            render_args[-1] = str(min(end, start + runner["max_frames_per_call"]))
        process = subprocess.Popen(
            render_args, cwd=engine.HERE, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
        )
        with memory.track(process.pid):
            stdout, stderr = process.communicate(timeout=timeout)
        if process.returncode:
            raise RuntimeError("Frame renderer failed: " + stderr[-2000:])
        return stdout.strip()

    def synthetic_run(args, env=None, timeout=180, stage="local step"):
        started = time.monotonic()
        try:
            return perform_stage(args, env=env, timeout=timeout, stage=stage)
        finally:
            engine.STAGE_SECONDS[stage] = engine.STAGE_SECONDS.get(stage, 0.0) + time.monotonic() - started

    def invoke(args):
        start_index = len(callbacks)
        try:
            with patch.object(sys, "argv", args), \
                patch.object(engine, "load_config", return_value=(cfg, config_path)), \
                patch.object(engine, "dependency_errors", return_value=[]), \
                patch.object(engine, "run", side_effect=synthetic_run), \
                patch.object(engine.atexit, "register", side_effect=callbacks.append), \
                redirect_stdout(io.StringIO()):
                engine.main()
        finally:
            # Mirror normal atexit order before starting the next invocation.
            for callback in reversed(callbacks[start_index:]):
                callback()
            del callbacks[start_index:]

    output_root.mkdir(parents=True, exist_ok=True)
    render = ["animate_evan.py", str(audio), "--output", str(output_root / "render"),
              "--config", str(config_path)]
    started = time.monotonic()
    invoke(render)
    cold_wall = time.monotonic() - started
    cold_metrics = json.loads((output_root / "render" / "render_metrics.json").read_text(encoding="utf-8"))
    cold_stages = dict(cold_metrics.get("stage_seconds", {}))

    runner.update({"phase": "warm", "frame_calls": 0})
    started = time.monotonic()
    invoke(render + ["--resume"])
    warm_wall = time.monotonic() - started
    warm_reused = sum(1 for path in (output_root / "render" / "frames").glob("*.jpg")
                      if engine.valid_frame(path))
    warm_invocations = runner["frame_calls"]

    render_dir = output_root / "render"
    progress_path = render_dir / "render_progress.json"
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    recovery_chunk = min(24, frames)
    checkpoint = frames - recovery_chunk
    for number in range(checkpoint, frames):
        (render_dir / "frames" / f"{number:06d}.jpg").unlink(missing_ok=True)
    progress["next_frame"] = checkpoint
    progress.pop("encoded_caption_sha256", None)
    progress_path.write_text(json.dumps(progress, sort_keys=True), encoding="utf-8")
    (render_dir / "evan.mp4").unlink(missing_ok=True)

    runner.update({"phase": "failure", "frame_calls": 0, "failure_after_calls": 1,
                   "max_frames_per_call": max(1, recovery_chunk // 3)})
    started = time.monotonic()
    try:
        invoke(render + ["--resume"])
    except RuntimeError as error:
        if "Synthetic interruption" not in str(error):
            raise
    else:
        raise RuntimeError("The injected renderer interruption did not occur.")
    failure_wall = time.monotonic() - started
    before_recovery = sum(1 for path in (render_dir / "frames").glob("*.jpg") if engine.valid_frame(path))

    runner.update({"phase": "recovery", "frame_calls": 0, "failure_after_calls": None,
                   "max_frames_per_call": None})
    started = time.monotonic()
    invoke(render + ["--resume"])
    recovery_wall = time.monotonic() - started
    final = json.loads((render_dir / "render_result.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    for number in range(frames):
        frame = render_dir / "frames" / f"{number:06d}.jpg"
        if not engine.valid_frame(frame):
            raise RuntimeError(f"Benchmark did not produce a valid frame: {frame.name}")
        digest.update(frame.read_bytes())

    peak_rss = memory.stop()
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "node": subprocess.run([node, "--version"], capture_output=True, text=True, check=True).stdout.strip(),
        "engine_version": final["engine_version"],
        "renderer_sha256": final["renderer_sha256"],
        "duration_seconds": duration,
        "frame_count": frames,
        "synthetic_audio_only": True,
        "cold_wall_seconds": round(cold_wall, 4),
        "cold_stage_seconds": {key: round(value, 4) for key, value in cold_stages.items()},
        "cold_frame_renderer_invocations": runner["cold_invocations"],
        "warm_resume_wall_seconds": round(warm_wall, 4),
        "warm_frame_cache_reuse_count": warm_reused,
        "warm_frame_renderer_invocations": warm_invocations,
        "failure_attempt_wall_seconds": round(failure_wall, 4),
        "recovery_wall_seconds": round(recovery_wall, 4),
        "recovery_existing_valid_frames": before_recovery,
        "recovery_frame_renderer_invocations": runner["recovery_invocations"],
        "recovery_overhead_seconds": round(failure_wall + recovery_wall, 4),
        "peak_rss_bytes_python_plus_renderer": peak_rss,
        "frame_bytes_sha256": digest.hexdigest(),
        "video_bytes": final["video_bytes"],
        "stage_timing_note": "Only Frame rendering invokes production work; other stages are deterministic synthetic fixtures.",
    }


def _compare(args) -> dict:
    script = Path(__file__).resolve()
    reports = {"baseline": [], "after": []}
    with tempfile.TemporaryDirectory(prefix="rovor-engine-benchmark-") as temporary:
        root = Path(temporary)
        roots = {"baseline": args.baseline_root, "after": args.after_root}
        for repeat in range(args.repeats):
            order = ("baseline", "after") if repeat % 2 == 0 else ("after", "baseline")
            for label in order:
                output = root / f"{label}-{repeat + 1}"
                command = [sys.executable, str(script), "--single", "--engine-root", str(roots[label]),
                           "--frames", str(args.frames), "--output-root", str(output)]
                result = subprocess.run(command, capture_output=True, text=True, check=False)
                if result.returncode:
                    raise RuntimeError(f"{label} benchmark repeat {repeat + 1} failed:\n"
                                       f"{result.stdout}\n{result.stderr}")
                reports[label].append(json.loads(result.stdout))

    numeric_fields = (
        "cold_wall_seconds", "cold_frame_renderer_invocations", "warm_resume_wall_seconds",
        "warm_frame_cache_reuse_count", "warm_frame_renderer_invocations",
        "failure_attempt_wall_seconds", "recovery_wall_seconds",
        "recovery_existing_valid_frames", "recovery_frame_renderer_invocations",
        "recovery_overhead_seconds", "peak_rss_bytes_python_plus_renderer",
    )

    def summarize(samples):
        result = dict(samples[0])
        result["runs"] = samples
        for field in numeric_fields:
            result[field] = round(statistics.median(sample[field] for sample in samples), 4)
        stage_names = set().union(*(sample["cold_stage_seconds"] for sample in samples))
        result["cold_stage_seconds"] = {
            stage: round(statistics.median(sample["cold_stage_seconds"].get(stage, 0.0)
                                           for sample in samples), 4)
            for stage in sorted(stage_names)
        }
        result["frame_bytes_sha256"] = samples[0]["frame_bytes_sha256"]
        return result

    baseline = summarize(reports["baseline"])
    after = summarize(reports["after"])
    frame_hashes = {sample["frame_bytes_sha256"] for samples in reports.values() for sample in samples}
    same_output = len(frame_hashes) == 1
    before = baseline["cold_wall_seconds"]
    now = after["cold_wall_seconds"]
    return {
        "schema_version": 1,
        "repeat_count": args.repeats,
        "baseline_ref": os.environ.get("ROVOR_BASELINE_REF", "local baseline"),
        "after_ref": os.environ.get("GITHUB_SHA", "local working tree"),
        "frame_output_identical": same_output,
        "cold_wall_change_percent": round((before - now) * 100 / before, 2) if before else None,
        "baseline": baseline,
        "after": after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--single", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--engine-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--output-root", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--frames", type=int, default=96, help="Synthetic frames to render per cold run (default: 96).")
    parser.add_argument("--repeats", type=int, default=3,
                        help="Cold/warm/failure samples per version; medians are reported (default: 3).")
    parser.add_argument("--baseline-root", type=Path, help="Engine tree at the baseline commit.")
    parser.add_argument("--after-root", type=Path, help="Engine tree after the change.")
    parser.add_argument("--output", type=Path, help="Write the comparison report as JSON.")
    args = parser.parse_args()
    if args.frames < 24:
        parser.error("--frames must be at least 24 to measure restart and recovery behavior.")
    if args.repeats < 3:
        parser.error("--repeats must be at least 3 to reduce runner noise.")
    if args.single:
        if not args.engine_root or not args.output_root:
            parser.error("Internal benchmark mode requires engine and output paths.")
        report = _run_engine(args.engine_root.resolve(), args.frames, args.output_root.resolve())
        print(json.dumps(report, sort_keys=True))
        return 0
    if not args.baseline_root or not args.after_root:
        parser.error("--baseline-root and --after-root are required.")
    report = _compare(args)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if report["frame_output_identical"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

