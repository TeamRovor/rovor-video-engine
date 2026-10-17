"""Script pronunciation priors anchored to experimental word timestamps and audio.
Phone boundaries are estimates, NOT forced alignment. Acoustic cues remain fallback.
"""
import re, wave
from difflib import SequenceMatcher
import numpy as np

OVERRIDES={'rovor':'R OW1 V ER0','favicon':'F AE1 V IH0 K AA0 N'}
VOWELS=set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split())
def tokens(text):return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower())
def shape(phone):
    p=phone.rstrip('012')
    if p in ('M','B','P'):return 'A'
    if p in ('F','V'):return 'G'
    if p=='L':return 'H'
    if p in ('UW','UH','W'):return 'F'
    if p in ('OW','AO','OY'):return 'E'
    if p in ('AA','AE','AW'):return 'D'
    if p in VOWELS:return 'C'
    return 'B'

def audio_envelope(path):
    with wave.open(str(path)) as f:
        if f.getsampwidth()!=2:raise ValueError('Speech analysis requires PCM16 WAV')
        rate=f.getframerate();x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
        x=x.reshape(-1,f.getnchannels()).mean(axis=1)
    hop=max(1,round(rate*.01));frames=[x[i:i+hop] for i in range(0,len(x),hop)]
    rms=np.array([np.sqrt(np.mean(a*a)) for a in frames]);reference=max(.005,float(np.percentile(rms,90)))
    # Fixed absolute floor prevents silent recordings normalizing into speech.
    energy=np.clip((rms-.002)/reference,0,1)
    energy=np.convolve(energy,[.2,.6,.2],mode='same')[:len(rms)]
    return {'step':hop/rate,'rms':rms.round(6).tolist(),'energy':energy.round(5).tolist(),'reference':reference}

def build_plan(script,transcript,wav,cues,dictionary=None):
    if dictionary is None:
        import cmudict
        dictionary=cmudict.dict()
    observed=[]
    for row in transcript['transcription']:
        words=tokens(row['text'])
        if not words:continue
        start=row['offsets']['from']/1000;end=row['offsets']['to']/1000
        confidence=float(np.mean([t.get('p',1) for t in row.get('tokens',[])]) if row.get('tokens') else 1)
        for i,w in enumerate(words):
            observed.append(dict(word=w,confidence=confidence,start=start+(end-start)*i/len(words),end=start+(end-start)*(i+1)/len(words),timing='word-estimate' if len(words)==1 else 'segment-estimate'))
    desired=tokens(script);match={};warnings=[]
    for block in SequenceMatcher(None,desired,[w['word'] for w in observed],autojunk=False).get_matching_blocks():
        for i in range(block.size):match[block.a+i]=block.b+i
    words=[];phones=[]
    for i,w in enumerate(desired):
        if i not in match:
            warnings.append('Unaligned script word: '+w);continue
        row=dict(observed[match[i]],scriptIndex=i)
        if row['end']<=row['start']:
            warnings.append('Zero-duration word anchor: '+w);continue
        if row['confidence']<.3:warnings.append('Low-confidence word anchor: '+w)
        pronunciation=OVERRIDES.get(w)
        entries=dictionary.get(w)
        ps=pronunciation.split() if pronunciation else entries[0] if entries else None
        row['pronunciationSource']='project-override' if pronunciation else 'cmudict' if ps else 'unknown'
        words.append(row)
        if not ps:
            warnings.append('Unknown pronunciation: '+w);continue
        lengths=[1.6 if p.rstrip('012') in VOWELS else .65 if p.rstrip('012') in ('P','T','K','B','D','G') else 1 for p in ps]
        span=row['end']-row['start'];cursor=row['start']
        for p,length in zip(ps,lengths):
            end=cursor+span*length/sum(lengths)
            phones.append(dict(start=cursor,end=end,phone=p,value=shape(p),word=w,timing='estimated-within-word'))
            cursor=end
    unmatched=[r['word'] for j,r in enumerate(observed) if j not in match.values()]
    if unmatched:warnings.append('Unmatched recognized words: '+' '.join(unmatched))
    return dict(version=1,script=script,words=words,phonemes=phones,audio=audio_envelope(wav),fallbackCues=cues,
                warnings=warnings,coverage=len(match)/max(1,len(desired)),
                timingMethod='Whisper experimental word anchors; duration-weighted pronunciation phones (not forced alignment)')

def planned_weights(t,plan,fallback):
    from painted_timing import speech_weights,ease
    nearby=[p for p in plan['phonemes'] if p['start']-.08<=t<=p['end']+.08]
    # Blend acoustic recognizer and pronunciation priors; contacts dominate only
    # around their estimated midpoint. Unknown/mismatched words use audio cues.
    prior=speech_weights(t,nearby,preserve_short=True) if nearby else speech_weights(t,fallback);acoustic=speech_weights(t,fallback)
    influence=max((1-float(ease(max(p['start']-t,t-p['end'],0)/.08)) for p in nearby),default=0)*.72
    weights=influence*prior+(1-influence)*acoustic
    env=plan['audio'];energy=float(np.interp(t,np.arange(len(env['energy']))*env['step'],env['energy']))
    # Energy modulates opening, never determines consonant identity.
    openness=.35+.65*np.sqrt(energy)
    for symbol in 'CDEF':
        idx='XABCDEFGH'.index(symbol);removed=weights[idx]*(1-openness);weights[idx]-=removed;weights[0]+=removed
    silence=float(np.clip(energy/.035,0,1));weights*=silence;weights[0]+=1-silence
    return weights/weights.sum()

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('script',type=Path);p.add_argument('words',type=Path);p.add_argument('wav',type=Path);p.add_argument('cues',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    plan=build_plan(a.script.read_text(),json.loads(a.words.read_text()),a.wav,json.loads(a.cues.read_text())['mouthCues'])
    a.output.write_text(json.dumps(plan,indent=2))
