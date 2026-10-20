"""Portable engine regression tests; synthetic I/O only, no model downloads or paid tools."""
from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

import animate_evan as engine
import evan_mcp as mcp
import launch_evan as launcher
import local_tools


def write_wav(path, seconds=2):
    with wave.open(str(path), 'wb') as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16000)
        target.writeframes(b'\x00\x00' * int(16000 * seconds))


class PipelineTests(unittest.TestCase):
    """Exercise real main/resume decisions while replacing expensive external processes."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.mp3 = self.root / 'original Evan recording.mp3'
        self.mp3.write_bytes(b'synthetic original recording fixture')
        self.config_path = self.root / 'local_tools.json'
        self.config_path.write_text('{}', encoding='utf-8')
        self.out = self.root / 'render'
        self.calls = []
        self.fail_stage = None
        self.partial_frames = False
        self.cfg = {name: name for name in local_tools.REQUIRED}
        self.cfg['sharp'] = 'sharp'
        self.transcript = {'transcription': [
            {'offsets': {'from': 0, 'to': 1000}, 'text': 'Your website matters.'},
            {'offsets': {'from': 1000, 'to': 2000}, 'text': 'A clear message helps.'},
        ]}
        self.cues = {'mouthCues': [{'start': 0, 'end': 2, 'value': 'B'}]}

    def external(self, args, env=None, timeout=180, stage='local step'):
        self.calls.append(stage)
        args = list(args)
        if stage == self.fail_stage:
            raise RuntimeError('Synthetic failure in ' + stage)
        if stage == 'Audio conversion':
            write_wav(Path(args[-1]))
        elif stage == 'Speech transcription':
            (self.out / 'transcript.json').write_text(json.dumps(self.transcript), encoding='utf-8')
        elif stage == 'Mouth timing':
            (self.out / 'mouth.json').write_text(json.dumps(self.cues), encoding='utf-8')
        elif stage == 'Frame rendering':
            start, end = int(args[-2]), int(args[-1])
            if self.partial_frames:
                end = min(end, start + 5)
                self.fail_stage = 'Frame rendering'
            for frame in range(start, end):
                # Syntactically framed JPEG fixture for the engine's resume check.
                (self.out / 'frames' / ('%06d.jpg' % frame)).write_bytes(b'\xff\xd8' + b'x' * 600 + b'\xff\xd9')
            return json.dumps({'nextFrame': end})
        elif stage == 'Video encoding':
            scene = json.loads((self.out / 'scene.json').read_text(encoding='utf-8'))
            Path(args[-1]).write_bytes(b'synthetic MP4:' + json.dumps(scene, sort_keys=True).encode('utf-8'))
        else:
            raise AssertionError('Unexpected external stage ' + stage)
        return ''

    def render(self, resume=False, captions=None):
        callbacks = []
        args = ['animate_evan.py', str(self.mp3), '--output', str(self.out), '--config', str(self.config_path)]
        if resume:
            args.append('--resume')
        if captions:
            args.extend(['--captions', str(captions)])
        # CLI invocations run in separate processes. Reset process-local metric state here.
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', args))
            stack.enter_context(patch.object(engine, 'load_config', return_value=(self.cfg, self.config_path)))
            stack.enter_context(patch.object(engine, 'dependency_errors', return_value=[]))
            stack.enter_context(patch.object(engine, 'renderer_fingerprint', return_value='fixture-renderer'))
            stack.enter_context(patch.object(engine, 'run', side_effect=self.external))
            stack.enter_context(patch.object(engine.atexit, 'register', side_effect=callbacks.append))
            stack.enter_context(patch.object(engine, 'STAGE_SECONDS', {}))
            stack.enter_context(patch.object(engine, 'BASE_ELAPSED_SECONDS', 0.0))
            stack.enter_context(patch.object(engine, 'METRICS_PATH', None))
            stack.enter_context(redirect_stdout(io.StringIO()))
            try:
                engine.main()
            finally:
                for callback in callbacks:
                    if getattr(callback, '__name__', '') == 'close':
                        callback()

    def test_completed_resume_reuses_all_expensive_stages(self):
        self.render()
        self.assertEqual(self.calls, ['Audio conversion', 'Speech transcription', 'Mouth timing', 'Frame rendering', 'Video encoding'])
        self.calls.clear()
        self.render(resume=True)
        self.assertEqual(self.calls, [])

    def test_caption_correction_reuses_audio_transcript_and_mouth_timing(self):
        self.render()
        original_transcript = (self.out / 'transcript.json').read_bytes()
        original_mouth = (self.out / 'mouth.json').read_bytes()
        captions = self.root / 'edited captions.srt'
        captions.write_text('1\n00:00:00,000 --> 00:00:02,000\nCorrected caption.\n', encoding='utf-8')
        self.calls.clear()
        self.render(resume=True, captions=captions)
        self.assertEqual(self.calls, ['Frame rendering', 'Video encoding'])
        self.assertEqual((self.out / 'transcript.json').read_bytes(), original_transcript)
        self.assertEqual((self.out / 'mouth.json').read_bytes(), original_mouth)
        self.assertEqual(json.loads((self.out / 'scene.json').read_text())['captions'][0]['text'], 'Corrected caption.')

    def test_failed_replacement_preserves_previous_video(self):
        self.render()
        previous = (self.out / 'evan.mp4').read_bytes()
        captions = self.out / 'captions.srt'
        captions.write_text('1\n00:00:00,000 --> 00:00:02,000\nNew caption\n', encoding='utf-8')
        self.fail_stage = 'Video encoding'
        with self.assertRaises(RuntimeError):
            self.render(resume=True)
        self.assertEqual((self.out / 'evan.mp4').read_bytes(), previous)
        progress = json.loads((self.out / 'render_progress.json').read_text())
        self.assertNotIn('encoded_caption_sha256', progress)

    def test_interrupted_frame_batch_resumes_at_saved_checkpoint(self):
        self.partial_frames = True
        with self.assertRaises(RuntimeError):
            self.render()
        progress = json.loads((self.out / 'render_progress.json').read_text())
        self.assertEqual(progress['next_frame'], 5)
        prefix = (self.out / 'frames' / '000000.jpg').stat().st_mtime_ns
        self.partial_frames = False
        self.fail_stage = None
        self.calls.clear()
        self.render(resume=True)
        self.assertEqual(self.calls, ['Frame rendering', 'Video encoding'])
        self.assertEqual((self.out / 'frames' / '000000.jpg').stat().st_mtime_ns, prefix)

    def test_truncated_frame_is_rebuilt_before_encoding(self):
        self.render()
        (self.out / 'frames' / '000003.jpg').write_bytes(b'broken')
        self.calls.clear()
        self.render(resume=True)
        self.assertEqual(self.calls, ['Frame rendering', 'Video encoding'])
        self.assertTrue(engine.valid_frame(self.out / 'frames' / '000003.jpg'))

    def test_transcript_dialogue_edit_refreshes_mouth_timing(self):
        self.render()
        transcript = copy.deepcopy(self.transcript)
        transcript['transcription'][0]['text'] = 'A different line of dialogue.'
        (self.out / 'transcript.json').write_text(json.dumps(transcript), encoding='utf-8')
        self.calls.clear()
        self.render(resume=True)
        self.assertEqual(self.calls, ['Mouth timing', 'Frame rendering', 'Video encoding'])
        self.assertIn('A different line', (self.out / 'dialog.txt').read_text())

    def test_changed_audio_never_silently_reuses_old_render(self):
        self.render()
        self.mp3.write_bytes(b'different original recording')
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, 'Continue only'):
            self.render(resume=True)
        self.assertEqual(self.calls, [])

    def test_overlapping_captions_rejected_before_frame_work(self):
        self.render()
        captions = self.out / 'captions.srt'
        captions.write_text('1\n00:00:00,000 --> 00:00:01,500\nOne\n\n2\n00:00:01,000 --> 00:00:02,000\nTwo\n', encoding='utf-8')
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, 'overlap'):
            self.render(resume=True)
        self.assertEqual(self.calls, [])


class PortableBoundaryTests(unittest.TestCase):
    def test_render_folder_lock_blocks_second_process_and_releases(self):
        with tempfile.TemporaryDirectory() as folder:
            lockfile = Path(folder) / '.render.lock'
            held = engine.acquire_render_lock(lockfile)
            script = ('from pathlib import Path; import animate_evan as e; import sys; '
                      'lock=e.acquire_render_lock(Path(sys.argv[1])); lock.close()')
            try:
                child = subprocess.run([sys.executable, '-c', script, str(lockfile)],
                    cwd=engine.HERE, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(child.returncode, 0)
                self.assertIn('already being used', child.stderr)
            finally:
                held.close()
            child = subprocess.run([sys.executable, '-c', script, str(lockfile)],
                cwd=engine.HERE, capture_output=True, text=True, timeout=10)
            self.assertEqual(child.returncode, 0, child.stderr)

    def test_config_resolves_relative_paths_from_config_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = {name: './tools/' + name for name in local_tools.REQUIRED}
            config['sharp'] = 'sharp'
            file = root / 'local_tools.json'
            file.write_text(json.dumps(config), encoding='utf-8')
            result, config_path = local_tools.load_config(file)
            self.assertEqual(config_path, file.resolve())
            self.assertEqual(Path(result['model']), root / 'tools' / 'model')
            self.assertEqual(Path(result['ffmpeg']), root / 'tools' / 'ffmpeg')
            self.assertEqual(result['sharp'], 'sharp')

    def test_launcher_accepts_quoted_unicode_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Evan voice č test.mp3'
            path.write_bytes(b'fixture')
            self.assertEqual(launcher.input_path('"' + str(path) + '"'), path.resolve())

    def test_utf8_bom_windows_line_endings_and_caption_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'captions.srt'
            path.write_bytes(b'\xef\xbb\xbf1\r\n00:00:00,100 --> 00:00:01,900\r\nEvan & Rovor\r\n')
            cues = engine.parse_srt(path, 2)
            engine.write_text_atomic(path, engine.serialize_srt(cues))
            self.assertNotIn(b'\r\n', path.read_bytes())
            self.assertEqual(engine.parse_srt(path, 2), cues)

    def test_truncated_wav_is_not_a_reusable_audio_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'voice.wav'
            write_wav(path)
            self.assertEqual(engine.wav_duration(path), 2)
            path.write_bytes(path.read_bytes()[:-100])
            self.assertIsNone(engine.wav_duration(path))

    def test_node_version_gate_matches_sharp_requirement(self):
        for version, expected in [('v18.20.0', False), ('v20.8.9', False), ('v20.9.0', True), ('v22.0.0', True), ('not-node', False)]:
            result = subprocess.CompletedProcess([], 0, stdout=version)
            with self.subTest(version=version), patch.object(local_tools.subprocess, 'run', return_value=result):
                self.assertEqual(local_tools._node_supports_sharp('node'), expected)


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.outputs = Path(self.temp.name)
        self.folder = self.outputs / 'job'
        self.folder.mkdir()
        self.video = self.folder / 'evan.mp4'
        self.video.write_bytes(b'old video')
        (self.folder / 'render.log').write_text('Created: ' + str(self.video), encoding='utf-8')
        (self.folder / 'render_result.json').write_text(json.dumps({'status': 'completed', 'video_file': 'evan.mp4', 'video_bytes': self.video.stat().st_size}), encoding='utf-8')

    def status(self, running=False):
        with patch.object(mcp, 'OUTPUTS', self.outputs), patch.object(mcp, 'is_running', return_value=running):
            return mcp.call_tool('evan_render_status', {'render_folder': str(self.folder)})

    def test_matching_video_and_report_is_completed(self):
        self.assertTrue(self.status()['completed'])

    def test_running_replacement_does_not_report_old_video_complete(self):
        result = self.status(running=True)
        self.assertFalse(result['completed'])
        self.assertFalse(result['failed'])
        self.assertIsNone(result['render_report'])

    def test_wrong_size_report_is_not_exposed(self):
        self.video.write_bytes(b'new video with different size')
        result = self.status()
        self.assertFalse(result['completed'])
        self.assertIsNone(result['render_report'])

    def test_failed_resume_does_not_claim_previous_success(self):
        logfile = self.folder / 'resume.log'
        logfile.write_text('ERROR: synthetic failed replacement', encoding='utf-8')
        (self.folder / 'mcp_job.json').write_text(json.dumps({'pid': 42, 'log_path': str(logfile)}), encoding='utf-8')
        self.assertFalse(self.status()['completed'])

    def test_outside_log_path_is_ignored(self):
        private = self.outputs / 'outside.log'
        private.write_text('outside content', encoding='utf-8')
        (self.folder / 'mcp_job.json').write_text(json.dumps({'log_path': str(private)}), encoding='utf-8')
        result = self.status()
        self.assertNotIn('outside content', result['log_tail'])


if __name__ == '__main__':
    unittest.main()
