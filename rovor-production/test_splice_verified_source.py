import hashlib,unittest
from pathlib import Path
from unittest.mock import patch
from tempfile import TemporaryDirectory
from splice_verified_source import preflight,splice
class SpliceContract(unittest.TestCase):
  def test_preflight_valid(self):
    with TemporaryDirectory() as d:
      voice=Path(d)/'voice';voice.write_bytes(b'original')
      def fake(p):return {'width':1920,'height':1080,'fps':'60/1','frames':9377 if p=='old' else 360}
      with patch('splice_verified_source.metadata',side_effect=fake):
        a,b=preflight('old','insert',voice,'landscape',6480,6840,hashlib.sha256(b'original').hexdigest())
        self.assertEqual((a['frames'],b['frames']),(9377,360))
  def test_wrong_audio_rejected(self):
    with TemporaryDirectory() as d:
      voice=Path(d)/'voice';voice.write_bytes(b'original')
      def fake(p):return {'width':1920,'height':1080,'fps':'60/1','frames':9377 if p=='old' else 360}
      with patch('splice_verified_source.metadata',side_effect=fake):
        with self.assertRaises(ValueError):preflight('old','insert',voice,'landscape',6480,6840,'bad')
  def test_mismatched_insert_rejected(self):
    with TemporaryDirectory() as d:
      voice=Path(d)/'voice';voice.write_bytes(b'original')
      def fake(p):return {'width':1920,'height':1080,'fps':'60/1','frames':9377 if p=='old' else 359}
      with patch('splice_verified_source.metadata',side_effect=fake):
        with self.assertRaises(ValueError):preflight('old','insert',voice,'landscape',6480,6840,hashlib.sha256(b'original').hexdigest())
  def test_wrong_view_rejected(self):
    with TemporaryDirectory() as d:
      voice=Path(d)/'voice';voice.write_bytes(b'original')
      def fake(p):return {'width':1920,'height':1080,'fps':'60/1','frames':9377 if p=='old' else 360}
      with patch('splice_verified_source.metadata',side_effect=fake):
        with self.assertRaises(ValueError):preflight('old','insert',voice,'portrait',6480,6840,hashlib.sha256(b'original').hexdigest())
  def test_cannot_overwrite_review(self):
    with TemporaryDirectory() as d:
      out=Path(d)/'already.mp4';out.write_bytes(b'protected')
      with patch('splice_verified_source.preflight',return_value=({'frames':9377},{})):
        with self.assertRaises(FileExistsError):splice('old','insert','voice',out,'landscape',6480,6840,'hash')
if __name__=='__main__':unittest.main()