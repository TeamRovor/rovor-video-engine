"""Friendly local launcher. Drag a recording into Terminal; no shell evaluation."""
from datetime import datetime
import json
from pathlib import Path
import shlex
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def input_path(value):
    raw = value.strip()
    direct = Path(raw).expanduser()
    if direct.is_file():
        return direct.resolve()
    parts = shlex.split(raw)
    if len(parts) != 1:
        raise ValueError('Please provide one recording at a time.')
    path = Path(parts[0]).expanduser()
    if not path.is_file():
        raise ValueError('That recording could not be found.')
    return path.resolve()


def preflight():
    config = json.loads((HERE / 'local_tools.json').read_text())
    missing = [name for name, value in config.items() if not Path(value).exists()]
    if missing:
        raise ValueError('Missing local tools: ' + ', '.join(missing) +
                         '. Keep the original Codex workspace on this Mac.')


def main():
    preflight()
    if '--check' in sys.argv:
        print('All local animation tools are present. No services contacted.')
        return
    print('EVAN — local recording to animation\nNo paid services are used.\n')
    if len(sys.argv) >= 3 and sys.argv[1] == '--resume':
        destination = Path(sys.argv[2]).expanduser().resolve()
        state = json.loads((destination / 'render_request.json').read_text())
        recording = Path(state['mp3'])
        options = ['--resume', '--character', state.get('character','reference')]
        if state.get('plan'):
            options.extend(['--plan', state['plan']])
    else:
        recording = input_path(input('Drag one MP3 here, then press Return: '))
        if recording.suffix.lower() != '.mp3':
            raise ValueError('Please choose an MP3 recording.')
        destination = HERE.parent / 'evan-videos' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        options = []
    result = subprocess.run([sys.executable, str(HERE / 'animate_evan.py'),
                             str(recording), '--output', str(destination), *options])
    if result.returncode:
        print('\nThe render stopped. Intermediate files are saved in: ' + str(destination))
        print('To resume: python3 launch_evan.py --resume ' + shlex.quote(str(destination)))
        raise SystemExit(result.returncode)
    print('\nYour video is ready: ' + str(destination / 'evan.mp4'))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print('\n' + str(error), file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nStopped.')
        sys.exit(130)
