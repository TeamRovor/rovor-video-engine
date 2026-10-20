import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('jobs', Path(__file__).resolve().parents[1]/'tools/render_jobs.py')
j = importlib.util.module_from_spec(spec); spec.loader.exec_module(j)

class Jobs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.audio = self.root/'input.mp3'; self.audio.write_bytes(b'synthetic')
    def submit(self):
        with patch.object(j, 'probe', return_value={'format':{'duration':'31'}, 'streams':[{'codec_type':'audio','codec_name':'mp3'}]}):
            return j.submit(self.root, self.audio)
    def test_missing_adapter_blocks_without_render(self):
        ident = self.submit(); j.run(self.root, ident, None)
        self.assertEqual(json.loads((self.root/ident/'status.json').read_text())['state'], 'blocked')
        with self.assertRaises(ValueError): j.artifact(self.root, ident, self.root/'out.mp4')
        with self.assertRaises(ValueError): j.run(self.root, ident, None)
    def test_reject_traversal(self):
        with self.assertRaises(ValueError): j.job(self.root, '../outside')
    def test_source_mutation(self):
        ident = self.submit(); (self.root/ident/'source.mp3').write_bytes(b'changed')
        with self.assertRaises(ValueError): j.run(self.root, ident, None)
        self.assertFalse((self.root/'.worker-lock').exists())
    def test_serial_worker(self):
        ident = self.submit(); (self.root/'.worker-lock').mkdir()
        with self.assertRaises(FileExistsError): j.run(self.root, ident, None)
    def test_duration_limit(self):
        with patch.object(j, 'probe', return_value={'format':{'duration':'61'},'streams':[]}):
            with self.assertRaises(ValueError): j.submit(self.root, self.audio)
    def test_mock_transport_roundtrip_and_tamper(self):
        ident = self.submit(); path = self.root/ident
        config = self.root/'adapter.json'; config.write_text('["trusted-adapter"]')
        def adapter(*args, **kwargs): (path/'render.mp4').write_bytes(b'mock video')
        with patch.object(j.subprocess, 'run', side_effect=adapter), patch.object(j, 'verify', side_effect=lambda p,r,*args:dict(name='render.mp4',sha256=j.digest(p/'render.mp4'),bytes=10)):
            j.run(self.root, ident, config)
        j.artifact(self.root, ident, self.root/'out.mp4')
        self.assertEqual((self.root/'out.mp4').read_bytes(), b'mock video')
        (path/'render.mp4').write_bytes(b'tampered')
        with self.assertRaises(ValueError): j.artifact(self.root, ident, self.root/'other.mp4')
    def test_estimated_speech_fails_before_media_probe(self):
        ident = self.submit(); path = self.root/ident
        (path/'speech-audit.json').write_text('{"status":"review_required"}')
        with patch.object(j, 'probe') as probe:
            with self.assertRaises(ValueError): j.verify(path, {})
            probe.assert_not_called()

if __name__ == '__main__': unittest.main()
