"""Offline Rovor sound-effects and background-music media library.

Stores actual audio under ~/Movies/RovorProduction/AudioLibrary/; only Python
code and metadata templates live in GitHub. Never infers legal permission from
a filename, uploads media, or marks sound design artistically approved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import wave

ROOT = Path.home() / "Movies" / "RovorProduction" / "AudioLibrary"
CATEGORIES = {"sound-effect": "SoundEffects", "background-music": "BackgroundMusic"}
EXTENSIONS = {".wav", ".mp3", ".flac", ".aiff", ".aif", ".m4a", ".ogg"}
LICENSE_KINDS = {"original-owned", "cc0", "separately-licensed"}
MAX_MUSIC_SECONDS = 3600.0
MAX_SFX_SECONDS = 90.0


class AssetRejected(ValueError):
    pass


def init_library(root=ROOT):
    root = Path(root).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    for category, folder in CATEGORIES.items():
        dest = root / folder
        if dest.is_symlink():
            raise AssetRejected("Audio folders cannot be symlinked")
        dest.mkdir(parents=True, exist_ok=True)
        guide = dest / "_HOW_TO_ADD_AUDIO.txt"
        if not guide.exists():
            guide.write_text(
                f"Rovor private {category} library.\n"
                "Put your audio files in this folder; WAV, MP3, FLAC, AIFF, M4A, OGG.\n"
                "For each track.wav add track.wav.asset.json beside it (template in repo).\n"
                "Only owner-verified source/license notes make an asset selectable.\n"
                "A filename, free download, or unverified license cannot establish rights.\n"
                "Do not place copyrighted mainstream music in this folder without rights.\n"
                "Nothing in this folder is uploaded to GitHub automatically.\n"
            )
    # Ship the two rights sidecar forms to the user's local library, not
    # just the GitHub repo, so importing existing files is straightforward.
    package=Path(__file__).resolve().parent
    for source_name,destination_name in (
        ("audio-library-sfx-sidecar.TEMPLATE.json", "_SFX-SIDECAR-TEMPLATE.json"),
        ("audio-library-music-sidecar.TEMPLATE.json", "_MUSIC-SIDECAR-TEMPLATE.json"),
    ):
        source=package/source_name
        dest=root/destination_name
        if source.is_file() and not dest.exists():
            dest.write_bytes(source.read_bytes())
    return root


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ffprobe():
    paths = []
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        paths.append(Path(ffprobe))
    ffmpeg = Path.home() / "Documents" / "Codex" / "2026-10-16" / "referenced-chatgpt-conversation-this-is-an" / "work" / "media-tools"
    paths.append(ffmpeg / "ffprobe")
    for path in paths:
        if path.is_file():
            return str(path)
    return None


def duration(path, ffprobe=None):
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as source:
                count, rate = source.getnframes(), source.getframerate()
                if rate <= 0 or count <= 0:
                    raise AssetRejected("Empty or malformed WAV")
                return count / rate
        except (wave.Error, EOFError, ZeroDivisionError) as exc:
            raise AssetRejected("Invalid PCM WAV") from exc
    tool = ffprobe or _ffprobe()
    if not tool:
        raise AssetRejected("ffprobe needed for non-WAV media; no duration assumed")
    try:
        run = subprocess.run([str(tool), "-v", "error", "-show_entries",
                              "format=duration:stream=codec_type", "-of", "json",
                              str(path)], capture_output=True, text=True,
                             timeout=30, check=True)
        result = json.loads(run.stdout)
        if not any(s.get("codec_type") == "audio" for s in result.get("streams", [])):
            raise AssetRejected("No decoded audio stream")
        seconds = float(result["format"]["duration"])
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
        raise AssetRejected("Cannot verify audio duration") from exc
    return seconds


def _metadata_valid(meta, category):
    if not isinstance(meta, dict) or meta.get("schemaVersion") != 1:
        raise AssetRejected("Missing asset schemaVersion=1")
    if meta.get("category") != category:
        raise AssetRejected("Asset placed in wrong category")
    tags = meta.get("eventTags", [])
    if (not isinstance(tags, list) or not 1 <= len(tags) <= 12 or
            any(not isinstance(v, str) or not v.strip() or len(v) > 48 for v in tags)):
        raise AssetRejected("Event tags must be 1-12 nonempty strings")
    if not isinstance(meta.get("description"), str) or len(meta["description"].strip()) < 8:
        raise AssetRejected("Describe what is actually audible in the asset")
    license_info = meta.get("license")
    if not isinstance(license_info, dict) or license_info.get("kind") not in LICENSE_KINDS:
        raise AssetRejected("License kind unverified or unsupported")
    if license_info.get("ownerConfirmedRights") is not True:
        raise AssetRejected("Owner must explicitly confirm permitted use")
    if not isinstance(license_info.get("source"), str) or len(license_info["source"].strip()) < 4:
        raise AssetRejected("Rights require exact source notes")
    if license_info["kind"] != "original-owned":
        evidence = license_info.get("evidence")
        if not isinstance(evidence, str) or len(evidence.strip()) < 8:
            raise AssetRejected("CC0/third-party use requires recorded license evidence")
    if category == "background-music":
        if meta.get("vocalContent") not in ("instrumental", "vocals", "unknown"):
            raise AssetRejected("Music vocal-content description required")
        if meta.get("loopable") not in (True, False):
            raise AssetRejected("Loopable status must be explicitly set")
    return tags


def inspect(path, category, root=ROOT, ffprobe=None):
    root = Path(root).resolve()
    folder = (root / CATEGORIES[category])
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
        raise AssetRejected("Missing/unsupported audio or symlink")
    resolved = path.resolve()
    if resolved.parent != folder.resolve():
        raise AssetRejected("Audio must be directly inside its own category folder")
    if path.stat().st_size < 128 or path.stat().st_size > 600_000_000:
        raise AssetRejected("Invalid audio file size")
    info = path.with_name(path.name + ".asset.json")
    if info.is_symlink() or not info.is_file() or info.resolve().parent != folder.resolve():
        raise AssetRejected("Sidecar rights file required beside every sound")
    try:
        meta = json.loads(info.read_text())
    except (OSError, UnicodeError, ValueError) as exc:
        raise AssetRejected("Invalid asset rights metadata") from exc
    tags = _metadata_valid(meta, category)
    seconds = duration(path, ffprobe)
    limit = MAX_SFX_SECONDS if category == "sound-effect" else MAX_MUSIC_SECONDS
    if not 0 < seconds <= limit:
        raise AssetRejected("Asset duration exceeds expected category limit")
    digest = sha256(path)
    declared = meta.get("sourceSha256")
    if declared is not None and declared != digest:
        raise AssetRejected("Audio changed after source hash was registered")
    return {
        "assetId": category + "-" + digest[:16],
        "category": category,
        "filename": path.name,
        "sha256": digest,
        "durationSeconds": round(seconds, 6),
        "bytes": path.stat().st_size,
        "description": meta["description"].strip(),
        "eventTags": tags,
        "mood": meta.get("mood", ""),
        "vocalContent": meta.get("vocalContent", "not-applicable"),
        "loopable": meta.get("loopable", False),
        "licenseKind": meta["license"]["kind"],
        "ownerConfirmedRights": True,
        "editorialApproved": False,
        "autoPublishApproved": False,
    }


def scan(root=ROOT, ffprobe=None):
    root = init_library(root)
    ready, rejected = [], []
    for category, folder in CATEGORIES.items():
        for path in sorted((root / folder).iterdir()):
            if not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                continue
            try:
                ready.append(inspect(path, category, root, ffprobe))
            except (AssetRejected, OSError, ValueError) as exc:
                rejected.append({"category":category,"filename":path.name,
                                 "reason":str(exc)})
    result = {"schemaVersion":1,"assetLibrary":str(root),"assets":ready,
              "rejected":rejected,"approvedForAutomatedPublishing":False}
    target = root / "catalog.json"
    temp = target.with_suffix(".partial")
    temp.write_text(json.dumps(result, indent=2)+"\n")
    temp.replace(target)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("init", "scan"))
    ap.add_argument("--root", type=Path, default=ROOT)
    args = ap.parse_args()
    if args.mode == "init":
        folder = init_library(args.root)
        print("ROVOR_SOUND_EFFECTS_FOLDER=" + str(folder / "SoundEffects"))
        print("ROVOR_BACKGROUND_MUSIC_FOLDER=" + str(folder / "BackgroundMusic"))
    else:
        result = scan(args.root)
        print("ROVOR_AUDIO_LIBRARY_SELECTABLE="+str(len(result["assets"])))
        print("ROVOR_AUDIO_LIBRARY_REJECTED="+str(len(result["rejected"])))
        for asset in result["assets"]:
            print("AUDIO_LIBRARY_ENTRY="+asset["assetId"]+" "+asset["filename"])
        for error in result["rejected"]:
            print("AUDIO_LIBRARY_REJECTED="+error["filename"]+" REASON="+error["reason"])
    print("UNLICENSED_OR_UNVERIFIED_AUDIO_ALLOWED=NO")


if __name__ == "__main__":
    main()
