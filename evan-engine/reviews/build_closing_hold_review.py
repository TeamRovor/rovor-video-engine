"""One fixed-dwell comparison from the registered closing-shot review cache.

Run with the repository's evan-engine on PYTHONPATH. No engine or artwork edits.
"""
import hashlib
import json
import shutil
import subprocess
import wave
from pathlib import Path
from narrated_export import mux_complete_audio

root = Path(__file__).resolve().parents[4]
source = root / 'outputs/evan-cartoon-closing-shot'
out = root / 'outputs/evan-cartoon-closing-hold'
media = root.parent / 'referenced-chatgpt-conversation-this-is-an/work'
ff = media / 'media-tools/ffmpeg'
voice = media / 'evan-narration.wav'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def run(args):
    return subprocess.run([str(ff), '-v', 'error', '-nostdin', *map(str, args)],
                          check=True, capture_output=True)

def build():
    # shortcut: authored still end-card; a longer character performance needs new acting.
    out.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((source / 'Verification.json').read_text())
    assert baseline['cutFrame'] == 1063 and not baseline['defaultChanged']
    assert sha(voice) == '28487eb9c730c3d6a9613a4d419d8d590aa3a72c7816de7fb9183d9a7e552f96'
    with wave.open(str(voice)) as f:
        assert (f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()) == (1, 2, 16000, 352758)
        f.setpos(304000)
        pcm = f.readframes(48758)
    assert len(pcm) == 48758 * 2
    frames = out / 'Frames'
    frames.mkdir(exist_ok=True)
    originals = {}
    for i in range(912, 1104):
        p = source / 'After/Frames' / f'{i:06}.png'
        originals[i] = sha(p)
        shutil.copy2(p, frames / p.name)
    last = frames / '001103.png'
    for i in range(1104, 1164):
        shutil.copy2(last, frames / f'{i:06}.png')
    assert all(sha(frames / f'{i:06}.png') == h for i, h in originals.items())
    assert all(sha(frames / f'{i:06}.png') == sha(last) for i in range(1104, 1164))
    padded = pcm + bytes((84000 - 48758) * 2)
    wav = out / 'Original-Closing-With-Longer-Hold.wav'
    with wave.open(str(wav), 'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(padded)
    with wave.open(str(wav)) as f:
        assert f.getnframes() == 84000 and f.readframes(84000) == padded
    silent = out / 'Silent.mp4'
    run(['-y', '-framerate', 48, '-start_number', 912, '-i', frames / '%06d.png',
         '-frames:v', 252, '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', 16,
         '-pix_fmt', 'yuv420p', silent])
    normal, slow = out / 'Longer-Normal.mp4', out / 'Longer-Quarter-Speed.mp4'
    audio = mux_complete_audio(ff, silent, wav, normal)
    run(['-y', '-framerate', 12, '-start_number', 912, '-i', frames / '%06d.png',
         '-frames:v', 1008, '-vf', 'fps=48', '-an', '-c:v', 'libx264',
         '-preset', 'fast', '-crf', 16, '-pix_fmt', 'yuv420p', slow])
    films = {}
    for p, expected in [(normal, 252), (slow, 1008)]:
        result = run(['-i', p, '-map', '0:v:0', '-f', 'framemd5', '-'])
        count = sum(bool(s and not s.startswith('#')) for s in result.stdout.decode().splitlines())
        assert count == expected
        films[p.name] = dict(decodedFrames=count, sha256=sha(p))
    for name in ['After-Normal.mp4', 'After-Quarter-Speed.mp4']:
        assert sha(source / name) == baseline['films'][name]['sha256']
        shutil.copy2(source / name, out / name.replace('After', 'Short'))
    report = dict(sourceFramesSha256=originals, originalFramesExact=192,
                  repeatedFinalFramesExact=60, holdFrame=1103, endTime=24.25,
                  cutFrame=1063, cutTime=1063/48, raisedShotDwellSeconds=(1164-1063)/48,
                  shortRaisedShotDwellSeconds=(1104-1063)/48,
                  sourcePcmRange=[304000,352758], originalPcmSamples=48758,
                  zeroPadSamples=35242, wavPcmExact=True, audio=audio, films=films,
                  sourceVerificationSha256=sha(source/'Verification.json'),
                  scriptSha256=sha(Path(__file__)),
                  defaultChanged=False, sourceArtworkChanged=False,
                  independentListeningAccepted=False, realTimeActingAccepted=False,
                  polishedMilestoneReady=False)
    (out / 'Verification.json').write_text(json.dumps(report, indent=2)+'\n')
    shutil.copy2(Path(__file__), out / 'build_closing_hold_review.py.txt')
    print(json.dumps({k:v for k,v in report.items() if k!='sourceFramesSha256'}, indent=2))

if __name__ == '__main__':
    build()
