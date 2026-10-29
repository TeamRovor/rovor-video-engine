"""Original waveform/energy/phone timing beside authored jaw excursion."""
import argparse,json,wave
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from duration_cartoon_head import duration_jaw_weights,DurationCartoonHead
from separated_cartoon_head import jaw_weights

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);p.add_argument('--start',type=float,default=8.375);p.add_argument('--end',type=float,default=9.375);a=p.parse_args();plan=json.loads(a.plan.read_text())
    with wave.open(str(a.wav)) as f:
        assert f.getnchannels()==1 and f.getsampwidth()==2;rate=f.getframerate();samples=np.frombuffer(f.readframes(f.getnframes()),'<i2')/32768
    times=np.arange(len(samples))/rate;take=(times>=a.start)&(times<a.end)
    fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[1,1,2]});fig.patch.set_facecolor('#f3eee2')
    for ax in axes:ax.set_facecolor('#faf7ef');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    axes[0].plot(times[take],samples[take],color='#48636d',lw=.45);axes[0].set_ylabel('PCM amplitude');axes[0].set_title('Original audio and forced-aligned phones / duration-sensitive jaw study',loc='left',fontsize=14)
    env=plan['audio'];et=np.arange(len(env['energy']))*env['step'];axes[1].plot(et,env['energy'],color='#b65b3e',lw=2);axes[1].set_ylabel('Existing energy\nenvelope (0–1)');axes[1].set_ylim(0,1.05)
    frame_times=np.arange(round(a.start*48),round(a.end*48)+1)/48
    geometry=DurationCartoonHead().geometry
    aperture=lambda w:sum(v*(geometry[k][7]-geometry[k][6]) for k,v in zip('XABCDEFGH',w))
    axes[2].plot(frame_times,[aperture(jaw_weights(t,plan)) for t in frame_times],'-o',ms=3,color='#888888',label='Previous jaw')
    axes[2].plot(frame_times,[aperture(duration_jaw_weights(t,plan)) for t in frame_times],'-o',ms=3,color='#237c87',label='Duration-sensitive jaw')
    for row in plan['phonemes']:
        if row['end']<=a.start or row['start']>=a.end:continue
        start=max(a.start,row['start']);end=min(a.end,row['end']);axes[2].axvspan(start,end,alpha=.065,color='#b65b3e' if row['phone'].rstrip('012') in ['F','V'] else '#237c87');axes[2].axvline(start,color='#888888',lw=.5,alpha=.5)
        axes[2].text((start+end)/2,1.01,row['phone'],transform=axes[2].get_xaxis_transform(),ha='center',fontsize=9)
    axes[2].set_ylabel('Jaw geometry aperture\n(native pixels)');axes[2].set_xlabel('Original recording time (seconds)');axes[2].legend(loc='upper right');axes[2].set_ylim(bottom=0);axes[2].set_xlim(a.start,a.end)
    fig.text(.08,.02,'Phone boundaries remain unverified. Curves are authored performance controls, not measured mouth anatomy or playback acceptance.',fontsize=9,color='#48636d')
    fig.tight_layout(rect=(0,.045,1,1));a.output.parent.mkdir(parents=True,exist_ok=True);fig.savefig(a.output,dpi=160);plt.close(fig)
