#!/usr/bin/env python3
"""Prepare 30s FCPXML-only native import candidates; NEVER opens Final Cut or a library.

Deliberately BLANK timeline diagnostics, not video deliverables. No personal
media, native FCP actions, model inference or external network calls. The user
must separately authorize importing into a NEW EMPTY disposable FCP library.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from fcp_interpreter_registration import validate_stage
from fcp_host_smoke import fixture


DEFAULT_DTD = Path('/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_13.dtd')


def create_candidate(file, width, height, label):
    """Derive from the host-tested FCPXML 1.13 fixture, changing only 30s duration."""
    fixture(file, width, height)
    tree = ET.parse(file)
    root = tree.getroot()
    assert root.get('version') == '1.13'
    project = root.find('./library/event/project')
    sequence = project.find('sequence')
    gap = sequence.find('./spine/gap')
    project.set('name', 'ROVOR NATIVE IMPORT TEST ' + label)
    sequence.set('duration', '30s')
    gap.set('duration', '30s')
    tree.write(file, encoding='utf-8', xml_declaration=True)

    parsed = ET.parse(file).getroot()
    fmts = parsed.findall('./resources/format')
    sequences = parsed.findall('./library/event/project/sequence')
    gaps = parsed.findall('./library/event/project/sequence/spine/gap')
    if (len(fmts) != 1 or len(sequences) != 1 or len(gaps) != 1
            or parsed.findall('.//asset') or parsed.findall('.//asset-clip')
            or fmts[0].get('width') != str(width)
            or fmts[0].get('height') != str(height)
            or fmts[0].get('frameDuration') != '1/60s'
            or sequences[0].get('duration') != '30s'
            or gaps[0].get('duration') != '30s'):
        raise ValueError('Unexpected geometry, duration or media reference')


def prepare(stage, output, dtd=DEFAULT_DTD, run=subprocess.run):
    stage_root, project, allowed = validate_stage(stage)
    output = output.expanduser().absolute()
    dtd = Path(dtd).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a brand-new directory')
    if not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('Output parent missing or symlinked')
    if output == stage_root or stage_root in output.parents or output in stage_root.parents:
        raise ValueError('Do not place native candidate inside prior evidence or stage')
    if not dtd.is_file() or dtd.is_symlink():
        raise ValueError('Final Cut Pro 1.13 DTD not installed at expected path')
    executable = shutil.which('xmllint')
    if not executable:
        raise ValueError('xmllint unavailable; cannot validate the installed DTD')
    # No Final Cut application, third-party MCP tool or paid provider is launched.
    with tempfile.TemporaryDirectory(prefix='.rovor-native-candidate-', dir=output.parent) as temp:
        staging = Path(temp)
        hashes = {}
        for label, width, height in (
            ('landscape', 1920, 1080), ('portrait', 1080, 1920)
        ):
            name = f'ROVOR-NATIVE-IMPORT-{label}-30s-60fps.fcpxml'
            source = staging / name
            create_candidate(source, width, height, label)
            try:
                result = run(
                    [executable, '--nonet', '--noout', '--dtdvalid',
                     str(dtd), str(source)],
                    check=False, capture_output=True, text=True, timeout=30)
            except subprocess.TimeoutExpired as exc:
                raise ValueError('Installed Apple DTD validation timed out') from exc
            if result.returncode != 0:
                diagnostic = ((result.stderr or '') + '\\n' + (result.stdout or '')).strip()
                diagnostic = diagnostic.replace('\\r', ' ').replace('\\n', ' | ')
                if not diagnostic:
                    diagnostic = '(xmllint returned no diagnostic output)'
                raise ValueError('Installed Apple DTD rejected 30s ' + label +
                                 ' FCPXML; xmllint exit=' + str(result.returncode) +
                                 '; diagnostic=' + diagnostic[:1800])
            hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
        text = (
            'ROVOR FINAL CUT NATIVE IMPORT GATE — technical test ONLY\n\n'
            'These are 30-second EMPTY FCPXML timelines at 60 fps, with no media.\n'
            'They are NOT videos, not edits and not a demonstration of rendering.\n'
            'Both XML files have been validated against this Mac’s installed Apple FCPXML 1.13 DTD.\n\n'
            'Manual operator-approved test, only if you choose to proceed:\n'
            '1. Quit any unattended editing agents. Do NOT open real client or Evan assets.\n'
            '2. In native Final Cut Pro create a new EMPTY library in a new disposable folder.\n'
            '3. Select that new library and use File > Import > XML. Choose ONLY the landscape XML here.\n'
            '4. Confirm a 30-second empty project at 1920x1080/60 fps if import succeeds.\n'
            '5. Repeat with portrait XML into that SAME disposable library, only after first passes.\n'
            '6. Record actual app version, import behavior, dimensions, frame rate and any errors.\n'
            '7. Do not treat this as an edit, export or final video; avoid real media and do not publish.\n\n'
            'No app import, edit or export has been performed by preparation of these files.\n'
            'If the native import behaves differently, STOP and report the observed UI.\n')
        (staging / 'READ_ME_FIRST.txt').write_text(text)
        data = {
            'schema_version': 1,
            'status': 'candidate_prepared_native_not_imported',
            'source_mcp_stage': str(stage_root),
            'output_dir': str(output),
            'fcpxml_version': '1.13',
            'duration_seconds': 30,
            'frame_rate': 60,
            'apple_dtd_sha256': hashlib.sha256(dtd.read_bytes()).hexdigest(),
            'fcpxml_sha256': hashes,
            'referenced_media_files': 0,
            'native_final_cut_import_verified': False,
            'native_final_cut_operated': False,
            'model_turn_started': False,
            'media_modified': False,
        }
        (staging / 'native-candidate-receipt.json').write_text(
            json.dumps(data, indent=2) + '\n')
        output.mkdir(mode=0o700)
        for source in staging.iterdir():
            dest = output / source.name
            shutil.copyfile(source, dest)
            dest.chmod(0o600)
    return data


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', type=Path, required=True,
                   help='Existing, proven Open Interpreter stage root')
    p.add_argument('--output', type=Path, required=True,
                   help='New, previously nonexistent native import candidate folder')
    p.add_argument('--dtd', type=Path, default=DEFAULT_DTD,
                   help='Installed Apple Final Cut Pro 1.13 DTD')
    args = p.parse_args(argv)
    try:
        report = prepare(args.stage, args.output, args.dtd)
        print(json.dumps(report, indent=2))
        print('Review READ_ME_FIRST.txt before ANY manual Final Cut native import.')
        return 0
    except Exception as exc:
        print('Native import candidate NOT READY: ' + type(exc).__name__ + ': ' + str(exc),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
