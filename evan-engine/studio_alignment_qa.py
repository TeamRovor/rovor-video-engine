"""Conservative QA of cartoon voice/phoneme alignment.

Diagnostics, NOT a source of truth for word boundaries. Flags anomalies with
independent waveform and human evidence; never infers a probability from
raw acoustic scores or treats an independent auto-aligner as ground truth.
"""
from __future__ import annotations
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
import wave


def _bounds(row,label):
    a,b=float(row['start']),float(row['end'])
    if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b):
        raise ValueError(f'Invalid {label} bounds: {row}')
    return a,b


def actual_audio(wav):
    path=Path(wav)
    with wave.open(str(path),'rb') as f:
        rate, channels, width, n=f.getframerate(),f.getnchannels(),f.getsampwidth(),f.getnframes()
        if channels not in (1,2) or width!=2 or rate<8000:
            raise ValueError('Audio QA requires PCM16 mono/stereo WAV, >= 8 kHz')
        raw=f.readframes(n)
    pcm=array.array('h');pcm.frombytes(raw)
    if sys.byteorder!='little':pcm.byteswap()
    hop=max(1,round(rate*.01)); energies=[]
    for i in range(0,n,hop):
        count=min(hop,n-i)
        samples=(pcm[j] for j in range(i*channels,(i+count)*channels))
        # Average channel power avoids cancelling phase-opposed stereo signals.
        sq=sum(float(v)*v for v in samples)
        energies.append(math.sqrt(sq/(count*channels))/32768)
    return {'sha256':hashlib.sha256(raw).hexdigest(),'sampleRate':rate,
            'durationSec':n/rate,'hopSec':hop/rate,'rms':energies}


def _percentile(values,p):
    if not values:return None
    v=sorted(values);k=(len(v)-1)*p;lo=int(k);hi=min(len(v)-1,lo+1)
    if lo==hi:return v[lo]
    return v[lo]*(hi-k)+v[hi]*(k-lo)


def evaluate(plan,wav=None,review=None,reference=None):
    if plan.get('alignment',{}).get('status') != 'acoustic':
        raise ValueError('Acoustic alignment is required. Never QC estimated fallbacks as verified sound.')
    words=plan['words']; phones=plan['phonemes']
    if not words or not phones:raise ValueError('Empty acoustic words or phones')
    audio=actual_audio(wav) if wav is not None else None
    duration=audio['durationSec'] if audio else None
    estimates={int(w['scriptIndex']):w for w in plan.get('estimatedWords',[])}
    decisions={int(w['scriptIndex']):w for w in (review or {}).get('words',[])}
    if len(decisions) != len((review or {}).get('words',[])):
        raise ValueError('Duplicate review decisions for script index')
    diagnostics=[]; structurals=[];risk=[];ordered=[]
    prev_end=0.
    for w in words:
        i=int(w['scriptIndex']);a,b=_bounds(w,'word')
        if ordered and i<=ordered[-1]:structurals.append(f'nonmonotonic-script-index:{i}')
        ordered.append(i)
        if a<prev_end-.03:structurals.append(f'overlap-word:{i}')
        if duration is not None and b>duration+.03:structurals.append(f'word-beyond-wav:{i}')
        prev_end=b
        p_here=[p for p in phones if int(p.get('scriptIndex',-1))==i]
        if not p_here:structurals.append(f'missing-phones:{i}')
        durations=[];run=0;largest_run=0
        prev_phone=a
        for p in p_here:
            x,y=_bounds(p,'phone')
            if x<a-.02 or y>b+.02:structurals.append(f'phone-outside-word:{i}:{p["phone"]}')
            if x<prev_phone-.025:structurals.append(f'overlapping-phones:{i}:{p["phone"]}')
            prev_phone=y
            lengths=y-x;durations.append(lengths)
            if lengths<=.011:run+=1;largest_run=max(largest_run,run)
            else:run=0
        if largest_run>=3:risk.append(f'consecutive-short-phones:{i}:{largest_run}')
        anchor=estimates.get(i)
        discrepancy=None
        if anchor:
            x,y=_bounds(anchor,'independent anchor')
            discrepancy=round(max(abs(a-x),abs(b-y)),4)
        if discrepancy is not None and discrepancy>.25:risk.append(f'word-anchor-disagreement:{i}')
        flagged=bool(w.get('reviewFlags')) or (discrepancy is not None and discrepancy>.25)
        reviewed=decisions.get(i,{})
        decision=reviewed.get('reviewDecision','pending')
        if decision not in ('pending','accept','revise','unresolved'):
            raise ValueError(f'Unexpected review decision {decision} at index {i}')
        notes=reviewed.get('reviewerNotes','')
        # A revised boundary must be exported back to the underlying speech
        # plan and realigned; a decision on its own cannot fix the animation.
        resolved=flagged and decision=='accept' and isinstance(notes,str) and bool(notes.strip())
        if flagged and not resolved:risk.append(f'unresolved-human-review:{i}')
        diagnostics.append({'scriptIndex':i,'word':w['word'],'start':a,'end':b,
             'phoneCount':len(p_here),'shortPhoneRun':largest_run,
             'acousticVsIndependentBoundaryDifferenceSec':discrepancy,
             'reviewFlagged':flagged,'reviewDecision':decision if flagged else 'not-required',
             'reviewResolved':resolved if flagged else None,
             'acousticScore':w.get('acousticScore'),'acousticScoreIsProbability':False})
    orphan=[p for p in phones if int(p.get('scriptIndex',-1)) not in set(ordered)]
    if orphan:structurals.append(f'orphan-phone-count:{len(orphan)}')
    if audio:
        curve=audio['rms'];dt=audio['hopSec']
        levels=[]
        for item in diagnostics:
            a,b=item['start'],item['end'];start=max(0,int(a/dt));end=min(len(curve),max(start+1,math.ceil(b/dt)))
            rms=statistics.mean(curve[start:end]) if start<len(curve) else 0.
            item['measuredWordRms']=round(rms,7);levels.append(rms)
        baseline=_percentile([v for v in levels if v>.001],.5)
        if baseline is not None:
            for item in diagnostics:
                # Weak acoustic energy is a REVIEW cue, not evidence a word is wrong.
                if item['measuredWordRms']<max(.002,baseline*.16):
                    risk.append(f'low-energy-word:{item["scriptIndex"]}')
    reference_metrics=None
    if reference is not None:
        if reference.get('provenance')!='human-annotated':
            raise ValueError('Only explicitly human-annotated reference may be labeled ground truth')
        labels={int(x['scriptIndex']):x for x in reference.get('words',[])}
        if len(labels)!=len(reference.get('words',[])):raise ValueError('Duplicate gold label index')
        errors=[];matched=0
        for item in diagnostics:
            gold=labels.get(item['scriptIndex'])
            if gold is None:continue
            ga,gb=_bounds(gold,'human reference')
            errors.extend((abs(item['start']-ga),abs(item['end']-gb)));matched+=1
        reference_metrics={'wordPairs':matched,'boundaryCount':len(errors),
             'medianBoundaryErrorSec':round(_percentile(errors,.5),4) if errors else None,
             'p95BoundaryErrorSec':round(_percentile(errors,.95),4) if errors else None,
             'fractionBoundariesWithin50ms':round(sum(e<=.05 for e in errors)/len(errors),4) if errors else None,
             'referenceIsHumanAnnotated':True}
    blockers=[]
    if not audio:blockers.append('No exact recording supplied: waveform evidence not checked')
    if structurals:blockers.append('Alignment interval/index structural errors need correction')
    if any(s.startswith('unresolved-human-review') for s in risk):blockers.append('Flagged words lack documented human acceptance or corrected plan')
    if reference_metrics is None:blockers.append('No human ground-truth timing benchmark supplied')
    # Even a reviewed 2s sample is not a completed cartoon film.
    return {'evaluationKind':'conservative-diagnostics-not-certification',
        'status':'blocked' if blockers else 'reviewed-not-animation-approved',
        'wordCount':len(words),'phoneCount':len(phones),
        'flaggedWordCount':sum(d['reviewFlagged'] for d in diagnostics),
        'unresolvedWordCount':sum(d['reviewFlagged'] and not d['reviewResolved'] for d in diagnostics),
        'wavEvidence': ({k:v for k,v in audio.items() if k!='rms'} if audio else None),
        'referenceMetrics':reference_metrics,
        'structuralErrors':structurals,'reviewRisks':sorted(set(risk)),
        'releaseBlockers':blockers,'words':diagnostics,
        'notes':['Log-likelihood and raw acoustic scores are not calibrated probabilities',
                 'RMS, short-phone runs and cross-model mismatch prioritize review, not auto-fixes',
                 'Even perfect source timing cannot approve visual lip shapes, acting or staging']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('speech_plan',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--wav',type=Path);p.add_argument('--review',type=Path);p.add_argument('--reference',type=Path)
    a=p.parse_args();load=lambda f:json.loads(f.read_text()) if f else None
    result=evaluate(load(a.speech_plan),a.wav,load(a.review),load(a.reference))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','wordCount','phoneCount','unresolvedWordCount','releaseBlockers')},indent=2))