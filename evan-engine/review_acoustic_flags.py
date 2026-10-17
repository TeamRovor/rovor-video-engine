"""Make evidence packets for suspicious acoustic word alignments.

This tool does NOT decide whether a word or phone boundary is accurate.
Compare aligned word bounds against the independent recognition estimate while
showing waveform, spectrogram, and constituent phones in recording time.
"""
import argparse
import csv
import json
import math
import re
import wave
from pathlib import Path

import numpy as np


def word_review_rows(plan, expected=None):
    if plan.get('alignment', {}).get('status') != 'acoustic':
        raise ValueError('Requires an acoustic speech plan; estimated fallback is not evidence')
    anchors = {int(w['scriptIndex']): w for w in plan.get('estimatedWords', [])}
    rows = []
    for word in plan['words']:
        flags = list(word.get('reviewFlags') or [])
        if not flags:
            continue
        i = int(word['scriptIndex'])
        anchor = anchors.get(i)
        a, b = float(word['start']), float(word['end'])
        if not (math.isfinite(a) and math.isfinite(b) and 0 <= a < b):
            raise ValueError(f'Invalid acoustic word bounds at script index {i}')
        if not anchor:
            anchor_bounds = None
            disagreement = None
            flags.append('missing-independent-anchor')
        else:
            x, y = float(anchor['start']), float(anchor['end'])
            if not (math.isfinite(x) and math.isfinite(y) and 0 <= x < y):
                raise ValueError(f'Invalid independent anchor at script index {i}')
            anchor_bounds = [x, y]
            disagreement = round(max(abs(a-x), abs(b-y)), 5)
        bounds = [a,b] if anchor_bounds is None else [min(a, anchor_bounds[0]), max(b, anchor_bounds[1])]
        safe = re.sub(r'[^a-z0-9-]', '-', word['word'].lower()).strip('-') or 'word'
        phones = [p for p in plan['phonemes'] if int(p.get('scriptIndex',-1)) == i]
        rows.append({
            'scriptIndex': i, 'word': word['word'], 'reviewFlags': flags,
            'acousticBounds': [a,b], 'independentAnchorBounds': anchor_bounds,
            'maxBoundaryDifferenceSec': disagreement,
            'acousticScore': word.get('acousticScore'),
            'phoneCount': len(phones),
            'phoneSequence': [p['phone'] for p in phones],
            'displayWindow': [round(max(0., bounds[0] - .35), 4), round(bounds[1] + .35, 4)],
            'evidenceImage': f'{i:03d}-{safe}.png', 'reviewDecision': 'pending',
            'reviewerNotes': '',
        })
    rows.sort(key=lambda x:x['scriptIndex'])
    if expected is not None and len(rows) != expected:
        raise ValueError(f'Expected {expected} flagged words; received {len(rows)}. No output written.')
    return rows


def wav_samples(path):
    with wave.open(str(path), 'rb') as f:
        rate, channels, sample_width = f.getframerate(), f.getnchannels(), f.getsampwidth()
        if sample_width != 2 or rate < 8000 or channels not in (1,2):
            raise ValueError('Review requires 8 kHz+ PCM16 mono/stereo WAV')
        raw = f.readframes(f.getnframes())
    x = np.frombuffer(raw, '<i2').reshape(-1, channels).astype('float32').mean(axis=1)/32768.
    return rate, x


def plot_item(plan, item, rate, x, target):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    a,b = item['displayWindow']; b = min(b,len(x)/rate)
    if b<=a: raise ValueError('Review word falls outside WAV duration')
    i0,i1 = max(0,int(a*rate)), min(len(x),int(math.ceil(b*rate)))
    segment = x[i0:i1]
    if not len(segment): raise ValueError('Empty review segment')
    ts = np.arange(i0,i1)/rate
    fig, axes = plt.subplots(4,1,figsize=(14,9),sharex=True,
                            gridspec_kw={'height_ratios':[1.1,1.8,.55,.8]},constrained_layout=True)
    waveform, spectrum, bounds_ax, phone_ax = axes
    stride=max(1,rate//3000)
    waveform.plot(ts[::stride],segment[::stride],lw=.6,color='#24546c')
    waveform.set_ylabel('PCM waveform'); waveform.set_ylim(-1.,1.)
    nfft = min(512, max(128, 2**int(math.floor(math.log2(max(128,len(segment)))))))
    overlap = int(nfft*.75)
    with np.errstate(divide='ignore'):
        spectrum.specgram(segment,Fs=rate,NFFT=nfft,noverlap=overlap,
                         xextent=(i0/rate,i0/rate+len(segment)/rate),
                         cmap='magma',vmin=-120,vmax=-30)
    spectrum.set_ylim(0,min(5000,rate/2));spectrum.set_ylabel('Spectrogram Hz')
    acoustic = item['acousticBounds']; anchor=item['independentAnchorBounds']
    for ax in (waveform,spectrum,bounds_ax,phone_ax):
        for t in acoustic:ax.axvline(t,color='#088a8a',lw=1.8,alpha=.9)
        if anchor:
            for t in anchor:ax.axvline(t,color='#c34b2c',lw=1.4,ls='--',alpha=.9)
        ax.set_xlim(a,b)
    bounds_ax.axvspan(*acoustic,color='#088a8a',alpha=.25)
    bounds_ax.text((acoustic[0]+acoustic[1])/2,.72,'ACOUSTIC',ha='center',fontsize=9)
    if anchor:
        bounds_ax.axvspan(*anchor,color='#c34b2c',alpha=.15)
        bounds_ax.text((anchor[0]+anchor[1])/2,.20,'INDEPENDENT ESTIMATE',ha='center',fontsize=8)
    bounds_ax.set_ylim(0,1);bounds_ax.set_yticks([]);bounds_ax.set_ylabel('Word')
    phones=[p for p in plan['phonemes'] if int(p.get('scriptIndex',-1)) == item['scriptIndex']]
    for p in phones:
        pa,pb=float(p['start']),float(p['end'])
        if pb<=pa:continue
        phone_ax.axvspan(pa,pb,color='#34678a',alpha=.18)
        phone_ax.text((pa+pb)/2,.48,p['phone'],ha='center',va='center',fontsize=8)
    phone_ax.set_ylim(0,1);phone_ax.set_yticks([]);phone_ax.set_ylabel('Phones')
    phone_ax.set_xlabel('Recording time (seconds)');phone_ax.xaxis.set_major_locator(MultipleLocator(.1))
    fig.suptitle(f"Review {item['scriptIndex']}: {item['word']} — {', '.join(item['reviewFlags'])}\n"
                 f"Acoustic teal | independent recognition estimate dashed orange | decision PENDING; acoustic scores are not probabilities",
                 fontsize=12)
    fig.savefig(target,dpi=145);plt.close(fig)


def create_packet(plan,wav,out,expected=None,render=True):
    rows=word_review_rows(plan,expected)
    out=Path(out)
    if not rows: raise ValueError('No flagged acoustic words; no evidence packet made')
    rate,x=wav_samples(wav)
    if any(item['acousticBounds'][1]>len(x)/rate+.04 for item in rows):
        raise ValueError('Word end exceeds review WAV duration')
    out.mkdir(parents=True,exist_ok=True)
    if render:
        for item in rows:plot_item(plan,item,rate,x,out/item['evidenceImage'])
    fields=['scriptIndex','word','reviewFlags','acousticBounds','independentAnchorBounds',
            'maxBoundaryDifferenceSec','phoneSequence','evidenceImage','reviewDecision','reviewerNotes']
    with (out/'review.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    (out/'review.json').write_text(json.dumps({
        'status':'awaiting-perceptual-review', 'acousticIsGroundTruth':False,
        'audioSampleRate':rate, 'recordingDurationSec':len(x)/rate,
        'flaggedWordCount':len(rows),'words':rows
    },indent=2)+'\n')
    lines=['# Acoustic alignment decisions — human review required', '',
           'Teal = forced acoustic alignment; orange dashed = independent recognition estimate.',
           'Neither method is ground truth. Compare sound on replay against waveform and spectrogram.',
           'For each row: listen at normal and slower speed; inspect plosives, fricatives, vowel onset and silence;',
           'enter accept, revise or unresolved plus notes into review.csv or review.json.',
           'These files are evidence packets, not approvals. Do not adjust speech timings without evidence.','']
    for row in rows:
        lines += [f"- [ ] {row['scriptIndex']:03d} **{row['word']}**: acoustic {row['acousticBounds']}, "
                  f"estimate {row['independentAnchorBounds']}, difference {row['maxBoundaryDifferenceSec']} s; "
                  f"{', '.join(row['reviewFlags'])} — {row['evidenceImage']}"]
    (out/'REVIEW.md').write_text('\n'.join(lines)+'\n')
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('speech_plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--expected',type=int,default=None,help='Fail closed if flagged count differs')
    p.add_argument('--index-only',action='store_true',help='Write review index without PNG renders')
    args=p.parse_args()
    rows=create_packet(json.loads(args.speech_plan.read_text()),args.wav,args.output,args.expected,not args.index_only)
    print(f'Generated {len(rows)} UNREVIEWED word evidence records at {args.output}')
