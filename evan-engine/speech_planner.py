"""Script-to-sound animation planning with audited acoustic forced alignment.
Duration priors and Rhubarb remain explicit fallbacks when alignment is rejected.
"""
import re, wave
from difflib import SequenceMatcher
import numpy as np

OVERRIDES={'rovor':'R OW1 V ER0','favicon':'F AE1 V IH0 K AA0 N'}
VOWELS=set('AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW'.split())
def tokens(text):return re.findall(r"[a-z]+(?:'[a-z]+)?",text.lower())
def shape(phone):
    from english_articulation import PHONE_CATALOG
    return PHONE_CATALOG.get(phone.rstrip('012'),{'targets':['B']})['targets'][0]

def audio_envelope(path):
    with wave.open(str(path)) as f:
        if f.getsampwidth()!=2:raise ValueError('Speech analysis requires PCM16 WAV')
        rate=f.getframerate();x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
        x=x.reshape(-1,f.getnchannels()).mean(axis=1)
    hop=max(1,round(rate*.01));frames=[x[i:i+hop] for i in range(0,len(x),hop)]
    rms=np.array([np.sqrt(np.mean(a*a)) for a in frames]);reference=max(.005,float(np.percentile(rms,90)))
    # Fixed absolute floor prevents silent recordings normalizing into speech.
    energy=np.clip((rms-.002)/reference,0,1)
    kernel=np.array([1,2,3,4,3,2,1],float);kernel/=kernel.sum()
    # Smooth micro-dips without turning every glottal pulse into a jaw twitch.
    energy=np.convolve(np.pad(energy,(3,3),mode='edge'),kernel,mode='valid')
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
    if plan.get('alignment',{}).get('status')=='acoustic':
        return acoustic_weights(t,plan,fallback)
    nearby=[p for p in plan.get('gestures',plan['phonemes']) if p['start']-.08<=t<=p['end']+.08]
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

def acoustic_weights(t,plan,fallback):
    from painted_timing import ease
    # A two-pose English diphthong is ONE acoustic phone. In the opt-in
    # profile, replace its independently timed half-phoneme envelopes with
    # two continuous, complementary strengths over its ORIGINAL phone span.
    from continuous_diphthong import PROFILE, glide_strengths
    glides=plan.get('continuousGlides',[]) if plan.get('coarticulationProfile')==PROFILE else []
    skip={g['phoneIndex'] for g in glides}
    out=np.zeros(9,float);out[0]=.06;contact=0.;fv=0.
    for g in plan.get('gestures',plan['phonemes']):
        if g.get('phoneIndex') in skip:
            continue
        a,b=g['start'],g['end'];center=(a+b)/2;symbol=g['value']
        if abs(t-center)>.25+(b-a)/2:continue
        base=g['phone'].rstrip('012')
        radius=max(.055,min(.14,(b-a)/2+.045))
        distance=abs((t+.018-center)/radius)
        if base in VOWELS:
            # Sustain a long vowel instead of pulsing only at its midpoint.
            strength=float(ease((t-(a-.035))/.060))*(1-float(ease((t-(b-.020))/.065)))
        else:
            strength=(1-distance*distance)**2 if distance<1 else 0.
        salience=1 if base in VOWELS or symbol in 'AGH' else .40
        out['XABCDEFGH'.index(symbol)]+=salience*strength
        envelope=float(ease((t-(a-.045))/.060))*(1-float(ease((t-(b-.010))/.065)))
        if symbol=='A':contact=max(contact,envelope)
        if symbol=='G':fv=max(fv,envelope)
    for glide in glides:
        first,second=glide_strengths(t,glide['start'],glide['end'])
        out['XABCDEFGH'.index(glide['targets'][0])]+=first
        out['XABCDEFGH'.index(glide['targets'][1])]+=second
    out[0]=max(.06,1-out[1:].sum())
    out/=out.sum()
    env=plan['audio'];energy=float(np.interp(t,np.arange(len(env['energy']))*env['step'],env['energy']))
    for symbol in 'CDEF':
        i='XABCDEFGH'.index(symbol);removed=out[i]*(1-(.40+.60*np.sqrt(energy)));out[i]-=removed;out[0]+=removed
    # Sustained silence settles to rest. Silent bilabial closures still retain
    # their contact target; waveform amplitude never decides phone identity.
    gate=1.
    for silence in plan.get('silences',[]):
        a,b=silence['start'],silence['end']
        if b-a<.08:continue
        rest=float(ease((t-a)/.070))*(1-float(ease((t-(b-.070))/.070)))
        gate*=1-rest
    out*=gate;out[0]+=1-gate
    out*=1-fv*.85;out[7]+=fv*.85
    out*=1-contact;out[1]+=contact
    return out/out.sum()

def finalize_plan(plan,wav,fps=48,required=False,coarticulation_profile='legacy'):
    from acoustic_alignment import upgrade_plan
    from english_articulation import phone_gestures,PHONE_CATALOG,cartoon_controls
    plan=upgrade_plan(plan,wav,required)
    plan['gestures']=phone_gestures(plan['phonemes'])
    if coarticulation_profile!='legacy':
        from continuous_diphthong import PROFILE, prepare_glides
        if coarticulation_profile!=PROFILE:
            raise ValueError('Unknown coarticulation profile')
        if plan.get('alignment',{}).get('status')!='acoustic':
            raise ValueError('Continuous diphthongs require audio-grounded phone alignment')
        plan['coarticulationProfile']=PROFILE
        plan['continuousGlides']=prepare_glides(plan['phonemes'],plan['gestures'])
    plan['phoneCatalog']=PHONE_CATALOG
    plan['controlContract']='Normalized animation targets, not anatomical measurements; spelling maps to pronunciation, not one pose per letter'
    n=int(np.ceil(len(plan['audio']['energy'])*plan['audio']['step']*fps))
    plan['controlFps']=fps
    plan['controls']=[dict(time=round(i/fps,6),**{k:round(v,6) for k,v in cartoon_controls(planned_weights(i/fps,plan,plan['fallbackCues'])).items()}) for i in range(n)]
    return plan

if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('script',type=Path);p.add_argument('words',type=Path);p.add_argument('wav',type=Path);p.add_argument('cues',type=Path);p.add_argument('output',type=Path);p.add_argument('--fps',type=int,choices=(24,30,48,60,120),default=48);p.add_argument('--require-alignment',action='store_true');p.add_argument('--coarticulation-profile',choices=('legacy','continuous-diphthong-v1'),default='legacy');a=p.parse_args()
    plan=build_plan(a.script.read_text(),json.loads(a.words.read_text()),a.wav,json.loads(a.cues.read_text())['mouthCues'])
    plan=finalize_plan(plan,a.wav,a.fps,a.require_alignment,a.coarticulation_profile)
    a.output.write_text(json.dumps(plan,indent=2))
