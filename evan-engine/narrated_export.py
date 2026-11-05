"""Mux a finite silent review video with the complete mono PCM16 narration.

Encoding audio in a command stopped by -frames:v can truncate its final packet.
Mux only after the silent video is complete, and verify the decoded sample count.
"""
import argparse,json,subprocess,tempfile,wave
from pathlib import Path

def mux_complete_audio(ffmpeg,video,audio,output):
    video,audio,output=map(Path,(video,audio,output))
    with wave.open(str(audio)) as source:
        if source.getnchannels()!=1 or source.getsampwidth()!=2 or source.getcomptype()!='NONE':
            raise ValueError('Review narration must be mono PCM16 WAV')
        rate=source.getframerate();expected=source.getnframes()
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix='.mp4',dir=output.parent,delete=False) as f:temporary=Path(f.name)
    def run(args):
        return subprocess.run([str(ffmpeg),'-hide_banner','-loglevel','error','-nostdin',*map(str,args)],check=True,capture_output=True)
    try:
        run(['-y','-i',video,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy',
             '-c:a','aac','-b:a','192k','-movie_timescale',rate,'-movflags','+faststart',temporary])
        decoded=run(['-i',temporary,'-map','0:a:0','-ac','1','-ar',rate,'-f','s16le','-'])
        actual=len(decoded.stdout)//2
        if actual!=expected:raise RuntimeError(f'Narration sample count changed: {expected} -> {actual}')
        temporary.replace(output)
        return dict(sourcePcm16Samples=expected,decodedPcm16Samples=actual,rate=rate,codec='AAC',decodeErrors=decoded.stderr.decode())
    finally:
        temporary.unlink(missing_ok=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('ffmpeg',type=Path);p.add_argument('video',type=Path);p.add_argument('audio',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(mux_complete_audio(a.ffmpeg,a.video,a.audio,a.output)))
