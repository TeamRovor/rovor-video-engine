"""Visual audit of the existing small/M-to-AO release labels; never retimes them."""
from pathlib import Path
import argparse,hashlib,wave,json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser(description=__doc__);p.add_argument('voice',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);args=p.parse_args();voice=args.voice;out=args.output;out.mkdir(parents=True,exist_ok=True)
with wave.open(str(voice)) as f:rate=f.getframerate();f.setpos(240000);raw=f.readframes(10400)
y=np.frombuffer(raw,dtype='<i2').astype(float)/32768;t=15+np.arange(len(y))/rate
plan=json.loads(args.plan.read_text());phones=[p for p in plan['phonemes'] if p['end']>15 and p['start']<15.65]
fig,axs=plt.subplots(3,1,figsize=(16,8),sharex=True,gridspec_kw={'height_ratios':[1,1,2]})
axs[0].plot(t,y,lw=.5,color='#294653');axs[0].set_ylabel('PCM amplitude')
win=80;rms=np.sqrt(np.convolve(y*y,np.ones(win)/win,mode='same'));axs[1].plot(t,rms,color='#aa4d28');axs[1].set_ylabel('5 ms RMS')
n=256;hop=32;frames=np.stack([y[i:i+n]*np.hanning(n) for i in range(0,len(y)-n+1,hop)]);power=20*np.log10(abs(np.fft.rfft(frames))+1e-7)
axs[2].imshow(power.T,origin='lower',aspect='auto',extent=[15+n/2/rate,15+(len(frames)-1)*hop/rate+n/2/rate,0,rate/2],cmap='magma',vmin=-55,vmax=5);axs[2].set_ylim(0,5000);axs[2].set_ylabel('Frequency Hz');axs[2].set_xlabel('Original recording time (seconds)')
for ax in axs:
 ax.set_xlim(15.24,15.62)
 for p in phones:
  ax.axvline(p['start'],color='#359dba',lw=.8,alpha=.8)
for p in phones:
 if p['end']>15.24 and p['start']<15.62:axs[0].text((max(p['start'],15.24)+min(p['end'],15.62))/2,.98,p['phone'],transform=axs[0].get_xaxis_transform(),ha='center',va='top',fontsize=11,clip_on=True)
for i in [740,741,742]:axs[1].axvline(i/48,color='#b3247d',ls='--',lw=1);axs[1].text(i/48,.96,str(i),transform=axs[1].get_xaxis_transform(),rotation=90,va='top',ha='right')
fig.suptitle('“small” release evidence — existing phone labels are estimates, not verified boundaries',fontsize=17)
fig.text(.01,.01,'Voiced energy continues through the M region; amplitude alone cannot identify the release. No phone labels moved. Magenta marks reviewed 48 fps frames.',fontsize=11)
fig.tight_layout(rect=[0,.035,1,.95]);fig.savefig(out/'Release-Acoustic-Evidence.png',dpi=120)
(out/'Acoustic-Review.json').write_text(json.dumps({'sourceAudioSha256':hashlib.sha256(voice.read_bytes()).hexdigest(),'planSha256':hashlib.sha256(args.plan.read_bytes()).hexdigest(),'range':[15.24,15.62],'sourceSampleRange':[240000,250400],'sampleRate':rate,'rmsWindowSamples':80,'fftWindowSamples':256,'fftHopSamples':32,'phoneLabels':phones,'timingChanged':False,'exactBoundariesVerified':False,'limits':'Waveform/RMS and spectrogram are visual evidence only; voiced M has energy and simple energy peaks cannot locate phone boundaries exactly.'},indent=2)+'\n')
