"""Independent word-anchor evidence review; never rewrites alignment timings.

Low energy is not proof of silence: stops, fricatives and breathing require
phonetic review. Plots compare both timelines on the recording's sample clock.
"""
import argparse,hashlib,json,wave
from pathlib import Path
import numpy as np

def read_audio(path):
    with wave.open(str(path)) as f:
        if f.getsampwidth()!=2:raise ValueError('Review expects PCM16 audio')
        rate=f.getframerate();channels=f.getnchannels()
        x=np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,channels).mean(axis=1)/32768
    return x,rate

def spectrum(x,rate,start_sample=0):
    size=max(32,round(rate*.025));hop=max(1,round(rate*.005))
    if len(x)<size:return np.empty((size//2+1,0)),np.array([]),np.fft.rfftfreq(size,1/rate)
    frames=np.lib.stride_tricks.sliding_window_view(x,size)[::hop]
    db=20*np.log10(np.maximum(abs(np.fft.rfft(frames*np.hanning(size),axis=1)),1e-7))
    # FFT windows are centered in time, not stretched to the clip endpoints.
    times=(start_sample+np.arange(len(frames))*hop+(size-1)/2)/rate
    return db.T,times,np.fft.rfftfreq(size,1/rate)

def flagged_regions(plan,duration,padding=.18):
    anchors={w['scriptIndex']:w for w in plan.get('estimatedWords',[])}
    rows=[]
    for w in plan['words']:
        if not w.get('reviewFlags'):continue
        anchor=anchors.get(w['scriptIndex'])
        rows.append(dict(scriptIndex=w['scriptIndex'],word=w['word'],acoustic=[w['start'],w['end']],anchor=[anchor['start'],anchor['end']] if anchor else None,flags=w['reviewFlags'],status='unreviewed',boundaryStatus='unresolved'))
    groups=[]
    for row in rows:
        anchor=row['anchor'] or row['acoustic']
        a=max(0,min(row['acoustic'][0],anchor[0])-padding);b=min(duration,max(row['acoustic'][1],anchor[1])+padding)
        if groups and a<=groups[-1]['end']+.35:groups[-1]['end']=max(groups[-1]['end'],b);groups[-1]['indices'].append(row['scriptIndex'])
        else:groups.append(dict(start=a,end=b,indices=[row['scriptIndex']]))
    return rows,groups

def energy_fraction(x,rate,interval,threshold_db=-40):
    a=max(0,round(interval[0]*rate));b=min(len(x),round(interval[1]*rate));size=max(1,round(rate*.02))
    frames=[x[i:min(i+size,b)] for i in range(a,b,size)]
    rms=np.array([np.sqrt(np.mean(f*f)) for f in frames if len(f)])
    return float(np.mean(20*np.log10(np.maximum(rms,1e-9))<threshold_db)) if len(rms) else None

def phone_audio_support(phones,x,rate):
    """Flag long assigned phones containing a sustained quiet run, never retime.

    Fixed -40dBFS/60ms thresholds are review heuristics, not silence/phone labels.
    Each20ms bin is entirely inside its phone; partial trailing bins are omitted.
    """
    # shortcut: fixed amplitude thresholds are review-only; calibrate before any automatic timing/pose decision.
    rows=[];size=max(1,round(rate*.02))
    for index,phone in enumerate(phones):
        if phone['end']-phone['start']<.25:continue
        a=max(0,round(phone['start']*rate));b=min(len(x),round(phone['end']*rate))
        bins=[(i,float(np.sqrt(np.mean(x[i:i+size]**2)))) for i in range(a,b-size+1,size)]
        longest=run=0;first=best=0
        for i,(sample,rms) in enumerate(bins):
            if rms<.01:
                if not run:first=sample
                run+=size
                if run>longest:longest=run;best=first
            else:run=0
        if longest/rate<.06:continue
        rows.append(dict(phoneIndex=index,scriptIndex=phone.get('scriptIndex'),word=phone['word'],phone=phone['phone'],assigned=[phone['start'],phone['end']],lowEnergyRun=[best/rate,(best+longest)/rate],thresholdDbFS=-40,binSamples=size,flag='long-phone-low-energy-run',boundaryStatus='unresolved',timingChanged=False))
    return rows

def plot_group(plan,x,rate,group,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    a=round(group['start']*rate);b=round(group['end']*rate);signal=x[a:b]
    fig,axes=plt.subplots(5,1,figsize=(18,9),sharex=True,gridspec_kw={'height_ratios':[2,2,1,1,1]})
    axes[0].plot(np.arange(a,b)/rate,signal,lw=.55,color='#254c61');axes[0].set_ylabel('Waveform')
    db,times,freq=spectrum(signal,rate,a)
    if len(times):axes[1].pcolormesh(times,freq,db,shading='nearest',cmap='magma',vmin=db.max()-65,vmax=db.max())
    axes[1].set_ylim(0,min(6000,rate/2));axes[1].set_ylabel('Hz')
    for ax,key,label,color in [(axes[2],'words','Acoustic words','#347d87'),(axes[3],'estimatedWords','Whisper anchors','#b77639')]:
        for w in plan[key]:
            if w['end']<group['start'] or w['start']>group['end']:continue
            ax.axvspan(w['start'],w['end'],alpha=.2,color=color);ax.axvline(w['start'],color=color,lw=.7)
            ax.text((w['start']+w['end'])/2,.45,w['word'],ha='center',va='center',rotation=20,fontsize=10,clip_on=True)
        ax.set_ylabel(label);ax.set_ylim(0,1);ax.set_yticks([])
    for p in plan['phonemes']:
        if p['end']<group['start'] or p['start']>group['end']:continue
        axes[4].axvline(p['start'],lw=.6,color='#597280');axes[4].text((p['start']+p['end'])/2,.5,p['phone'],ha='center',fontsize=8,clip_on=True)
    axes[4].set_ylim(0,1);axes[4].set_yticks([]);axes[4].set_ylabel('Acoustic phones');axes[4].set_xlabel('Recording time (seconds)')
    for ax in axes:ax.set_xlim(a/rate,b/rate);ax.grid(axis='x',alpha=.2)
    fig.suptitle('Word-boundary audit: two hypotheses against the same recording\nNeither recognizer is ground truth; quiet intervals may contain consonants or breath.')
    fig.tight_layout();fig.savefig(output,dpi=120);plt.close(fig)

def audit(plan,wav,output):
    x,rate=read_audio(wav);rows,groups=flagged_regions(plan,len(x)/rate);output.mkdir(parents=True,exist_ok=True)
    for row in rows:
        row['anchorOutsideRecording']=(row['anchor'][0]<0 or row['anchor'][1]>len(x)/rate) if row['anchor'] else None
        row['energyMeasurementNote']='20 ms RMS windows; intervals clipped to recording; not a speech classifier'
        row['lowEnergyFractionBelowMinus40dBFS']={name:energy_fraction(x,rate,row[name]) if row[name] is not None else None for name in ('acoustic','anchor')}
    for i,g in enumerate(groups,1):
        g['plot']=f'Region-{i:02}.png';g['audio']=f'Region-{i:02}.wav';plot_group(plan,x,rate,g,output/g['plot'])
        with wave.open(str(output/g['audio']),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate);f.writeframes((np.clip(x[round(g['start']*rate):round(g['end']*rate)],-1,1)*32767).astype('<i2').tobytes())
    report=dict(version=1,audioSha256=hashlib.sha256(wav.read_bytes()).hexdigest(),canonicalPlanSha256=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest(),sampleRate=rate,words=rows,regions=groups,timingsModified=False,note='Energy is supporting evidence only, never an automatic word-boundary correction.')
    (output/'Timing-Audit.json').write_text(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=audit(json.loads(a.plan.read_text()),a.wav,a.output);print(json.dumps(dict(words=len(r['words']),regions=len(r['regions']))))
