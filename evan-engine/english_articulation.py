"""General American English ARPABET -> cartoon articulation, not letter poses.
39 base phones. Silent letters and digraphs are handled by word pronunciation.
Targets are animation controls, not measurements of a particular speaker's lips.
"""
VOWELS={
 'AA':('open back',('D',)), 'AE':('open front',('D',)),
 'AH':('central',('C',)), 'AO':('rounded back',('E',)),
 'AW':('open to rounded',('D','F')), 'AY':('open to front',('C','B')),
 'EH':('mid front',('C',)), 'ER':('rhotic central',('C',)),
 'EY':('mid to front',('C','B')), 'IH':('near-close front',('B',)),
 'IY':('close front',('B',)), 'OW':('rounded glide',('E','F')),
 'OY':('rounded to front',('E','B')), 'UH':('near-close rounded',('F',)),
 'UW':('close rounded',('F',)),
}
CONSONANTS={
 'B':('bilabial stop','A'), 'CH':('postalveolar affricate','B'),
 'D':('alveolar stop','B'), 'DH':('dental fricative','H'),
 'F':('labiodental fricative','G'), 'G':('velar stop','B'),
 'HH':('glottal fricative','C'), 'JH':('postalveolar affricate','B'),
 'K':('velar stop','B'), 'L':('alveolar lateral','H'),
 'M':('bilabial nasal','A'), 'N':('alveolar nasal','B'),
 'NG':('velar nasal','B'), 'P':('bilabial stop','A'),
 'R':('rhotic approximant','B'), 'S':('alveolar fricative','B'),
 'SH':('postalveolar fricative','B'), 'T':('alveolar stop','B'),
 'TH':('dental fricative','H'), 'V':('labiodental fricative','G'),
 'W':('rounded approximant','F'), 'Y':('palatal approximant','B'),
 'Z':('alveolar fricative','B'), 'ZH':('postalveolar fricative','B'),
}
PHONE_CATALOG={p:dict(kind='vowel',description=desc,targets=list(targets)) for p,(desc,targets) in VOWELS.items()}
PHONE_CATALOG.update({p:dict(kind='consonant',description=desc,targets=[target]) for p,(desc,target) in CONSONANTS.items()})

def phone_gestures(phones):
    """Expand diphthongs into timed overlapping targets; keep original phone IDs."""
    result=[]
    for i,phone in enumerate(phones):
        base=phone['phone'].rstrip('012');targets=PHONE_CATALOG.get(base,{}).get('targets',[phone['value']])
        a,b=phone['start'],phone['end'];span=b-a
        for phase,target in enumerate(targets):
            row=dict(phone,value=target,phoneIndex=i,phase=phase)
            # Two targets transition through the vowel; no new sound boundary.
            row['start']=a+span*phase/len(targets);row['end']=a+span*(phase+1)/len(targets)
            result.append(row)
    return result

def cartoon_controls(weights):
    """Stable normalized control contract for a future cartoon rig as well as mesh."""
    w=dict(zip('XABCDEFGH',map(float,weights)))
    return dict(jawOpen=min(1,.10*w['B']+.46*w['C']+.84*w['D']+.30*w['E']+.15*w['F']+.12*w['H']),
                lipSeal=w['A'],lipRound=min(1,.7*w['E']+w['F']),
                lipSpread=min(1,.8*w['B']+.3*w['C']),lowerLipContact=w['G'],tongueVisible=w['H'])
