"""Convert one Evan MP3 to a 2D animated MP4, fully offline.

Runs local Whisper, Rhubarb, Sharp/Node, FFmpeg. Supports --resume after a stopped
stage and --plan for manually specifying timed original illustrations. No APIs.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import wave

from scene_planner import generate_plan, validate_plan

HERE = Path(__file__).resolve().parent


def run(args, env=None):
    try:
        result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                                timeout=1800, env=env, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('A local step timed out. Re-run with --resume; '
                           'if it repeats, the tool may need a faster model or shorter audio.') from exc
    if result.returncode:
        raise RuntimeError('Local tool failed: ' + ' '.join(str(a) for a in args[:2]) +
                           '\n' + result.stderr[-2000:])
    return result.stdout


def read_json(path):
    try:
        return json.loads(path.read_text()) if path.is_file() else None
    except (ValueError, OSError):
        return None


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


def frame_command(config, character, scene, frames, start, total):
    """Choose an opt-in backend without importing painted build dependencies."""
    if character == 'painted':
        return [config.get('painted_python', sys.executable), HERE / 'render_painted_scene.py',
                scene, frames, start, total]
    return [config['node'], HERE / 'render_frames.cjs', scene, frames, start, total]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mp3', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--config', type=Path, default=HERE / 'local_tools.json')
    parser.add_argument('--plan', type=Path, help='Optional hand-written JSON array of scenes')
    parser.add_argument('--resume', action='store_true', help='Continue stages in an existing output directory')
    parser.add_argument('--character', choices=('calibrated','reference','vector','painted'), default='calibrated', help='V4 calibrated sprites (default), V3 reference, V2 vector, or experimental painted mesh rig')
    parser.add_argument('--mouth-mode', choices=('subtle','detailed','still'), default='subtle', help='Subtle lips (default), detailed phonemes or no lip swapping')
    args = parser.parse_args()
    if not args.mp3.is_file() or args.mp3.suffix.lower() != '.mp3':
        parser.error('Please provide an existing MP3 recording.')
    if args.plan and not args.plan.is_file():
        parser.error('The scene-plan JSON file was not found.')
    audio = args.mp3.resolve()
    fingerprint = {'mp3': str(audio), 'size': audio.stat().st_size,
                   'modified_ns': audio.stat().st_mtime_ns,
                   'plan': str(args.plan.resolve()) if args.plan else None, 'character': args.character,
                   'mouth_mode': args.mouth_mode}
    args.output.mkdir(parents=True, exist_ok=args.resume)
    out = args.output.resolve()
    state = out / 'render_request.json'
    if args.resume:
        previous = read_json(state)
        if previous != fingerprint:
            raise ValueError('Resume requires an existing run with the same audio and scene plan.')
    else:
        state.write_text(json.dumps(fingerprint, indent=2))
    cfg = json.loads(args.config.read_text())
    wav = out / 'narration.wav'
    if not wav.is_file():
        print('Reading the recording locally...', flush=True)
        run([cfg['ffmpeg'], '-v', 'error', '-i', audio, '-ar', '16000', '-ac', '1',
             '-c:a', 'pcm_s16le', wav])
    with wave.open(str(wav)) as voice:
        duration = voice.getnframes() / voice.getframerate()
    if duration > 900:
        raise ValueError('Recordings longer than 15 minutes must be split into chapters.')
    if duration > 60:
        print(f'Long-form rendering: {duration:.0f} seconds of narration. This may take considerable time and disk space.', flush=True)
    transcript_path = out / 'transcript.json'
    transcript = read_json(transcript_path)
    if not transcript or not transcript.get('transcription'):
        print('Transcribing speech locally...', flush=True)
        run([cfg['whisper'], '-m', cfg['model'], '-f', wav, '-oj', '-of', out / 'transcript'])
        transcript = read_json(transcript_path)
        if not transcript or not transcript.get('transcription'):
            raise RuntimeError('Whisper did not produce usable segments.')
    dialog = out / 'dialog.txt'
    if not dialog.is_file():
        dialog.write_text(' '.join(r['text'].strip() for r in transcript['transcription']))
    mouth_path = out / 'mouth.json'
    cues = read_json(mouth_path)
    if not cues or not cues.get('mouthCues'):
        print('Timing mouth shapes locally...', flush=True)
        run([cfg['rhubarb'], '-f', 'json', '-o', mouth_path, '-d', dialog, wav])
        cues = read_json(mouth_path)
        if not cues or not cues.get('mouthCues'):
            raise RuntimeError('Rhubarb did not produce lip-sync timings.')
    scene_path = out / 'scene.json'
    scene = read_json(scene_path)
    if not scene:
        provided_plan = json.loads(args.plan.read_text()) if args.plan else None
        scene = make_scene(transcript, cues, duration, provided_plan)
        scene['characterStyle'] = args.character
        scene['mouthMode'] = args.mouth_mode
        scene_path.write_text(json.dumps(scene, indent=2))
    current_scene=read_json(scene_path)
    if current_scene.get('duration') != duration:
        raise ValueError('Scene metadata does not match the audio duration.')
    if current_scene.get('characterStyle') != args.character or current_scene.get('mouthMode','subtle') != args.mouth_mode:
        raise ValueError('Saved scene character/mouth settings differ; create a new output directory.')
    total = math.ceil(duration * 24)
    frames = out / 'frames'
    frames.mkdir(exist_ok=True)
    # Resume at the first missing frame. Preserve all completed original frames.
    start = next((i for i in range(total) if not valid_frame(frames / f'{i:06d}.jpg')), total)
    print(f'Animating Evan: {start}/{total} frames already present...', flush=True)
    env = dict(os.environ, EVAN_SHARP=cfg['sharp'])
    if args.character == 'painted' and cfg.get('painted_packages'):
        env['PYTHONPATH'] = str(cfg['painted_packages']) + os.pathsep + env.get('PYTHONPATH', '')
    while start < total:
        raw = run(frame_command(cfg, args.character, scene_path, frames, start, total), env)
        result = json.loads(raw)
        next_frame = result['nextFrame']
        if next_frame <= start:
            raise RuntimeError('The renderer made no progress. Re-run with --resume.')
        start = next_frame
    video = out / 'evan.mp4'
    if not video.is_file() or video.stat().st_size == 0:
        print('Encoding the final video...', flush=True)
        staging = out / 'evan.partial.mp4'
        run([cfg['ffmpeg'], '-y', '-v', 'error', '-framerate', '24', '-i', frames / '%06d.jpg',
             '-i', audio, '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264',
             '-preset', 'ultrafast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac',
             '-t', duration, '-movflags', '+faststart', staging])
        staging.replace(video)
    print('Created: ' + str(video))


if __name__ == '__main__':
    main()
