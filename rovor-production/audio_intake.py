"""Local, private Rovor audio catalog and preproduction intake.

Handles short and 8-9-minute MP3s without pretending auto-ASR is phoneme truth.
Does not render cartoons or publish narration. Input paths are restricted to
Rovor-controlled audio folders and the known reference WAV.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import wave

HOME = Path.home()
INBOX = HOME / "Movies/RovorAudioInbox"
OUT = HOME / "Movies/RovorProduction"
REFERENCE = HOME / "Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav"
FFMPEG = HOME / "Documents/Codex/2026-10-16/referenced-chatgpt-conversation-this-is-an/work/media-tools/ffmpeg"
VALID_EXT = {".mp3", ".wav", ".m4a", ".aac"}
MAX_DURATION = 900  # Explicit chapter boundary above 15 minutes.
ID_RE = re.compile(r"^[0-9a-f]{16}$")


def roots():
    folders = [INBOX]
    cloud = HOME / "Library/CloudStorage"
    candidates = list(cloud.glob("GoogleDrive*")) if cloud.is_dir() else []
    candidates += list(Path("/Volumes").glob("GoogleDrive*"))
    for mount in candidates:
        for prefix in ("My Drive", "MyDrive", ""):
            folder = mount / prefix / "shortsrovordigital"
            if folder.is_dir():
                folders.append(folder)
    return folders


def collect():
    found = {}
    for root in roots():
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file() or path.suffix.lower() not in VALID_EXT:
                continue
            real = path.resolve()
            if root.resolve() not in real.parents:
                continue
            stat = real.stat()
            if not (128 <= stat.st_size <= 2_000_000_000):
                continue
            identity = hashlib.sha256((str(real) + "|" + str(stat.st_size) + "|" +
                                       str(stat.st_mtime_ns)).encode()).hexdigest()[:16]
            found[identity] = {"id": identity, "name": real.name, "bytes": stat.st_size,
                               "source": "rovor-drive" if root != INBOX else "inbox", "_path": real}
    if REFERENCE.is_file():
        stat = REFERENCE.stat()
        key = hashlib.sha256((str(REFERENCE) + "|" + str(stat.st_size) + "|" +
                              str(stat.st_mtime_ns)).encode()).hexdigest()[:16]
        found[key] = {"id": key, "name": "Original Evan reference WAV", "bytes": stat.st_size,
                      "source": "reference", "_path": REFERENCE}
    return dict(sorted(found.items(), key=lambda pair: (pair[1]["name"].lower(), pair[0])))


def public_catalog(found):
    return [{key: value for key, value in row.items() if not key.startswith("_")}
            for row in found.values()]


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".partial")
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tool_config():
    configs = list((HOME / "Documents/Codex").glob("**/local_tools.json"))
    for path in sorted(configs):
        try:
            cfg = json.loads(path.read_text())
            if Path(cfg.get("whisper", "")).is_file() and Path(cfg.get("model", "")).is_file():
                return cfg
        except (ValueError, OSError, TypeError):
            continue
    return {}


def decode(audio, wav):
    ffmpeg = FFMPEG if FFMPEG.is_file() else None
    if ffmpeg is None:
        raise RuntimeError("Original known FFmpeg binary is unavailable; no audio was decoded")
    partial = wav.with_name("narration-16khz.partial.wav")
    try:
        subprocess.run([str(ffmpeg), "-nostdin", "-v", "error", "-y",
                        "-i", str(audio), "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(partial)], check=True, timeout=900)
        with wave.open(str(partial), "rb") as f:
            if f.getnframes() <= 0:
                raise ValueError("Audio decoder returned an empty WAV")
        partial.replace(wav)
    finally:
        if partial.exists():
            partial.unlink()
    with wave.open(str(wav), "rb") as f:
        duration = f.getnframes() / f.getframerate()
        if not (0 < duration <= MAX_DURATION):
            raise ValueError("Audio exceeds 15 minutes or is empty; split into chapters")
        if (f.getframerate(), f.getnchannels(), f.getsampwidth()) != (16000, 1, 2):
            raise ValueError("Decoded WAV must be 16 kHz mono PCM16")
    return duration


def graphs(wav, out):
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with wave.open(str(wav), "rb") as f:
        raw = f.readframes(f.getnframes())
        rate = f.getframerate()
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    step = 160  # 10 milliseconds at 16 kHz
    padded = np.pad(x, (0, (-len(x)) % step))
    windows = padded.reshape(-1, step)
    rms = np.sqrt(np.mean(windows * windows, axis=1))
    peak = np.max(np.abs(windows), axis=1)
    times = np.arange(len(rms)) * .01
    db = 20 * np.log10(np.maximum(rms, 1e-8))
    data = np.stack((times, rms, peak, db), axis=-1)
    np.savetxt(out / "waveform-10ms.csv", data, delimiter=",", fmt="%.6f",
               header="time_sec,rms,peak,rms_dbfs", comments="")
    fig, ax = plt.subplots(figsize=(16, 3.4))
    ax.plot(times[::5], db[::5], linewidth=.55)
    ax.set(xlabel="Recording time (seconds)", ylabel="RMS dBFS",
           title="Narration energy (10 ms measurements; 50 ms display sampling)")
    ax.set_ylim(-90, 0)
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(out / "waveform-overview.png", dpi=130)
    plt.close(fig)
    # Keep frequency evidence legible for 8-9-minute audio: one chart per minute.
    for chapter, start in enumerate(range(0, len(x), rate * 60), 1):
        sample = x[start:start + rate * 60]
        if len(sample) < 512:
            continue
        fig, ax = plt.subplots(figsize=(13, 3.4))
        ax.specgram(sample, Fs=rate, NFFT=512, noverlap=384,
                    cmap="magma", vmin=-120, vmax=-30)
        ax.set(xlabel=f"Time in chapter {chapter} (seconds)", ylabel="Frequency (Hz)",
               title=f"Spectrogram chapter {chapter}")
        ax.set_ylim(0, 6000)
        fig.tight_layout()
        fig.savefig(out / f"spectrogram-{chapter:02d}.png", dpi=110)
        plt.close(fig)
    return {"windows10ms": int(len(rms)), "durationSec": round(len(x) / rate, 6),
            "peakAbsolute": round(float(np.max(np.abs(x))), 6),
            "silentWindowsDbfsBelow45": int(np.sum(db < -45)),
            "waveformEvidence": "waveform-10ms.csv",
            "spectrogramCount": math.ceil(len(x) / (rate * 60))}


def transcribe(wav, out):
    cfg = tool_config()
    if not cfg:
        return {"status": "tool-unavailable", "reason": "No matching configured local Whisper executable and model"}
    exe = str(cfg["whisper"])
    prefix = out / "whisper-draft"
    expected = out / "whisper-draft.json"
    if not expected.is_file():
        subprocess.run([exe, "-m", cfg["model"], "-f", str(wav),
                        "-l", "en", "-oj", "-of", str(prefix)], check=True, timeout=7200)
    if not expected.is_file():
        return {"status": "tool-output-missing", "reason": "Whisper did not create transcript JSON"}
    result = json.loads(expected.read_text())
    lines = []
    for segment in result.get("transcription", []):
        text = segment.get("text", "").strip()
        if text:
            lines.append(text)
    (out / "transcript-DRAFT.txt").write_text(" ".join(lines) + "\n")
    return {"status": "machine-draft-requires-human-correction",
            "segmentCount": len(lines), "transcript": "transcript-DRAFT.txt",
            "phonemeBoundariesCertified": False}


def analyze(selected_id, with_asr=True):
    if not ID_RE.fullmatch(selected_id):
        raise ValueError("Invalid audio selection ID; use a catalog ID")
    catalog = collect()
    if selected_id not in catalog:
        raise ValueError("Selected recording not present in the allowlisted local audio library")
    row = catalog[selected_id]
    original = row["_path"]
    sha = digest(original)
    target = OUT / "analysis" / sha[:16]
    target.mkdir(parents=True, exist_ok=True)
    wav = target / "narration-16khz.wav"
    if wav.is_file() and wav.stat().st_size > 44:
        with wave.open(str(wav), "rb") as f:
            duration = f.getnframes() / f.getframerate()
        if not (0 < duration <= MAX_DURATION):
            raise ValueError("Cached WAV duration invalid")
    else:
        duration = decode(original, wav)
    if not (target / "waveform-10ms.csv").is_file():
        evidence = graphs(wav, target)
    else:
        evidence = {"status": "existing graphs preserved"}
    transcription = transcribe(wav, target) if with_asr else {"status": "not-requested"}
    manifest = {
        "audioId": selected_id,
        "audioSha256": sha,
        "durationSec": duration,
        "sourceType": row["source"],
        "recordingName": row["name"],
        "sampleRate": 16000,
        "pcmChannels": 1,
        "evidence": evidence,
        "transcription": transcription,
        "phonemeAlignment": "NOT_CERTIFIED",
        "studioStoryboard": "NOT_CREATED",
        "fullRender": "NOT_STARTED",
        "notes": ["Machine transcript is not authoritative.",
                  "English pronunciation and phoneme timing require verified script and acoustic alignment.",
                  "A waveform alone cannot identify English words or phonemes.",
                  "This intake does not claim visual or artistic approval."]
    }
    write_json(target / "analysis.json", manifest)
    print("ROVOR_AUDIO_ANALYSIS=COMPLETE")
    print("AUDIO_ID=" + selected_id)
    print("DURATION_SEC=" + str(round(duration, 3)))
    print("TRANSCRIPTION_STATUS=" + transcription["status"])
    print("PHONEME_CERTIFIED=NO")
    print("STORYBOARD_APPROVED=NO")
    print("PRIVATE_OUTPUT_DIR=" + str(target))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("catalog", "analyze"))
    parser.add_argument("--id", default="")
    parser.add_argument("--no-asr", action="store_true")
    args = parser.parse_args()
    if args.mode == "catalog":
        INBOX.mkdir(parents=True, exist_ok=True)
        results = public_catalog(collect())
        OUT.mkdir(parents=True, exist_ok=True)
        write_json(OUT / "audio-catalog.json", results)
        print("ROVOR_AUDIO_CATALOG_COUNT=" + str(len(results)))
        for row in results:
            print(f"{row['id']} | {row['name']} | {row['bytes']} bytes | {row['source']}")
    else:
        if not args.id:
            parser.error("--id is required for analyze")
        analyze(args.id, not args.no_asr)


if __name__ == "__main__":
    main()
