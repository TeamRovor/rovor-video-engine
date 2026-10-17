import tempfile
import unittest
import wave
from pathlib import Path
import numpy as np
from speech_planner import audio_envelope
from render_acting_video import verify_audio_plan


class RecordingMatchTests(unittest.TestCase):
    def test_wrong_take_cannot_use_existing_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'voice.wav'
            def write(amplitude):
                values=(amplitude*np.sin(np.arange(1600)*.17)).astype('<i2')
                with wave.open(str(path),'wb') as wav:
                    wav.setparams((1,2,16000,0,'NONE','not compressed'))
                    wav.writeframes(values.tobytes())
            write(1000);plan={'audio':audio_envelope(path)}
            result=verify_audio_plan(plan,path)
            self.assertTrue(result['rmsEnvelopeMatched'])
            self.assertFalse(result['phonemeTimingVerified'])
            write(2000)
            with self.assertRaisesRegex(ValueError,'does not match'):
                verify_audio_plan(plan,path)


if __name__=='__main__':unittest.main()
