"""Convert one Evan MP3 to a 2D animated MP4, fully offline.

Runs local Whisper, Rhubarb, Sharp/Node, FFmpeg. Supports --resume after a stopped
stage and --plan for manually specifying timed original illustrations. No APIs.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave

from local_tools import default_config_path, dependency_errors, load_config
from scene_planner import generate_plan, validate_plan

HERE = Path(__file__).resolve().parent


def read_engine_version():
    try:
        version = json.loads((HERE / 'package.json').read_text(encoding='utf-8')).get('version')
        return version if isinstance(version, str) and version else 'unknown'
    except (OSError, ValueError):
        return 'unknown'


ENGINE_VERSION = read_engine_version()


def run(args, env=None, timeout=180, stage='local step'):
    try:
        result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout,
                                env=env, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'{stage.capitalize()} exceeded {timeout} seconds. Re-run with --resume; '
                           'completed stages and frames will be reused.') from exc
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


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


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
    return True


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
        if start < end:
            segments.append(dict(start=start, end=end, text=row['text'].strip()))
    scenes, gestures = generate_plan(segments, duration)
    if manual_plan is not None:
        scenes = validate_plan(manual_plan, duration)
    return dict(duration=duration, segments=segments, mouthCues=cues['mouthCues'],
                scenePlan=scenes, gestures=gestures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mp3', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=default_config_path())
    parser.add_argument('--plan', type=Path, help='Optional hand-written JSON array of scenes')
    parser.add_argument('--resume', action='store_true', help='Continue stages in an existing output directory')
    parser.add_argument('--character', choices=('reference','vector'), default='reference', help='Character artwork mode (reference sprites or V2 vector rig)')
    args = parser.parse_args()
    if not args.mp3.is_file() or args.mp3.suffix.lower() != '.mp3':
        parser.error('Please provide an existing MP3 recording.')
    if args.plan and not args.plan.is_file():
        parser.error('The scene-plan JSON file was not found.')
    try:
        cfg, config_path = load_config(args.config)
    except ValueError as error:
        parser.error(str(error))
    missing = dependency_errors(cfg)
    if missing:
        parser.error('Missing local tools: ' + ', '.join(missing))
    audio = args.mp3.resolve()
    fingerprint = {'fingerprint_version': 3, 'mp3': str(audio), 'size': audio.stat().st_size,
                   'modified_ns': audio.stat().st_mtime_ns,
                   'input_sha256': sha256_file(audio),
                   'plan': str(args.plan.resolve()) if args.plan else None,
                   'plan_sha256': sha256_file(args.plan) if args.plan else None,
                   'config_path': str(config_path), 'config_sha256': sha256_file(config_path),
                   'character': args.character, 'engine_version': ENGINE_VERSION}
    args.output.mkdir(parents=True, exist_ok=args.resume)
    out = args.output.resolve()
    state = out / 'render_request.json'
    if args.resume:
        previous = read_json(state)
        if not same_request(previous, fingerprint):
            raise ValueError('Continue only when the audio, scene plan, character mode, tool config, and engine version match.')
    else:
        write_json_atomic(state, fingerprint)
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
    if not dialog.is_file():
        dialog.write_text(' '.join(r['text'].strip() for r in transcript['transcription']), encoding='utf-8')
    mouth_path = out / 'mouth.json'
    cues = read_json(mouth_path)
    if not valid_cues(cues):
        print('Timing mouth shapes locally...', flush=True)
        run([cfg['rhubarb'], '-f', 'json', '-o', mouth_path, '-d', dialog, wav],
            timeout=120, stage='Mouth timing')
        cues = read_json(mouth_path)
        if not valid_cues(cues):
            raise RuntimeError('Rhubarb did not produce lip-sync timings.')
    scene_path = out / 'scene.json'
    scene = read_json(scene_path)
    if not scene:
        provided_plan = json.loads(args.plan.read_text(encoding='utf-8')) if args.plan else None
        scene = make_scene(transcript, cues, duration, provided_plan)
        scene['characterStyle'] = args.character
        write_json_atomic(scene_path, scene)
    if not isinstance(scene, dict) or scene.get('duration') != duration:
        raise ValueError('Scene metadata does not match the audio duration.')
    scene['scenePlan'] = validate_plan(scene.get('scenePlan'), duration)
    if not isinstance(scene.get('segments'), list) or not valid_cues({'mouthCues': scene.get('mouthCues')}):
        raise ValueError('Saved scene data is incomplete. Remove scene.json and resume to rebuild it.')
    total = math.ceil(duration * 24)
    frames = out / 'frames'
    frames.mkdir(exist_ok=True)
    # Resume at the first missing frame. Preserve all completed original frames.
    start = next((i for i in range(total) if not valid_frame(frames / f'{i:06d}.jpg')), total)
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
    video = out / 'evan.mp4'
    if not video.is_file() or video.stat().st_size == 0:
        print('Encoding the final video...', flush=True)
        staging = out / 'evan.partial.mp4'
        run([cfg['ffmpeg'], '-y', '-v', 'error', '-framerate', '24', '-i', frames / '%06d.jpg',
             '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264',
             '-preset', 'ultrafast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
             '-t', duration, '-movflags', '+faststart', staging], timeout=300, stage='Video encoding')
        staging.replace(video)
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

