#!/usr/bin/env python3
"""Run Moho's fixed read-only Lua inventory script and return validated JSON."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Optional

DEFAULT_MOHO = Path('/Applications/Moho.app/Contents/MacOS/Moho')
INSPECTOR = Path(__file__).with_name('moho_cli_inspect.lua')
MAX_REPORT_BYTES = 8 * 1024 * 1024


def reject_constant(value):
    raise ValueError(f'Invalid JSON number: {value}')


def inspect(project: Path, executable: Optional[Path] = None, timeout: int = 120) -> dict:
    project = project.expanduser().resolve(strict=True)
    if not project.is_file() or project.suffix.lower() != '.moho':
        raise ValueError('Project must be an existing .moho file')
    moho = executable or Path(os.environ.get('MOHO_EXECUTABLE', str(DEFAULT_MOHO))).expanduser()
    moho = moho.resolve(strict=True)
    if not moho.is_file() or not os.access(moho, os.X_OK):
        raise ValueError('Configured Moho executable is not runnable')
    if not INSPECTOR.is_file():
        raise ValueError('Bundled read-only Moho inspector is missing')

    with tempfile.TemporaryDirectory(prefix='rovor-moho-inspect-') as temp:
        os.chmod(temp, 0o700)
        report_path = Path(temp) / 'inventory.json'
        env = os.environ.copy()
        env['ROVOR_MOHO_PROJECT'] = str(project)
        env['ROVOR_MOHO_REPORT'] = str(report_path)
        result = subprocess.run([str(moho), str(INSPECTOR.resolve())], env=env,
                                stdin=subprocess.DEVNULL, capture_output=True,
                                timeout=timeout, check=False)
        if result.returncode != 0:
            detail = result.stderr.decode('utf-8', 'replace')[-2000:]
            raise RuntimeError(f'Moho CLI exited with status {result.returncode}: {detail}')
        if not report_path.is_file() or report_path.stat().st_size > MAX_REPORT_BYTES:
            raise ValueError('Moho did not produce a bounded inventory report')
        report = json.loads(report_path.read_text(encoding='utf-8'), parse_constant=reject_constant)
        if not isinstance(report, dict) or report.get('ok') is not True:
            raise ValueError('Moho inventory did not complete successfully')
        path_value = report.get('path')
        if not isinstance(path_value, str) or not path_value:
            raise ValueError('Moho inventory omitted its project path')
        reported_path = Path(path_value).expanduser()
        if not reported_path.is_absolute() or reported_path.resolve() != project:
            raise ValueError('Moho opened a different project than requested')
        required = {'name', 'width', 'height', 'fps', 'startFrame', 'endFrame',
                    'topLayers', 'totalLayers', 'layers'}
        if not required.issubset(report):
            raise ValueError('Moho inventory is missing required document fields')
        for key in ('width', 'height', 'fps', 'startFrame', 'endFrame', 'topLayers', 'totalLayers'):
            if type(report[key]) not in (int, float) or not float(report[key]) > 0:
                raise ValueError(f'Moho inventory has an invalid {key}')
        if not isinstance(report['layers'], list):
            raise ValueError('Moho inventory layers must be an array')
        return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('--moho', type=Path, help='Moho executable (or set MOHO_EXECUTABLE)')
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 600:
            raise ValueError('Timeout must be between 1 and 600 seconds')
        print(json.dumps(inspect(args.project, args.moho, args.timeout), indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(f'{type(exc).__name__}: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
