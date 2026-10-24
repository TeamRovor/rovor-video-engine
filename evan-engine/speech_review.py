"""Export waveform, spectrogram, mouth controls and word/phone evidence."""
import argparse,json,wave
from pathlib import Path
import numpy as np

def render_review(plan,wav,output,start=0,duration=2.5):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from speech_planner import planned_weights
    with wave.open(str(wav)) as f:
        rate=f.getframerate();channels=f.getnchannels()
        x=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,channels).mean(axis=1)/32768
    end=min(start+duration,len(x)/rate)
    if start<0 or end<=start:raise ValueError('Choose a non-empty review interval inside the recording')
    p=plan;acoustic=p.get('alignment',{}).get('status')=='acoustic'
    fig,axes=plt.subplots(5,1,figsize=(18,11),sharex=True,gridspec_kw={'height_ratios':[2,2,1,1,1]})
    waveform,spectrum,controls,words,phones=axes
    time=np.arange(len(x))/rate;keep=(time>=start)&(time<=end)
    waveform.plot(time[keep][::4],x[keep][::4],lw=.5,color='#315674');waveform.set_ylabel('Actual waveform')
    from speech_alignment_audit import spectrum as measured_spectrum
    first=round(start*rate);last=round(end*rate)
    db,centers,frequencies=measured_spectrum(x[first:last],rate,first)
    if len(centers):
        spectrum.pcolormesh(centers,frequencies,db,shading='nearest',vmin=db.max()-70,vmax=db.max(),cmap='magma')
    spectrum.set_ylim(0,min(6000,rate/2));spectrum.set_ylabel('Spectrum (Hz)')
    e=p['audio'];controls.plot(np.arange(len(e['energy']))*e['step'],e['energy'],label='Measured energy',alpha=.5)
    q=np.arange(start,end,1/240);weights=np.array([planned_weights(t,p,p['fallbackCues']) for t in q])
    controls.plot(q,weights[:,3:7].sum(axis=1),label='Vowel opening weight')
    controls.plot(q,weights[:,1],label='MBP contact',alpha=.7);controls.legend(loc='upper right',fontsize=8);controls.set_ylabel('Planned weights')
    for i,w in enumerate(p['words']):
        if w['end']<start or w['start']>end:continue
        flagged=bool(w.get('reviewFlags'))
        words.axvspan(w['start'],w['end'],color='#ce7862' if flagged else '#497fa5',alpha=.18 if i%2 else .30)
        words.text((w['start']+w['end'])/2,.3,w['word']+('*' if flagged else ''),ha='center',fontsize=10,rotation=25,clip_on=True)
    for phone in p['phonemes']:
        if phone['end']<start or phone['start']>end:continue
        phones.text((phone['start']+phone['end'])/2,.3,phone['phone']+'\n'+phone['value'],ha='center',fontsize=8,clip_on=True)
        phones.axvline(phone['start'],lw=.5,alpha=.3)
    words.set_ylabel('Aligned words *' if acoustic else 'Word estimates');phones.set_ylabel('Aligned phone\n/ initial mouth' if acoustic else 'Estimated phone\n/ mouth');phones.set_xlabel('Recording time (seconds)')
    for ax in axes:ax.set_xlim(start,end)
    for ax in (waveform,controls,words,phones):ax.grid(axis='x',alpha=.2)
    fig.suptitle('Evan speech review: script + recording\n'+(p['alignment']['method']+'; * = word/phone evidence requiring review' if acoustic else 'Estimated phone boundaries; acoustic alignment unavailable'))
    fig.tight_layout();fig.savefig(output,dpi=150);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=float,default=0);p.add_argument('--duration',type=float,default=2.5);p.add_argument('--audit-dir',type=Path);a=p.parse_args()
    plan=json.loads(a.plan.read_text())
    render_review(plan,a.wav,a.output,a.start,a.duration)
    if a.audit_dir and plan.get('alignment',{}).get('status')=='acoustic':
        from speech_alignment_audit import audit
        audit(plan,a.wav,a.audit_dir)
