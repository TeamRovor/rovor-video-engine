#!/usr/bin/env python3
"""Compile a VERIFIED chapter's English phone switches to a disposable .moho.

This is a safe, source-only native archive operation. No Moho executable,
renderer, Mac connection, source artwork changes, or guessed rig controls.
A trusted host must supply a genuine 60fps, correctly sized Moho template
and its explicitly calibrated switch-layer UUID and exact viseme child names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

from chapter_package import load_json, verify_package
import moho_compile as moho

MAX_MAPPING_BYTES = 64 * 1024
SHA_HEX = set("0123456789abcdef")


def _sha_file(path):
    with path.open("rb") as src:
        digest = hashlib.sha256()
        for block in iter(lambda: src.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(c in SHA_HEX for c in value))


def _calibration(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MAPPING_BYTES:
        raise ValueError("Missing or unsafe native rig calibration JSON")
    mapping = moho.decode(path.read_bytes())
    expected = {"schemaVersion", "chapterIndex", "templateSha256", "sourceWavSha256",
                "mouthLayerUuid", "restChild", "phoneToChild"}
    if not isinstance(mapping, dict) or set(mapping) != expected or mapping["schemaVersion"] != 1:
        raise ValueError("Unexpected rig calibration schema")
    if (type(mapping["chapterIndex"]) is not int or mapping["chapterIndex"] < 0
            or not _sha256(mapping["templateSha256"])
            or not _sha256(mapping["sourceWavSha256"])
            or not isinstance(mapping["mouthLayerUuid"], str) or not mapping["mouthLayerUuid"]
            or not isinstance(mapping["restChild"], str) or not mapping["restChild"]):
        raise ValueError("Missing exact chapter, source fingerprint or calibrated native mouth identity")
    phones = mapping["phoneToChild"]
    if (not isinstance(phones, dict) or not phones or
            any(not isinstance(k, str) or not k.isalpha() or not k.isupper()
                or not isinstance(v, str) or not v.strip()
                for k, v in phones.items())):
        raise ValueError("Invalid phoneme-to-native-switch calibration")
    return mapping


def _native_target(doc, mapping, frames):
    project = doc["project_data"]
    if (project.get("fps") != 60 or project.get("start_frame") != 1 or
            type(project.get("end_frame")) is not int or
            project["end_frame"] != frames):
        raise ValueError("Moho source template must already have exact chapter frame count at native 60fps")
    targets = [layer for layer in moho.layers(doc)
               if layer.get("uuid") == mapping["mouthLayerUuid"]]
    if len(targets) != 1 or targets[0].get("type") != "SwitchLayer":
        raise ValueError("Explicit native mouth layer UUID is missing, duplicated, or not a switch layer")
    target = targets[0]
    if target.get("switch_interpolation") is not False:
        raise ValueError("Interpolated native switches require separate real-rig validation")
    channel = target.get("switch_keys")
    if (not isinstance(channel, dict) or channel.get("type") != "String"
            or channel.get("ref") is not False or channel.get("mute") is not False
            or not isinstance(channel.get("when"), list)
            or not channel["when"] or channel["when"][0] != 0
            or not isinstance(channel.get("val"), list) or not channel["val"]
            or channel["val"][0] != mapping["restChild"]):
        raise ValueError("Native template must preserve a verified mouth-rest frame zero")
    names = [child.get("name") for child in target.get("layers", [])]
    if not names or any(not isinstance(name, str) or not name for name in names):
        raise ValueError("Native switch must have named child layers")
    if len(names) != len(set(names)):
        raise ValueError("Native switch layer has ambiguous child names")
    used = {mapping["restChild"], *mapping["phoneToChild"].values()}
    if not used.issubset(set(names)):
        raise ValueError("Calibrated mouth mapping references an absent switch child")
    return target


def compile_chapter(bundle_root, chapter_index, native_template, calibration,
                    destination):
    """Create a NEW real .moho archive containing a selected chapter's phones.

    A clean source package is required. Native document fps and end frame
    must ALREADY match this chapter; no unsafe 24->60 metadata retiming.
    The job does not transcribe, modify source rigs, or render movie frames.
    """
    bundle_root, native_template, destination = (Path(bundle_root),
                                                  Path(native_template),
                                                  Path(destination))
    if type(chapter_index) is not int or chapter_index < 0:
        raise ValueError("Invalid chapter number")
    if native_template.is_symlink() or not native_template.is_file():
        raise ValueError("Native Moho template must be an existing regular file, not symlink")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination exists; never replace original Moho project")
    if not destination.parent.is_dir() or destination.parent.is_symlink():
        raise ValueError("Output parent must be an existing regular directory")
    bundle = verify_package(bundle_root)
    ledger = load_json(Path(bundle_root) / "bundle.json")
    if chapter_index >= bundle["chapterCount"]:
        raise ValueError("Chapter number absent from independently verified package")
    selected = ledger["chapters"][chapter_index]
    folder = Path(bundle_root) / selected["directory"]
    evidence = load_json(folder / "chapter.json")
    chapter = evidence["chapterPlan"]
    speech = load_json(folder / "acoustic-plan.json")
    mapping = _calibration(calibration)
    actual_native_hash = _sha_file(native_template)
    if (mapping["chapterIndex"] != chapter_index or
            mapping["sourceWavSha256"] != ledger["sourceWavSha256"] or
            mapping["templateSha256"] != actual_native_hash):
        raise ValueError("Native template, chapter identity or original-audio binding changed")
    doc, _, _ = moho.load_archive(native_template)
    _native_target(doc, mapping, chapter["frameCount"])
    # The acoustic gate is independently re-run inside moho.speech_keys.
    # Use precisely the chapter's video frame interval, not the PCM segment
    # rounded to nearest 16kHz sample: the two can differ by half a sample.
    video_seconds = chapter["frameCount"] / 60
    keys = moho.speech_keys(speech, video_seconds,
                            mapping["phoneToChild"], mapping["restChild"])
    if (not keys or keys[0]["frame"] != 1 or keys[-1]["frame"] > chapter["frameCount"] or
            len(keys) > chapter["frameCount"] or
            any(k["value"] not in mapping["phoneToChild"].values() and
                k["value"] != mapping["restChild"] for k in keys)):
        raise ValueError("Calculated Moho mouth keys exceed the chapter bounds")
    proposal = {"fps": 60, "sourceSha256": actual_native_hash,
                "replaceTargetAnimation": True,
                "patches": [{"layerUuid": mapping["mouthLayerUuid"],
                             "channel": "switch_keys", "keys": keys}]}
    # Build into a private disposable area, verify the generated actual Moho
    # ZIP archive, then expose ONLY a fully validated, exclusive new output.
    # Existing sources and concurrent destination owners are never removed.
    with tempfile.TemporaryDirectory(prefix=".rovor-native-", dir=str(destination.parent)) as temp:
        candidate = Path(temp) / "compiled.moho"
        native_result = moho.compile_archive(native_template, candidate, proposal)
        compiled_doc, _, _ = moho.load_archive(candidate)
        after = _native_target(compiled_doc, mapping, chapter["frameCount"])
        if (after["switch_keys"]["when"] != [0] + [k["frame"] for k in keys]
                or after["switch_keys"]["val"] != [mapping["restChild"]] + [k["value"] for k in keys]):
            raise ValueError("Compiled native switch animation does not match verified acoustic keys")
        if _sha_file(native_template) != actual_native_hash:
            raise ValueError("Native source Moho template changed during compilation")
        output_hash = _sha_file(candidate)
        with destination.open("xb") as out, candidate.open("rb") as src:
            shutil.copyfileobj(src, out)
        if _sha_file(destination) != output_hash:
            raise ValueError("Native output archive copy verification failed")
    return {
        "status": "compiled_pending_native_moho_render_and_artistic_review",
        "chapterIndex": chapter_index,
        "chapterFrames": chapter["frameCount"],
        "fps": 60,
        "chapterAudioPcmSha256": selected["narrationPcmSha256"],
        "sourceOriginalWavSha256": ledger["sourceWavSha256"],
        "originalNativeTemplateSha256": actual_native_hash,
        "compiledArchiveSha256": output_hash,
        "targetNativeSwitchLayerUuid": mapping["mouthLayerUuid"],
        "verifiedSwitchKeyCount": len(keys),
        "frameZeroPreserved": native_result["frameZeroPreserved"],
        "nativeMohoCliRenderPerformed": False,
        "animatedCharacterArtValidated": False,
        "phonemeLipSyncVisuallyApproved": False,
        "studioApproval": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--chapter", type=int, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(compile_chapter(args.package, args.chapter,
                                         args.template, args.calibration, args.out),
                         indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
