"""Cross-platform configuration and preflight checks for local render tools."""
import json
import os
from pathlib import Path
import shutil
import subprocess


ENGINE = Path(__file__).resolve().parent
REQUIRED = ("ffmpeg", "whisper", "model", "rhubarb", "node")
EXECUTABLES = ("ffmpeg", "whisper", "rhubarb", "node")


def default_config_path(explicit=None):
    value = explicit or os.environ.get("ROVOR_LOCAL_TOOLS_CONFIG") or ENGINE / "local_tools.json"
    value = os.path.expandvars(os.path.expanduser(str(value)))
    return Path(value).resolve()


def load_config(explicit=None):
    path = default_config_path(explicit)
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(
            f"Local tool config not found: {path}. Create local_tools.json from the "
            "platform-appropriate example in the engine README, then set the tool paths."
        ) from error
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read local tool config {path}: {error}") from error
    if not isinstance(config, dict):
        raise ValueError("Local tool config must contain a JSON object.")
    missing = [name for name in REQUIRED if not isinstance(config.get(name), str) or not config[name].strip()]
    if missing:
        raise ValueError("Local tool config is missing required string values: " + ", ".join(missing))
    config = {
        key: os.path.expandvars(os.path.expanduser(value.strip()))
        for key, value in config.items()
        if isinstance(value, str)
    }
    config.setdefault("sharp", "sharp")
    for key in (*REQUIRED, "sharp"):
        value = config.get(key)
        if not value:
            continue
        if key == "model" or _has_path_component(value):
            candidate = Path(value).expanduser()
            if not candidate.is_absolute():
                candidate = path.parent / candidate
            config[key] = str(candidate.resolve())
    for key in EXECUTABLES:
        if not _has_path_component(config[key]):
            resolved = shutil.which(config[key])
            if resolved:
                config[key] = str(Path(resolved).resolve())
    return config, path


def _has_path_component(value):
    return Path(value).is_absolute() or "/" in value or "\\" in value


def _executable_available(value):
    if _has_path_component(value):
        return Path(value).is_file()
    return shutil.which(value) is not None


def dependency_errors(config):
    missing = [name for name in EXECUTABLES if not _executable_available(config[name])]
    model = Path(config["model"])
    if not model.is_file():
        missing.append("model")

    sharp = config.get("sharp", "sharp")
    try:
        result = subprocess.run(
            [config["node"], "-e", "require.resolve(process.argv[1])", sharp],
            cwd=ENGINE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
        if result.returncode:
            missing.append("sharp")
    except (OSError, subprocess.TimeoutExpired):
        missing.append("sharp")
    return missing

