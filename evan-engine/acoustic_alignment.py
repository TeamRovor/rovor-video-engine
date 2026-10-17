"""Two-pass local acoustic forced alignment with explicit audit/fallback.
PocketSphinx acoustic scores are diagnostics, NOT calibrated confidence.
"""
import re,wave

def align_script(plan,wav):
    from pocketsphinx import Decoder
    from speech_planner import tokens,shape,OVERRIDES
    if plan['coverage']<.85:raise ValueError('Script/recognition agreement below 85%; refusing forced alignment')
    with wave.open(str(wav)) as f:
        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):
            raise ValueError('Acoustic alignment requires 16 kHz mono PCM16 WAV')
        data=f.readframes(f.getnframes());duration=f.getnframes()/16000
    ps=Decoder(lm=None,loglevel='ERROR',frate=100)
    desired=tokens(plan['script'])
    for word,pron in OVERRIDES.items():ps.add_word(word,re.sub('[012]','',pron),True)
    unknown=sorted({w for w in desired if not ps.lookup_word(w)})
    if unknown:raise ValueError('Missing acoustic dictionary pronunciations: '+', '.join(unknown))
    ps.set_align_text(' '.join(desired))
    ps.start_utt();ps.process_raw(data,full_utt=True);ps.end_utt()
    ps.set_alignment()
    ps.start_utt();ps.process_raw(data,full_utt=True);ps.end_utt()
    words=[];phones=[];silences=[];warnings=[]
    spans=list(re.finditer(r"[a-z]+(?:'[a-z]+)?",plan['script'].lower()))
    anchors={w['scriptIndex']:w for w in plan['words']}
    for entry in ps.get_alignment():
        start=entry.start/100;end=(entry.start+entry.duration)/100
        if entry.name in ('<sil>','<s>','</s>','[SPEECH]'):
            silences.append(dict(start=start,end=end));continue
        i=len(words)
        name=re.sub(r'\(\d+\)$','',entry.name)
        if i>=len(desired) or name!=desired[i]:raise ValueError('Forced alignment word sequence differs from script')
        if end<=start or end>duration+.04:raise ValueError('Invalid acoustic word duration: '+name)
        anchor=anchors.get(i);disagreement=max(abs(start-anchor['start']),abs(end-anchor['end'])) if anchor else None
        flags=[]
        if disagreement is not None and disagreement>.25:flags.append('word-anchor-disagreement')
        if end-start>1.5:flags.append('long-word-duration')
        row=dict(word=name,scriptIndex=i,start=start,end=end,timing='acoustic-forced',
                 acousticScore=entry.score,confidence=None,reviewFlags=flags,
                 anchorDisagreement=disagreement,charStart=spans[i].start(),charEnd=spans[i].end())
        words.append(row)
        for phone in entry:
            a=phone.start/100;b=(phone.start+phone.duration)/100
            if b<=a:raise ValueError('Zero-duration acoustic phone: '+name+' '+phone.name)
            phones.append(dict(start=a,end=b,phone=phone.name,value=shape(phone.name),word=name,
                               scriptIndex=i,timing='acoustic-forced',acousticScore=phone.score,confidence=None))
        if flags:warnings.append('Review acoustic alignment: '+name+' ('+', '.join(flags)+')')
    if len(words)!=len(desired):raise ValueError('Incomplete acoustic alignment')
    # Audit mismatches remain visible even when forced text can be aligned.
    return dict(words=words,phonemes=phones,silences=silences,warnings=warnings,
                method='PocketSphinx two-pass word/phone acoustic forced alignment, 10 ms frames',
                confidenceNote='Raw acoustic scores are not probabilities; word-anchor disagreement flags require review')

def upgrade_plan(plan,wav,required=False):
    try:aligned=align_script(plan,wav)
    except (ImportError,RuntimeError,ValueError) as error:
        if required:raise
        plan['alignment']={'status':'fallback','reason':str(error)}
        plan['warnings'].append('Acoustic alignment unavailable/rejected: '+str(error))
        return plan
    plan['estimatedWords']=plan['words'];plan['estimatedPhonemes']=plan['phonemes']
    plan['recognitionWarnings']=list(plan['warnings'])
    plan['warnings']=['Recognition audit: '+w for w in plan['warnings']]
    for key in ('words','phonemes','silences'):plan[key]=aligned[key]
    plan['warnings'].extend(aligned['warnings'])
    plan['alignment']=dict(status='acoustic',method=aligned['method'],confidenceNote=aligned['confidenceNote'],wordCoverage=1.,reviewWordCount=sum(bool(w['reviewFlags']) for w in aligned['words']))
    plan['timingMethod']=aligned['method'];plan['version']=2
    return plan
