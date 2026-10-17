"""Decode a development preview and verify cadence and the original voice take."""
import argparse
from fractions import Fraction
import json
import hashlib
import math
import re
from pathlib import Path
import subprocess
import wave
import numpy as np


def verify_frames(checksums,size,fps,count):
    headers={};frames=[]
    for line in checksums.splitlines():
        if line.startswith('#tb 0:'):headers['timebase']=Fraction(line.split(':',1)[1].strip())
        elif line.startswith('#dimensions 0:'):headers['size']=tuple(map(int,line.split(':',1)[1].strip().split('x')))
        elif line and not line.startswith('#'):
            fields=[p.strip() for p in line.split(',')]
            frames.append(tuple(map(int,fields[1:4])))
    if headers.get('size')!=tuple(size):raise ValueError('Unexpected decoded dimensions')
    if headers.get('timebase')!=Fraction(1,fps):raise ValueError('Unexpected decoded frame timebase')
    if len(frames)!=count:raise ValueError(f'Expected {count} frames; decoded {len(frames)}')
    if any(row!=(i,i,1) for i,row in enumerate(frames)):
        raise ValueError('Missing, duplicated or irregular decoded frame timestamps')
    return {'dimensions':list(size),'fps':fps,'decodedFrames':len(frames),'continuousTimestamps':True}


def compare_audio(actual,reference,sample_rate=16000):
    actual=np.asarray(actual,dtype=np.float64);reference=np.asarray(reference,dtype=np.float64)
    if not len(actual) or not len(reference):raise ValueError('Missing decoded audio')
    if abs(len(actual)-len(reference))>sample_rate*.05:raise ValueError('Audio duration differs from the reference')
    actual=actual-actual.mean();reference=reference-reference.mean()
    n=1<<(len(actual)+len(reference)-1).bit_length()
    cross=np.fft.irfft(np.fft.rfft(actual,n)*np.conj(np.fft.rfft(reference,n)),n)
    limit=round(sample_rate*.1);lags=np.arange(-limit,limit+1)
    lag=int(lags[np.argmax(cross[lags%n])])
    if lag>=0:a=actual[lag:];b=reference
    else:a=actual;b=reference[-lag:]
    length=min(len(a),len(b));a=a[:length];b=b[:length]
    energy=float(np.linalg.norm(a)*np.linalg.norm(b))
    correlation=float(np.dot(a,b)/energy) if energy else 0.0
    if abs(lag)>sample_rate*.002:raise ValueError(f'Audio is offset by {lag/sample_rate:.4f} seconds')
    if correlation<.98:raise ValueError(f'Decoded audio does not match reference: {correlation:.5f}')
    return {'referenceCorrelation':correlation,'offsetSamples':lag,'comparisonSampleRate':sample_rate,
            'decodedAudioSeconds':len(actual)/sample_rate,'referenceAudioSeconds':len(reference)/sample_rate,
            'phonemeTimingVerified':False}


def decode_audio(ffmpeg,path):
    result=subprocess.run([ffmpeg,'-nostdin','-hide_banner','-loglevel','info','-xerror','-copyts',
        '-i',str(path),'-map','0:a:0','-ac','1','-af','aresample=16000,ashowinfo','-ar','16000','-f','f32le','-'],
        check=True,capture_output=True)
    first=re.search(r'n:\s*0\s+pts:\s*-?\d+\s+pts_time:\s*([-+0-9.eE]+)',result.stderr.decode())
    if first is None or abs(float(first.group(1)))>.002:raise ValueError('Audio track does not start at zero')
    return np.frombuffer(result.stdout,dtype='<f4')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video',type=Path);p.add_argument('reference',type=Path)
    p.add_argument('--ffmpeg',required=True);p.add_argument('--vertical',action='store_true');p.add_argument('--report',type=Path)
    a=p.parse_args()
    with wave.open(str(a.reference)) as w:duration=w.getnframes()/w.getframerate()
    checksums=subprocess.run([a.ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-xerror',
        '-copyts','-i',str(a.video),'-map','0:v:0','-fps_mode','passthrough','-f','framemd5','-'],check=True,capture_output=True,text=True).stdout
    with a.video.open('rb') as f:video_sha=hashlib.file_digest(f,'sha256').hexdigest()
    report={'video':a.video.name,'videoSha256':video_sha,**verify_frames(checksums,(1080,1920) if a.vertical else (1920,1080),60,math.ceil(duration*60)),
            **compare_audio(decode_audio(a.ffmpeg,a.video),decode_audio(a.ffmpeg,a.reference))}
    if a.report:a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
