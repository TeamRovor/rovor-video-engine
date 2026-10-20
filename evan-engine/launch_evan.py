"""Cross-platform local launcher. Accepts a dropped or pasted recording path."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys

from local_tools import dependency_errors, load_config


HERE = Path(__file__).resolve().parent


def input_path(value):
    raw = str(value).strip()
    if not raw:
        raise ValueError("Please provide one recording at a time.")
    direct = raw
    if len(direct) >= 2 and direct[0] == direct[-1] and direct[0] in "\"'":
        direct = direct[1:-1]
    path = Path(direct).expanduser()
    if path.is_file():
        return path.resolve()
    try:
        parts = shlex.split(raw, posix=os.name != "nt")
    except ValueError as error:
        raise ValueError("The recording path has unmatched quotes.") from error
    if len(parts) != 1:
        raise ValueError("Please provide one recording at a time.")
    path = Path(parts[0].strip("\"' ")).expanduser()
    if not path.is_file():
        raise ValueError("That recording could not be found.")
    return path.resolve()


def _quote_path(value):
    if os.name == "nt":
        return subprocess.list2cmdline([str(value)])
    return shlex.quote(str(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mp3", nargs="?", help="MP3 path; if omitted, the launcher prompts for it")
    parser.add_argument("--resume", type=Path, help="Continue an interrupted render folder")
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to local_tools.json (or set ROVOR_LOCAL_TOOLS_CONFIG)")
    parser.add_argument("--check", action="store_true", help="Check local tools without rendering")
    args = parser.parse_args()

    state = None
    if args.resume:
        destination = args.resume.expanduser().resolve()
        try:
            state = json.loads((destination / "render_request.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError("The render folder has no readable render_request.json.") from error
        if not isinstance(state, dict) or not state.get("mp3"):
            raise ValueError("The render folder is missing its source recording path.")
        recording = Path(state["mp3"]).expanduser()
        options = ["--resume", "--character", state.get("character", "reference")]
        if state.get("plan"):
            options.extend(["--plan", state["plan"]])
    else:
        recording = None
        destination = None
        options = []

    config_option = args.config or (state.get("config_path") if state else None)
    config, config_path = load_config(config_option)
    missing = dependency_errors(config)
    if args.check:
        if missing:
            raise ValueError("Missing local tools: " + ", ".join(missing))
        print("All local animation tools are present. No services contacted.")
        return
    if missing:
        raise ValueError("Missing local tools: " + ", ".join(missing))

    if not args.resume:
        print("EVAN — local recording to animation\nNo paid services are used.\n")
        supplied = args.mp3 or input("Drop or paste one MP3 path here, then press Return: ")
        recording = input_path(supplied)
        if recording.suffix.lower() != ".mp3":
            raise ValueError("Please choose an MP3 recording.")
        destination = HERE.parent / "evan-videos" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    result = subprocess.run(
        [sys.executable, str(HERE / "animate_evan.py"), str(recording), "--output", str(destination),
         "--config", str(config_path), *options],
        check=False,
    )
    if result.returncode:
        resume_command = "python launch_evan.py --resume " + _quote_path(destination)
        print("\nThe render stopped. Intermediate files are saved in: " + str(destination))
        print("To resume: " + resume_command)
        raise SystemExit(result.returncode)
    print("\nYour video is ready: " + str(destination / "evan.mp4"))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print("\n" + str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(130)

