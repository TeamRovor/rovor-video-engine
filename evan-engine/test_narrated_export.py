"""Regression for truncated audio when a 48fps cut ends between AAC packets."""
import os,subprocess,tempfile,unittest,wave
from pathlib import Path
import numpy as np
from PIL import Image
from narrated_export import mux_complete_audio
class NarrationExportTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('ROVOR_TEST_FFMPEG'),'Set ROVOR_TEST_FFMPEG for the integration check')
    def test_complete_fractional_frame_audio_with_longer_image_sequence(self):
        ff=os.environ['ROVOR_TEST_FFMPEG']
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);im=root/'source.png';Image.new('RGB',(32,32),'#385b6b').save(im)
            for i in range(240):os.link(im,root/f'{i:06}.png')
            wav=root/'voice.wav';n=74667;t=np.arange(n)/16000;pcm=(np.sin(t*2*np.pi*170)*4000).astype('<i2')
            with wave.open(str(wav),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(pcm.tobytes())
            video=root/'silent.mp4';subprocess.run([ff,'-hide_banner','-loglevel','error','-nostdin','-y','-framerate','48','-i',str(root/'%06d.png'),'-frames:v','224','-an','-c:v','libx264','-pix_fmt','yuv420p',str(video)],check=True,capture_output=True)
            result=mux_complete_audio(ff,video,wav,root/'final.mp4');self.assertEqual(result['decodedPcm16Samples'],n)
            decoded=subprocess.run([ff,'-hide_banner','-loglevel','error','-nostdin','-i',str(root/'final.mp4'),'-map','0:v:0','-f','framemd5','-'],check=True,capture_output=True)
            self.assertEqual(sum(bool(x and not x.startswith('#')) for x in decoded.stdout.decode().splitlines()),224)
if __name__=='__main__':unittest.main()
