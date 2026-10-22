#!/usr/bin/env python3
"""Jane: import existing synthetic FCPXML into NEW native Final Cut library.

Uses Apple's documented FCPXML 'library location' option plus Open Document
Apple event, NOT GUI menu clicks. No model inference, real media, user-project
edits, existing library paths or arbitrary XML. A one-time macOS Automation
permission prompt may appear. Native timeline verification still unproven.
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
import time
import xml.etree.ElementTree as ET

DTD = Path('/Applications/Final Cut Pro.app/Contents/Frameworks/Interchange.framework/Versions/A/Resources/FCPXMLv1_13.dtd')
APP = Path('/Applications/Final Cut Pro.app')
LABELS = (('landscape', '1920', '1080'), ('portrait', '1080', '1920'))
OPEN_XML_SCRIPT = """
on run argv
    if (count of argv) is not 1 then error "Expected one FCPXML"
    tell application "Final Cut Pro"
        activate
        open POSIX file (item 1 of argv)
    end tell
end run
"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def in_root(base, path):
    return path == base or base in path.parents


def candidates_from_receipt(folder):
    folder = folder.expanduser().absolute()
    root = Path.home() / 'Documents' / 'Rovor'
    if not in_root(root, folder) or folder.is_symlink() or not folder.is_dir():
        raise ValueError('Candidates must be within ~/Documents/Rovor')
    manifest = folder / 'native-candidate-receipt.json'
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError('Missing trusted candidate receipt')
    receipt = json.loads(manifest.read_text())
    if (receipt.get('status') != 'candidate_prepared_native_not_imported'
            or receipt.get('duration_seconds') != 30
            or receipt.get('frame_rate') != 60
            or receipt.get('referenced_media_files') != 0
            or receipt.get('native_final_cut_operated') is not False):
        raise ValueError('Unsafe candidate receipt')
    hashes = receipt.get('fcpxml_sha256')
    if not isinstance(hashes, dict) or len(hashes) != 2:
        raise ValueError('Expected exactly two source XML hashes')
    inputs = {}
    for label, width, height in LABELS:
        filename = f'ROVOR-NATIVE-IMPORT-{label}-30s-60fps.fcpxml'
        source = folder / filename
        if (not source.is_file() or source.is_symlink()
                or source.stat().st_size > 100000 or sha(source) != hashes.get(filename)):
            raise ValueError('Candidate changed or missing: ' + label)
        root_xml = ET.parse(source).getroot()
        fmts = root_xml.findall('./resources/format')
        sequences = root_xml.findall('./library/event/project/sequence')
        gaps = root_xml.findall('./library/event/project/sequence/spine/gap')
        if (root_xml.tag != 'fcpxml' or root_xml.get('version') != '1.13'
                or len(fmts) != 1 or len(sequences) != 1 or len(gaps) != 1
                or fmts[0].get('width') != width
                or fmts[0].get('height') != height
                or fmts[0].get('frameDuration') != '1/60s'
                or sequences[0].get('duration') != '30s'
                or gaps[0].get('duration') != '30s'
                or root_xml.find('import-options') is not None
                or any('src' in node.attrib for node in root_xml.iter())
                or list(root_xml.findall('.//asset'))
                or list(root_xml.findall('.//asset-clip'))):
            raise ValueError('Source is not exact media-free 30s test format')
        inputs[label] = source
    return inputs


def receipt_write(folder, report):
    tmp = folder / 'receipt.tmp'
    with tmp.open('x') as out:
        json.dump(report, out, indent=2)
        out.write('\n')
    os.replace(tmp, folder / 'native-auto-import-receipt.json')


def prepare(candidates, output, dtd=DTD, run=subprocess.run):
    files = candidates_from_receipt(candidates)
    base = Path.home() / 'Documents' / 'Rovor'
    output = output.expanduser().absolute()
    if (not in_root(base, output) or output == base or output.is_symlink()
            or output.exists() or not output.parent.is_dir()
            or output.parent.is_symlink()):
        raise ValueError('Output must be a new path under ~/Documents/Rovor')
    if in_root(output, Path(candidates).expanduser().absolute()):
        raise ValueError('Output overlaps source candidates')
    if not dtd.is_file() or dtd.is_symlink():
        raise ValueError('Apple 1.13 DTD is missing')
    xmllint = shutil.which('xmllint')
    if not xmllint:
        raise ValueError('xmllint is required for safe import preparation')
    target_library = output / 'ROVOR-Jane-Test.fcpbundle'
    with tempfile.TemporaryDirectory(prefix='.rovor-jane-import-', dir=output.parent) as tmpname:
        tmp = Path(tmpname)
        local_dtd = tmp / 'FCPXMLv1_13.dtd'
        shutil.copyfile(dtd, local_dtd)
        if sha(local_dtd) != sha(dtd):
            raise ValueError('Apple DTD copy differs from installed DTD')
        xmlhashes = {}
        for label, _, _ in LABELS:
            root = ET.parse(files[label]).getroot()
            opts = ET.Element('import-options')
            ET.SubElement(opts, 'option', key='library location', value=target_library.as_uri())
            ET.SubElement(opts, 'option', key='copy assets', value='0')
            ET.SubElement(opts, 'option', key='suppress warnings', value='0')
            root.insert(0, opts)
            dest = tmp / (label + '-auto.fcpxml')
            ET.ElementTree(root).write(dest, xml_declaration=True, encoding='utf-8')
            process = run(
                [xmllint, '--nonet', '--noout', '--dtdvalid', str(local_dtd), str(dest)],
                check=False, capture_output=True, text=True, timeout=30)
            if process.returncode:
                error = (process.stderr or process.stdout or '').replace('\n', ' ')[:500]
                raise ValueError('DTD rejected automated ' + label + ': ' + error)
            xmlhashes[label] = sha(dest)
        output.mkdir(mode=0o700)
        for label, _, _ in LABELS:
            src = tmp / (label + '-auto.fcpxml')
            dst = output / src.name
            shutil.copyfile(src, dst)
            dst.chmod(0o600)
    report = {
        'status': 'ready_to_dispatch_not_launched',
        'target_library': str(target_library),
        'xml_hashes': xmlhashes,
        'apple_dtd_sha256': sha(dtd),
        'apple_event_sent': False,
        'library_creation_observed': False,
        'native_timeline_verified': False,
        'model_turn_started': False,
        'original_media_modified': False,
    }
    receipt_write(output, report)
    return report


def dispatch(output, report, run=subprocess.run, clock=time.monotonic,
             sleep=time.sleep, wait_seconds=65):
    if report['status'] != 'ready_to_dispatch_not_launched':
        raise ValueError('Refusing duplicate dispatch')
    if not APP.is_dir():
        raise ValueError('Final Cut Pro application not installed')
    target = Path(report['target_library'])
    try:
        for label, _, _ in LABELS:
            xml = output / (label + '-auto.fcpxml')
            # AppleScript argument separate from source: no path interpolation.
            result = run(['osascript', '-e', OPEN_XML_SCRIPT, str(xml)],
                         check=False, capture_output=True, text=True, timeout=90)
            report['apple_event_sent'] = True
            report['last_dispatched'] = label
            if result.returncode:
                report['status'] = 'apple_event_failed'
                report['error'] = ('osascript exit=' + str(result.returncode) + ' ' +
                                   (result.stderr or '').strip()[:1200])
                break
            if label == 'landscape':
                deadline = clock() + wait_seconds
                while not target.is_dir() and clock() < deadline:
                    sleep(1)
                if not target.is_dir():
                    report['status'] = 'native_library_not_observed'
                    report['error'] = 'Target library was not created; portrait NOT sent'
                    break
                report['library_creation_observed'] = True
        else:
            report['status'] = 'apple_events_sent_timeline_unverified'
    except subprocess.TimeoutExpired:
        report['status'] = 'apple_event_timeout'
        report['error'] = 'Possible macOS Automation permission prompt or modal'
    except Exception as exc:
        report['status'] = 'apple_event_failed'
        report['error'] = type(exc).__name__ + ': ' + str(exc)[:600]
    finally:
        report['native_timeline_verified'] = False
        receipt_write(output, report)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidates', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--dispatch', action='store_true',
                   help='Allow actual Apple event to create new test library')
    args = p.parse_args(argv)
    try:
        output = args.output.expanduser().absolute()
        state = prepare(args.candidates, output)
        if args.dispatch:
            state = dispatch(output, state)
        print(json.dumps(state, indent=2))
        return 0 if state['status'] in (
            'ready_to_dispatch_not_launched', 'apple_events_sent_timeline_unverified') else 2
    except Exception as exc:
        print('Jane native import stopped safely: ' + type(exc).__name__ + ': ' +
              str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
