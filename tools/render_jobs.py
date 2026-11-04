#!/usr/bin/env python3
"""Private local spool: transport only; no built-in Moho renderer or remote shell."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

MAX_BYTES = 25 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    tmp = path.with_suffix('.partial')
    tmp.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    os.chmod(path, 0o600)

def job(root, ident):
    if not re.fullmatch(r'[0-9a-f]{32}', ident):
        raise ValueError('Invalid job ID')
    path = root / ident
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Unknown job')
    return path

def probe(path, runtime_root=None):
    """Inspect media with ffprobe when installed, otherwise Apple's AVFoundation."""
    ffprobe = shutil.which('ffprobe')
    if ffprobe:
        r = subprocess.run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, timeout=20, check=True)
        return json.loads(r.stdout)
    swiftc = shutil.which('swiftc')
    helper = Path(__file__).with_name('media_probe.swift')
    if not swiftc or not helper.is_file():
        raise RuntimeError('Media verification needs ffprobe or macOS swiftc with the bundled AVFoundation probe')
    runtime = Path(runtime_root or Path.home() / 'Library' / 'Application Support' / 'Rovor' / 'moho-render') / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(runtime, 0o700)
    executable = runtime / 'media-probe'
    if not executable.is_file() or executable.stat().st_mtime < helper.stat().st_mtime:
        partial = runtime / 'media-probe.partial'
        module_cache = runtime / 'module-cache'
        module_cache.mkdir(mode=0o700, exist_ok=True)
        subprocess.run([swiftc, '-parse-as-library', '-module-cache-path', str(module_cache), '-O', str(helper), '-o', str(partial)], capture_output=True, text=True, timeout=180, check=True)
        os.chmod(partial, 0o700)
        partial.replace(executable)
    r = subprocess.run([str(executable), str(path)], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(r.stdout)

def video_quality(path, runtime_root=None):
    """Sample native frames to reject completely black or frozen MP4 exports."""
    swiftc = shutil.which('swiftc')
    helper = Path(__file__).with_name('video_quality.swift')
    if not swiftc or not helper.is_file():
        raise RuntimeError('Visual frame verification needs macOS swiftc and the bundled AVFoundation helper')
    runtime = Path(runtime_root or Path.home() / 'Library' / 'Application Support' / 'Rovor' / 'moho-render') / 'runtime'
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(runtime, 0o700)
    executable = runtime / 'video-quality'
    if not executable.is_file() or executable.stat().st_mtime < helper.stat().st_mtime:
        partial = runtime / 'video-quality.partial'
        module_cache = runtime / 'module-cache'
        module_cache.mkdir(mode=0o700, exist_ok=True)
        subprocess.run([swiftc, '-parse-as-library', '-module-cache-path', str(module_cache), '-O', str(helper), '-o', str(partial)], capture_output=True, text=True, timeout=180, check=True)
        os.chmod(partial, 0o700)
        partial.replace(executable)
    result = subprocess.run([str(executable), str(path)], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(result.stdout)

def submit(root, audio):
    if audio.suffix.lower() != '.mp3' or not audio.is_file() or not 0 < audio.stat().st_size <= MAX_BYTES:
        raise ValueError('Expected nonempty MP3, at most 25 MiB')
    metadata = probe(audio, root)
    duration = float(metadata['format']['duration'])
    if not math.isfinite(duration) or not 0 < duration <= 60:
        raise ValueError('Initial limit is 60 seconds; never truncate narration')
    if not any(s.get('codec_name') == 'mp3' and s.get('codec_type') == 'audio' for s in metadata['streams']):
        raise ValueError('Input is not decoded as MP3')
    ident = uuid.uuid4().hex
    path = root / ident
    path.mkdir(mode=0o700)
    try:
        shutil.copyfile(audio, path / 'source.mp3')
        os.chmod(path / 'source.mp3', 0o600)
        request = dict(id=ident, sourceSha256=digest(path/'source.mp3'), duration=duration, width=1920, height=1080, fps=60)
        write(path/'request.json', request)
        write(path/'status.json', dict(state='queued', id=ident, artisticApproval=False))
    except Exception:
        shutil.rmtree(path)
        raise
    return ident

def verify(path, request, runtime_root=None):
    # Adapter must use the existing acoustic plan gate; reject unresolved flags.
    qa = json.loads((path/'speech-audit.json').read_text())
    if (qa.get('status') != 'technical_pass_pending_visual_review' or qa.get('alignmentSource') != 'acoustic'
            or qa.get('provenance') != 'source-WAV header read' or qa.get('fps') != 60
            or qa.get('errors') or qa.get('reviewFlags')):
        raise ValueError('Acoustic QA missing, estimated, or unresolved')
    evidence = json.loads((path/'moho-evidence.json').read_text())
    if (evidence.get('renderer') != 'Moho Pro 14' or evidence.get('sourceSha256') != request['sourceSha256']
            or evidence.get('disposableProjectVerified') is not True or not evidence.get('rigSha256')):
        raise ValueError('Missing Moho source/rig/disposable-project evidence')
    media = path/'render.mp4'
    if media.is_symlink() or not media.is_file() or media.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ValueError('Invalid or oversized artifact')
    m = probe(media, runtime_root)
    video = [s for s in m['streams'] if s.get('codec_type') == 'video']
    if len(video) != 1 or not any(s.get('codec_type') == 'audio' for s in m['streams']):
        raise ValueError('Expected one video and narration audio')
    v = video[0]
    if (v.get('width'), v.get('height'), v.get('avg_frame_rate')) != (1920, 1080, '60/1'):
        raise ValueError('Artifact must be native 1920x1080 at 60 fps')
    artifact_duration = float(m['format']['duration'])
    source_duration = request['duration']
    if (isinstance(source_duration, bool) or not isinstance(source_duration, (int, float))
            or not math.isfinite(source_duration) or source_duration <= 0
            or not math.isfinite(artifact_duration) or artifact_duration <= 0):
        raise ValueError('Invalid source or artifact duration')
    if abs(artifact_duration - source_duration) > .15:
        raise ValueError('Narration duration changed')
    quality = video_quality(media, runtime_root)
    if (type(quality.get('sampleCount')) is not int or quality['sampleCount'] != 12
            or type(quality.get('distinctFrameCount')) is not int
            or not 2 <= quality['distinctFrameCount'] <= quality['sampleCount']
            or type(quality.get('blackFrameCount')) is not int
            or not 0 <= quality['blackFrameCount'] <= 1):
        raise ValueError('Video is frozen, mostly black, or lacks 12-frame sampling evidence')
    return dict(name='render.mp4', sha256=digest(media), bytes=media.stat().st_size)

def run(root, ident, adapter):
    path = job(root, ident)
    # One worker across all jobs; crash recovery is explicit, never replay writes.
    lock = root/'.worker-lock'
    lock.mkdir()
    try:
        state = json.loads((path/'status.json').read_text())
        if state['state'] != 'queued':
            raise ValueError('Job already attempted; inspect evidence and submit a new job')
        request = json.loads((path/'request.json').read_text())
        if digest(path/'source.mp3') != request['sourceSha256']:
            raise ValueError('Source checksum changed')
        if adapter is None:
            write(path/'status.json', dict(id=ident, state='blocked', reason='Verified Moho adapter not configured', artisticApproval=False))
            return
        argv = json.loads(adapter.read_text())
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv):
            raise ValueError('Administrator adapter must be a JSON argv array')
        write(path/'status.json', dict(id=ident, state='running', artisticApproval=False))
        try:
            # Adapter is trusted host configuration, never supplied by the job.
            # It receives a private job directory; no shell expansion.
            with (path/'worker.log').open('wb') as log:
                subprocess.run(argv + [str(path.resolve())], stdout=log, stderr=log, timeout=1800, check=True)
            artifact = verify(path, request, root)
            write(path/'status.json', dict(id=ident, state='review_required', artifact=artifact, artisticApproval=False, diagnostic=request['duration'] < 30))
        except Exception as exc:
            write(path/'status.json', dict(id=ident, state='failed', reason=type(exc).__name__, artisticApproval=False))
    finally:
        lock.rmdir()

def artifact(root, ident, destination):
    path = job(root, ident)
    status = json.loads((path/'status.json').read_text())
    if status['state'] != 'review_required':
        raise ValueError('No verified artifact')
    source = path/'render.mp4'
    if source.is_symlink() or digest(source) != status['artifact']['sha256']:
        raise ValueError('Artifact checksum changed')
    with destination.open('xb') as out, source.open('rb') as inp:
        shutil.copyfileobj(inp, out)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('submit'); s.add_argument('mp3', type=Path)
    s = sub.add_parser('run'); s.add_argument('id'); s.add_argument('--adapter', type=Path)
    s = sub.add_parser('status'); s.add_argument('id')
    s = sub.add_parser('artifact'); s.add_argument('id'); s.add_argument('destination', type=Path)
    a = p.parse_args()
    a.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        if a.command == 'submit': print(submit(a.root, a.mp3))
        elif a.command == 'run': run(a.root, a.id, a.adapter)
        elif a.command == 'status': print((job(a.root, a.id)/'status.json').read_text())
        else: artifact(a.root, a.id, a.destination)
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(type(exc).__name__ + ': ' + str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
