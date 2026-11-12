"""Visual acoustic evidence for the longer FV test; no boundary correction."""
import argparse,hashlib,json,wave
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('voice',type=Path);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 with wave.open(str(a.voice)) as f:rate=f.getframerate();raw=f.readframes(f.getnframes())
 signal=np.frombuffer(raw,dtype='<i2').astype(float)/32768;plan=json.loads(a.plan.read_text());windows=[(11.35,11.92,'version / of'),(13.1,13.66,'specifically / for')];fig,axes=plt.subplots(3,2,figsize=(16,8),gridspec_kw={'height_ratios':[1,1,2]});reviews=[]
 for col,(start,end,title) in enumerate(windows):
  lo,hi=round(start*rate),round(end*rate);y=signal[lo:hi];t=lo/rate+np.arange(len(y))/rate;axes[0,col].plot(t,y,lw=.5,color='#294653');axes[0,col].set_title(title);rms=np.sqrt(np.convolve(y*y,np.ones(80)/80,mode='same'));axes[1,col].plot(t,rms,color='#aa4d28')
  n=256;hop=32;frames=np.stack([y[i:i+n]*np.hanning(n) for i in range(0,len(y)-n+1,hop)]);power=20*np.log10(abs(np.fft.rfft(frames))+1e-7)
  axes[2,col].imshow(power.T,origin='lower',aspect='auto',extent=[start+n/2/rate,start+(len(frames)-1)*hop/rate+n/2/rate,0,rate/2],cmap='magma',vmin=-55,vmax=5);axes[2,col].set_ylim(0,5000);axes[2,col].set_xlabel('Original recording time (seconds)')
  phones=[q for q in plan['phonemes'] if q['end']>start and q['start']<end]
  for row in range(3):
   ax=axes[row,col];ax.set_xlim(start,end)
   for q in phones:ax.axvline(q['start'],color='#359dba',lw=.8,alpha=.8)
  for q in phones:axes[0,col].text((max(q['start'],start)+min(q['end'],end))/2,.98,q['phone'],transform=axes[0,col].get_xaxis_transform(),ha='center',va='top',fontsize=10,clip_on=True)
  reviews.append(dict(window=[start,end],sourceSamples=[lo,hi],estimatedPhones=phones))
 for row,label in enumerate(['PCM amplitude','5 ms RMS','Frequency Hz']):axes[row,0].set_ylabel(label)
 fig.suptitle('F/V transition evidence — labels remain unverified estimates',fontsize=18);fig.text(.015,.012,'Original audio; 256-sample FFT / 32-sample hop. These visual windows do not independently verify exact F/V boundaries. No labels moved.',fontsize=11);fig.tight_layout(rect=[0,.04,1,.95]);fig.savefig(a.output/'FV-Acoustic-Evidence.png',dpi=120)
 (a.output/'Acoustic-Review.json').write_text(json.dumps(dict(sourceAudioSha256=hashlib.sha256(a.voice.read_bytes()).hexdigest(),planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),sampleRate=rate,windows=reviews,timingChanged=False,exactBoundariesVerified=False,independentListening=False),indent=2)+'\n')
