"""Export recording waveform, planned mouth weights and word/phone evidence."""
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
    end=min(start+duration,len(x)/rate);p=plan
    fig,axes=plt.subplots(4,1,figsize=(18,9),sharex=True,gridspec_kw={'height_ratios':[2,1,1,1]})
    time=np.arange(len(x))/rate;keep=(time>=start)&(time<=end)
    axes[0].plot(time[keep][::4],x[keep][::4],lw=.5,color='#315674');axes[0].set_ylabel('Actual waveform')
    e=p['audio'];axes[1].plot(np.arange(len(e['energy']))*e['step'],e['energy'],label='Measured energy',alpha=.5)
    q=np.arange(start,end,1/240);weights=np.array([planned_weights(t,p,p['fallbackCues']) for t in q])
    axes[1].plot(q,weights[:,3:7].sum(axis=1),label='Vowel opening weight')
    axes[1].plot(q,weights[:,1],label='MBP contact',alpha=.6);axes[1].legend(loc='upper right');axes[1].set_ylabel('Planned weights')
    for i,w in enumerate(p['words']):
        if w['end']<start or w['start']>end:continue
        axes[2].axvspan(w['start'],w['end'],alpha=.12 if i%2 else .24)
        axes[2].text((w['start']+w['end'])/2,.3,w['word'],ha='center',fontsize=10,rotation=25,clip_on=True)
    for phone in p['phonemes']:
        if phone['end']<start or phone['start']>end:continue
        axes[3].text((phone['start']+phone['end'])/2,.3,phone['phone']+'\n'+phone['value'],ha='center',fontsize=8,clip_on=True)
        axes[3].axvline(phone['start'],lw=.5,alpha=.3)
    axes[2].set_ylabel('Word estimates');axes[3].set_ylabel('Estimated phone\n/ mouth');axes[3].set_xlabel('Recording time (seconds)')
    for ax in axes:ax.set_xlim(start,end);ax.grid(axis='x',alpha=.2)
    fig.suptitle('Evan speech review: script + recording\nExperimental word anchors; phone boundaries are duration estimates, NOT forced alignment')
    fig.tight_layout();fig.savefig(output,dpi=150);plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=float,default=0);p.add_argument('--duration',type=float,default=2.5);a=p.parse_args()
    render_review(json.loads(a.plan.read_text()),a.wav,a.output,a.start,a.duration)
