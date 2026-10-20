"""Convert one Evan MP3 to a 2D animated MP4, fully offline.

Runs local Whisper, Rhubarb, Sharp/Node, FFmpeg. Supports --resume after a stopped
stage and --plan for manually specifying timed original illustrations. No APIs.
"""
import argparse
import atexit
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import wave

from local_tools import default_config_path, dependency_errors, load_config
from scene_planner import generate_plan, validate_plan

HERE = Path(__file__).resolve().parent
SRT_TIME = re.compile(r'^(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})$')
SRT_CUE = re.compile(r'^(\d{2,}:\d{2}:\d{2}[,.]\d{3})\s+-->\s+'
                     r'(\d{2,}:\d{2}:\d{2}[,.]\d{3})(?:\s+.*)?$')


def read_engine_version():
    try:
        version = json.loads((HERE / 'package.json').read_text(encoding='utf-8')).get('version')
        return version if isinstance(version, str) and version else 'unknown'
    except (OSError, ValueError):
        return 'unknown'


ENGINE_VERSION = read_engine_version()
STAGE_SECONDS = {}
RUN_STARTED = time.monotonic()
BASE_ELAPSED_SECONDS = 0.0
METRICS_PATH = None


def save_render_metrics():
    if METRICS_PATH is None:
        return
    elapsed = BASE_ELAPSED_SECONDS + max(0.0, time.monotonic() - RUN_STARTED)
    try:
        write_json_atomic(METRICS_PATH, {
            'stage_seconds': STAGE_SECONDS,
            'elapsed_seconds': elapsed,
        })
    except OSError:
        # Diagnostics must never make an otherwise usable render fail.
        pass


def run(args, env=None, timeout=180, stage='local step'):
    started = time.monotonic()
    try:
        result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout,
                                env=env, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'{stage.capitalize()} exceeded {timeout} seconds. Re-run with --resume; '
                           'completed stages and frames will be reused.') from exc
    finally:
        STAGE_SECONDS[stage] = STAGE_SECONDS.get(stage, 0.0) + (time.monotonic() - started)
        save_render_metrics()
    if result.returncode:
        raise RuntimeError(stage.capitalize() + ' failed: ' + ' '.join(str(a) for a in args[:2]) +
                           '\n' + result.stderr[-2000:])
    return result.stdout


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else None
    except (ValueError, OSError):
        return None


def write_json_atomic(path, value):
    staging = path.with_name(path.name + '.writing')
    staging.write_text(json.dumps(value, indent=2), encoding='utf-8')
    staging.replace(path)


def write_text_atomic(path, value):
    staging = path.with_name(path.name + '.writing')
    with staging.open('w', encoding='utf-8', newline='\n') as target:
        target.write(value)
    staging.replace(path)


def acquire_render_lock(path):
    lock = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b' ')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as error:
        lock.close()
        raise ValueError('This render folder is already being used by another engine process.') from error
    lock.seek(0)
    lock.truncate()
    lock.write(str(os.getpid()).encode('ascii'))
    lock.flush()
    return lock


def parse_srt_time(value):
    match = SRT_TIME.fullmatch(value.strip())
    if not match:
        raise ValueError('Use SRT timestamps such as 00:00:01,250 --> 00:00:02,500.')
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    if minutes >= 60 or seconds >= 60:
        raise ValueError('Subtitle minutes and seconds must be between 00 and 59.')
    return hours * 3600 + minutes * 60 + seconds + millis / 1000


def parse_srt(path, duration):
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('The captions file is too large to safely render.')
    source = path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n[ \t]*\n', source.strip()) if source.strip() else []
    if not blocks or len(blocks) > 2000:
        raise ValueError('The captions file must contain between 1 and 2,000 subtitle cues.')
    captions = []
    for block in blocks:
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if len(lines) < 2:
            raise ValueError('Each SRT cue needs a timestamp line and caption text.')
        match = SRT_CUE.fullmatch(lines[0].strip())
        if not match:
            raise ValueError('A subtitle timestamp is invalid. Expected HH:MM:SS,mmm --> HH:MM:SS,mmm.')
        start, end = (parse_srt_time(value) for value in match.groups())
        text = ' '.join(line.strip() for line in lines[1:] if line.strip())
        if not text or len(text) > 10000 or any(ord(char) < 32 and char not in '\t' for char in text):
            raise ValueError('Subtitle text must contain 1 to 10,000 printable characters.')
        if start < 0 or start >= duration or end <= start or end > duration + 0.05:
            raise ValueError('Every subtitle must start before the audio ends and have a positive duration.')
        captions.append({'start': start, 'end': min(end, duration), 'text': text})
    if any(captions[index]['start'] > captions[index + 1]['start']
           for index in range(len(captions) - 1)):
        raise ValueError('Subtitle cues must be ordered by start time.')
    return captions


def format_srt_time(value):
    millis = max(0, int(round(value * 1000)))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    seconds, millis = divmod(millis, 1000)
    return f'{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}'


def serialize_srt(captions):
    return '\n\n'.join(
        f"{index}\n{format_srt_time(cue['start'])} --> {format_srt_time(cue['end'])}\n{cue['text']}"
        for index, cue in enumerate(captions, start=1)
    ) + '\n'


def transcript_captions(transcript, duration):
    rows = []
    for row in transcript['transcription']:
        start = max(0, row['offsets']['from'] / 1000)
        end = min(duration, row['offsets']['to'] / 1000)
        printable = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', row['text'])
        text = ' '.join(printable.split())
        if text and start < end and start < duration:
            rows.append({'start': start, 'end': end, 'text': text})
    rows.sort(key=lambda cue: (cue['start'], cue['end']))
    captions = []
    for index, cue in enumerate(rows):
        if index + 1 < len(rows):
            cue['end'] = min(cue['end'], rows[index + 1]['start'])
        if cue['start'] < cue['end']:
            captions.append(cue)
    if not captions:
        raise ValueError('No usable subtitle cues were found in the transcript.')
    return captions


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def renderer_fingerprint():
    root = HERE.parent
    sources = [HERE / name for name in (
        'animate_evan.py', 'local_tools.py', 'scene_planner.py', 'package.json',
        'render_frames.cjs', 'evan_puppet.cjs', 'evan_reference.cjs',
        'caption_utils.cjs', 'scene_graphics.cjs')]
    assets = root / 'evan-character' / 'v3-assets'
    if assets.is_dir():
        sources.extend(path for path in assets.rglob('*') if path.is_file())
    digest = hashlib.sha256()
    for path in sorted(sources, key=lambda item: str(item.relative_to(root)).casefold()):
        digest.update(str(path.relative_to(root)).replace(os.sep, '/').encode('utf-8') + b'\0')
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
    return digest.hexdigest()


def file_stamp(value):
    path = Path(value)
    try:
        metadata = path.stat()
        return {'path': str(path.resolve()), 'size': metadata.st_size,
                'modified_ns': metadata.st_mtime_ns}
    except OSError:
        return {'path': str(path)}


def same_request(previous, current):
    return isinstance(previous, dict) and previous == current


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        return False


def valid_transcript(value):
    rows = value.get('transcription') if isinstance(value, dict) else None
    if not isinstance(rows, list) or not rows:
        return False
    for row in rows:
        offsets = row.get('offsets') if isinstance(row, dict) else None
        if (not isinstance(offsets, dict) or not isinstance(row.get('text'), str) or
                not finite_number(offsets.get('from')) or
                not finite_number(offsets.get('to')) or
                offsets['from'] < 0 or offsets['to'] <= offsets['from']):
            return False
    return any(row['text'].strip() for row in rows)


def valid_segments(rows, duration):
    if not isinstance(rows, list) or not rows:
        return False
    return all(
        isinstance(row, dict) and isinstance(row.get('text'), str) and row['text'].strip() and
        finite_number(row.get('start')) and finite_number(row.get('end')) and
        0 <= row['start'] < row['end'] <= duration
        for row in rows
    )


def valid_gestures(rows, duration):
    if not isinstance(rows, list):
        return False
    kinds = {'outro', 'present', 'pinch', 'emphasis', 'point'}
    return all(
        isinstance(row, dict) and isinstance(row.get('kind'), str) and row['kind'] in kinds and
        finite_number(row.get('start')) and finite_number(row.get('end')) and
        0 <= row['start'] < row['end'] <= duration
        for row in rows
    )


def valid_cues(value):
    rows = value.get('mouthCues') if isinstance(value, dict) else None
    if not isinstance(rows, list) or not rows:
        return False
    return all(
        isinstance(row, dict) and
        finite_number(row.get('start')) and finite_number(row.get('end')) and
        0 <= row['start'] < row['end'] and
        isinstance(row.get('value'), str) and
        row['value'] in {'X', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'}
        for row in rows
    )


def valid_frame(path):
    # A killed renderer can leave a truncated JPEG. Ignore it on resume.
    try:
        if path.stat().st_size < 512:
            return False
        with path.open('rb') as frame:
            start = frame.read(2)
            frame.seek(-2, 2)
            end = frame.read(2)
        return start == b'\xff\xd8' and end == b'\xff\xd9'
    except OSError:
        return False


def wav_duration(path):
    try:
        with wave.open(str(path), 'rb') as voice:
            sample_count = voice.getnframes()
            sample_rate = voice.getframerate()
            channels = voice.getnchannels()
            sample_width = voice.getsampwidth()
            if sample_count <= 0 or sample_rate <= 0 or channels <= 0 or sample_width <= 0:
                return None
            duration = sample_count / sample_rate
            if not math.isfinite(duration) or duration <= 0:
                return None
            if duration > 61:
                return duration
            expected_bytes = sample_count * channels * sample_width
            if len(voice.readframes(sample_count)) != expected_bytes:
                return None
        return duration if math.isfinite(duration) and duration > 0 else None
    except (EOFError, OSError, ValueError, wave.Error):
        return None


def make_scene(transcript, cues, duration, manual_plan=None):
    segments = []
    for row in transcript['transcription']:
        start = row['offsets']['from'] / 1000
        end = min(duration, row['offsets']['to'] / 1000)
        text = row['text'].strip()
        if text and start < end:
            segments.append(dict(start=start, end=end, text=text))
    scenes, gestures = generate_plan(segments, duration)
    if manual_plan is not None:
        scenes = validate_plan(manual_plan, duration)
    return dict(duration=duration, segments=segments, mouthCues=cues['mouthCues'],
                scenePlan=scenes, gestures=gestures)


def main():
    global BASE_ELAPSED_SECONDS, METRICS_PATH, RUN_STARTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mp3', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=default_config_path())
    parser.add_argument('--plan', type=Path, help='Optional hand-written JSON array of scenes')
    parser.add_argument('--captions', type=Path,
                        help='Optional SRT file; defaults to captions.srt in the output folder')
    parser.add_argument('--resume', action='store_true', help='Continue stages in an existing output directory')
    parser.add_argument('--character', choices=('reference','vector'), default='reference', help='Character artwork mode (reference sprites or V2 vector rig)')
    args = parser.parse_args()
    if not args.mp3.is_file() or args.mp3.suffix.lower() != '.mp3':
        parser.error('Please provide an existing MP3 recording.')
    if args.plan and not args.plan.is_file():
        parser.error('The scene-plan JSON file was not found.')
    if args.captions and not args.captions.is_file():
        parser.error('The SRT captions file was not found.')
    try:
        cfg, config_path = load_config(args.config)
    except ValueError as error:
        parser.error(str(error))
    missing = dependency_errors(cfg)
    if missing:
        parser.error('Missing local tools: ' + ', '.join(missing))
    audio = args.mp3.resolve()
    renderer_sha = renderer_fingerprint()
    fingerprint = {'fingerprint_version': 4, 'mp3': str(audio), 'size': audio.stat().st_size,
                   'modified_ns': audio.stat().st_mtime_ns,
                   'input_sha256': sha256_file(audio),
                   'plan': str(args.plan.resolve()) if args.plan else None,
                   'plan_sha256': sha256_file(args.plan) if args.plan else None,
                   'config_path': str(config_path), 'config_sha256': sha256_file(config_path),
                   'character': args.character, 'engine_version': ENGINE_VERSION,
                   'renderer_sha256': renderer_sha,
                   'tool_files': {name: file_stamp(cfg[name])
                                  for name in ('ffmpeg', 'whisper', 'model', 'rhubarb', 'node')}}
    args.output.mkdir(parents=True, exist_ok=args.resume)
    out = args.output.resolve()
    lock = acquire_render_lock(out / '.render.lock')
    atexit.register(lock.close)
    state = out / 'render_request.json'
    if args.resume:
        previous = read_json(state)
        if not same_request(previous, fingerprint):
            raise ValueError('Continue only when the audio, scene plan, character mode, tool config, and engine version match.')
    else:
        write_json_atomic(state, fingerprint)
    metrics_path = out / 'render_metrics.json'
    previous_metrics = read_json(metrics_path) if args.resume else None
    stage_seconds = previous_metrics.get('stage_seconds') if isinstance(previous_metrics, dict) else None
    if isinstance(stage_seconds, dict):
        STAGE_SECONDS.update({
            name: float(seconds) for name, seconds in stage_seconds.items()
            if isinstance(name, str) and isinstance(seconds, (int, float)) and
            finite_number(seconds) and seconds >= 0
        })
    elapsed_seconds = previous_metrics.get('elapsed_seconds', 0) if isinstance(previous_metrics, dict) else 0
    if finite_number(elapsed_seconds) and elapsed_seconds >= 0:
        BASE_ELAPSED_SECONDS = float(elapsed_seconds)
    METRICS_PATH = metrics_path
    RUN_STARTED = time.monotonic()
    atexit.register(save_render_metrics)
    save_render_metrics()
    wav = out / 'narration.wav'
    duration = wav_duration(wav)
    if duration is None:
        print('Reading the recording locally...', flush=True)
        staging_wav = out / 'narration.partial.wav'
        if staging_wav.exists():
            staging_wav.unlink()
        run([cfg['ffmpeg'], '-y', '-v', 'error', '-i', audio, '-t', '61', '-ar', '16000', '-ac', '1',
             '-c:a', 'pcm_s16le', staging_wav], timeout=120, stage='Audio conversion')
        duration = wav_duration(staging_wav)
        if duration is None:
            raise RuntimeError('FFmpeg did not produce a complete, usable audio file.')
        staging_wav.replace(wav)
    if duration > 60:
        raise ValueError('This prototype supports recordings up to 60 seconds.')
    transcript_path = out / 'transcript.json'
    transcript = read_json(transcript_path)
    if not valid_transcript(transcript):
        print('Transcribing speech locally...', flush=True)
        run([cfg['whisper'], '-m', cfg['model'], '-f', wav, '-oj', '-of', out / 'transcript'],
            timeout=300, stage='Speech transcription')
        transcript = read_json(transcript_path)
        if not valid_transcript(transcript):
            raise RuntimeError('Whisper did not produce usable segments.')
    dialog = out / 'dialog.txt'
    dialog_text = ' '.join(row['text'].strip() for row in transcript['transcription'])
    try:
        existing_dialog = dialog.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        existing_dialog = None
    dialog_changed = existing_dialog != dialog_text
    if dialog_changed:
        write_text_atomic(dialog, dialog_text)
    mouth_path = out / 'mouth.json'
    cues = None if dialog_changed else read_json(mouth_path)
    if not valid_cues(cues):
        print('Timing mouth shapes locally...', flush=True)
        run([cfg['rhubarb'], '-f', 'json', '-o', mouth_path, '-d', dialog, wav],
            timeout=120, stage='Mouth timing')
        cues = read_json(mouth_path)
        if not valid_cues(cues):
            raise RuntimeError('Rhubarb did not produce lip-sync timings.')
    scene_path = out / 'scene.json'
    transcript_hash = sha256_file(transcript_path)
    mouth_hash = sha256_file(mouth_path)
    scene = read_json(scene_path)
    if (not isinstance(scene, dict) or not scene or
            scene.get('transcript_sha256') != transcript_hash or
            scene.get('mouth_sha256') != mouth_hash):
        provided_plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else None
        scene = make_scene(transcript, cues, duration, provided_plan)
        scene['characterStyle'] = args.character
        scene['transcript_sha256'] = transcript_hash
        scene['mouth_sha256'] = mouth_hash
        write_json_atomic(scene_path, scene)
    if scene.get('duration') != duration:
        raise ValueError('Scene metadata does not match the audio duration.')
    scene['scenePlan'] = validate_plan(scene.get('scenePlan'), duration)
    if (scene.get('characterStyle') not in ('reference', 'vector') or
            scene.get('characterStyle') != args.character or
            not valid_segments(scene.get('segments'), duration) or
            not valid_gestures(scene.get('gestures'), duration) or
            not valid_cues({'mouthCues': scene.get('mouthCues')})):
        raise ValueError('Saved scene data is incomplete. Remove scene.json and resume to rebuild it.')
    captions_path = out / 'captions.srt'
    captions_source = args.captions.resolve() if args.captions else captions_path
    if captions_source.is_file():
        captions = parse_srt(captions_source, duration)
    else:
        captions = transcript_captions(transcript, duration)
    if captions_source.resolve() != captions_path.resolve() or not captions_path.exists():
        write_text_atomic(captions_path, serialize_srt(captions))
    scene['captions'] = captions
    write_json_atomic(scene_path, scene)
    total = math.ceil(duration * 24)
    frames = out / 'frames'
    frames.mkdir(exist_ok=True)
    caption_hash = hashlib.sha256(serialize_srt(captions).encode('utf-8')).hexdigest()
    scene_hash = hashlib.sha256(json.dumps(scene, sort_keys=True, separators=(',', ':'),
                                           ensure_ascii=False).encode('utf-8')).hexdigest()
    progress_path = out / 'render_progress.json'
    progress = read_json(progress_path)
    progress_matches = (isinstance(progress, dict) and
                        progress.get('caption_sha256') == caption_hash and
                        progress.get('scene_sha256') == scene_hash and
                        progress.get('engine_version') == ENGINE_VERSION and
                        isinstance(progress.get('frame_count'), int) and
                        not isinstance(progress.get('frame_count'), bool) and
                        progress['frame_count'] == total and
                        isinstance(progress.get('next_frame'), int) and
                        not isinstance(progress.get('next_frame'), bool) and
                        0 <= progress['next_frame'] <= total)
    if not progress_matches:
        progress = {'caption_sha256': caption_hash, 'scene_sha256': scene_hash,
                    'engine_version': ENGINE_VERSION,
                    'frame_count': total, 'next_frame': 0}
    start = progress['next_frame']
    # If a previously completed JPEG is missing or truncated, rebuild from that frame.
    for frame_number in range(start):
        if not valid_frame(frames / f'{frame_number:06d}.jpg'):
            start = frame_number
            break
    if start < total:
        progress.pop('encoded_caption_sha256', None)
    progress['next_frame'] = start
    write_json_atomic(progress_path, progress)
    print(f'Animating Evan: {start}/{total} frames already present...', flush=True)
    env = dict(os.environ, EVAN_SHARP=cfg['sharp'])
    while start < total:
        raw = run([cfg['node'], HERE / 'render_frames.cjs', scene_path, frames, start, total],
                  env, timeout=35, stage='Frame rendering')
        result = json.loads(raw)
        next_frame = result.get('nextFrame') if isinstance(result, dict) else None
        if isinstance(next_frame, bool) or not isinstance(next_frame, int) or not start < next_frame <= total:
            raise RuntimeError('The renderer returned an invalid frame range. Re-run with --resume.')
        start = next_frame
        progress['next_frame'] = start
        write_json_atomic(progress_path, progress)
    video = out / 'evan.mp4'
    video_ready = video.is_file() and video.stat().st_size > 0
    if not video_ready or progress.get('encoded_caption_sha256') != caption_hash:
        print('Encoding the final video...', flush=True)
        staging = out / 'evan.partial.mp4'
        run([cfg['ffmpeg'], '-y', '-v', 'error', '-framerate', '24', '-i', frames / '%06d.jpg',
             '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264',
             '-preset', 'ultrafast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
             '-t', duration, '-movflags', '+faststart', staging], timeout=300, stage='Video encoding')
        staging.replace(video)
        progress['encoded_caption_sha256'] = caption_hash
        write_json_atomic(progress_path, progress)
    save_render_metrics()
    write_json_atomic(out / 'render_result.json', {
        'status': 'completed',
        'completed_at': datetime.now(timezone.utc).isoformat(),
        'engine_version': ENGINE_VERSION,
        'renderer_sha256': renderer_sha,
        'audio_file': audio.name,
        'audio_sha256': fingerprint['input_sha256'],
        'duration_seconds': duration,
        'frame_rate': 24,
        'frame_count': total,
        'resolution': '720x1280',
        'character_style': args.character,
        'caption_count': len(captions),
        'caption_sha256': caption_hash,
        'scene_sha256': scene_hash,
        'video_file': video.name,
        'video_bytes': video.stat().st_size,
        'stage_seconds': {name: round(seconds, 2) for name, seconds in STAGE_SECONDS.items()},
        'elapsed_seconds': round(BASE_ELAPSED_SECONDS + time.monotonic() - RUN_STARTED, 2),
    })
    print('Created: ' + str(video))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nRender stopped.', file=sys.stderr)
        sys.exit(130)
    except (EOFError, OSError, RuntimeError, ValueError, wave.Error) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)

