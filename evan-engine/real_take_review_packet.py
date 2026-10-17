"""Generate human acoustic review evidence from an authentic PCM16 WAV and paired scene.

The packet is NOT a forced alignment, a phoneme classifier, a word-boundary
correction, or permission to publish animation. Audio never leaves the local
workspace; generated evidence contains no source audio samples.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np
from scipy.signal import stft


def _read_wav(path: Path):
    with wave.open(str(path), 'rb') as f:
        rate, channels, width, n = f.getframerate(), f.getnchannels(), f.getsampwidth(), f.getnframes()
        if channels != 1 or width != 2 or rate != 16000 or n <= 0:
            raise ValueError('Require 16 kHz mono PCM16 review proxy with known provenance')
        raw = f.readframes(n)
    if len(raw) != n * 2:
        raise ValueError('Truncated audio')
    return np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768, rate, hashlib.sha256(raw).hexdigest()


def _interval(row, limit):
    a, b = row.get('start'), row.get('end')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (a, b)):
        raise ValueError('Nonfinite interval')
    if not (0 <= a < b <= limit + 0.04):
        raise ValueError('Invalid or out-of-range interval')
    return float(a), float(b)


def audit(wav_path: Path, scene_path: Path, output_dir: Path, *, expected_pcm_sha256: str | None = None,
          plots: bool = True) -> dict:
    signal, rate, digest = _read_wav(wav_path)
    if expected_pcm_sha256 is not None and digest != expected_pcm_sha256:
        raise ValueError('Audio source does not match paired-take PCM checksum')
    scene = json.loads(Path(scene_path).read_text())
    duration = len(signal) / rate
    if abs(scene.get('duration', -100) - duration) > .04:
        raise ValueError('Scene duration does not match decoded take')
    cues = scene.get('mouthCues', [])
    segments = scene.get('segments', [])
    if not cues or not segments:
        raise ValueError('Missing real scene cues or spoken segments')
    for row in cues + segments:
        _interval(row, duration)
    if any(abs(cues[i]['end'] - cues[i+1]['start']) > .025 for i in range(len(cues)-1)):
        raise ValueError('Cues are discontinuous')
    if any(segments[i]['start'] > segments[i+1]['start'] for i in range(len(segments)-1)):
        raise ValueError('Segments not ordered')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, cue in enumerate(cues):
        a, b = _interval(cue, duration)
        x = signal[max(0, int(a*rate)):min(len(signal), max(int(a*rate)+1, int(b*rate)))]
        rms = float(np.sqrt(np.mean(x*x))) if len(x) else 0.
        # Quiet closure or fricative can be linguistically meaningful: flag, never delete.
        rms_db = 20*math.log10(max(1e-8, rms))
        rows.append({'cueIndex': i, 'startSec': a, 'endSec': b,
                     'rhubarbShape': cue.get('value'), 'durationMs': round((b-a)*1000, 2),
                     'measuredRmsDbfs': round(rms_db, 2),
                     'reviewFlags': (['subframe-at-24fps'] if b-a < 1/24 else []) +
                                    (['quiet-nonidle'] if cue.get('value') != 'X' and rms_db < -37 else []) +
                                    (['held-nonidle'] if cue.get('value') != 'X' and b-a > .4 else [])})
    # A readable TSV can be edited by a human without rewriting the source cues.
    with (output_dir/'cue-review.tsv').open('w') as f:
        f.write('cueIndex\tstartSec\tendSec\trhubarbShape\tdurationMs\tmeasuredRmsDbfs\treviewFlags\thumanDecision\treviewerNotes\n')
        for row in rows:
            f.write('\t'.join(str(row[k]) if k != 'reviewFlags' else ','.join(row[k])
                for k in ('cueIndex','startSec','endSec','rhubarbShape','durationMs','measuredRmsDbfs','reviewFlags')) + '\tpending\t\n')
    if plots:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        for i, seg in enumerate(segments):
            a,b = _interval(seg, duration)
            lo=max(0,int((a-.12)*rate)); hi=min(len(signal),int((b+.12)*rate))
            x=signal[lo:hi]
            times=np.arange(len(x))/rate+lo/rate
            f,t,z=stft(x, fs=rate, nperseg=512, noverlap=448, boundary=None)
            mask=f<=6000
            fig,(ax1,ax2)=plt.subplots(2,1,figsize=(12,4.8),sharex=True,layout='constrained')
            ax1.plot(times,x,linewidth=.42,color='#142b48')
            ax1.set_ylabel('Amplitude')
            ax1.set_ylim(-1,1)
            ax2.pcolormesh(t+lo/rate,f[mask],20*np.log10(np.maximum(1e-7,np.abs(z[mask]))),
                           shading='auto',cmap='magma',vmin=-85,vmax=-22)
            ax2.set_ylabel('Hz');ax2.set_xlabel('Seconds (source audio)')
            for row in rows:
                if row['endSec']<a or row['startSec']>b: continue
                color='#e59a27' if row['reviewFlags'] else '#8c9ba9'
                for ax in (ax1,ax2):ax.axvline(row['startSec'],alpha=.35,color=color,linewidth=.8)
                if row['reviewFlags']:
                    ax1.text(row['startSec'],.78,str(row['cueIndex']),fontsize=7,color='#8d4100')
            for ax in (ax1,ax2):
                ax.axvline(a,color='white' if ax==ax2 else '#476e93',linewidth=.7,alpha=.6)
                ax.axvline(b,color='white' if ax==ax2 else '#476e93',linewidth=.7,alpha=.6)
                ax.set_xlim(lo/rate,hi/rate)
            title=seg.get('text','')
            fig.suptitle(f'V3 audio segment {i+1:02d} — {title[:88]}',fontsize=12)
            fig.savefig(output_dir/f'segment-{i+1:02d}.png',dpi=145)
            plt.close(fig)
    report={'kind':'human-review-evidence-not-phoneme-validation',
            'sourceWavPcmSha256':digest,'durationSec':duration,'sampleRate':rate,
            'sourceSceneSha256':hashlib.sha256(Path(scene_path).read_bytes()).hexdigest(),
            'mouthCueCount':len(cues),'spokenSegmentCount':len(segments),
            'subframeCueIndices':[r['cueIndex'] for r in rows if 'subframe-at-24fps' in r['reviewFlags']],
            'quietNonidleIndices':[r['cueIndex'] for r in rows if 'quiet-nonidle' in r['reviewFlags']],
            'heldNonidleIndices':[r['cueIndex'] for r in rows if 'held-nonidle' in r['reviewFlags']],
            'contactPoseReviewCandidates':{
                'MBP-closure-from-Rhubarb-A-not-phoneme-proof':[r['cueIndex'] for r in rows if r['rhubarbShape']=='A'],
                'FV-lip-teeth-from-Rhubarb-G-not-phoneme-proof':[r['cueIndex'] for r in rows if r['rhubarbShape']=='G'],
                'L-tongue-from-Rhubarb-H-not-phoneme-proof':[r['cueIndex'] for r in rows if r['rhubarbShape']=='H']},
            'audioPairedWithLaterMaster':False,'later18FlaggedWordsReviewed':False,
            'humanPhonemeBoundariesVerified':False,'visualApproved':False,'releaseReady':False,
            'reviewInstructions':'Listen at normal speed, then slow; inspect wave/spectrogram and label exact closures; never infer F/V/L/MBP from Rhubarb labels alone.'}
    (output_dir/'evidence.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('wav',type=Path);p.add_argument('scene',type=Path);p.add_argument('output_dir',type=Path)
    p.add_argument('--expected-pcm-sha256');p.add_argument('--no-plots',action='store_true')
    a=p.parse_args()
    print(json.dumps(audit(a.wav,a.scene,a.output_dir,expected_pcm_sha256=a.expected_pcm_sha256,
                           plots=not a.no_plots),indent=2))