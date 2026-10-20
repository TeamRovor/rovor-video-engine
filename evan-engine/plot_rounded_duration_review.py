"""Three AO waveform/spectrum/control comparisons; no alignment acceptance."""
import argparse,json,wave
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text());rows=json.loads(a.audit.read_text())['rows']
 with wave.open(str(a.wav)) as f:rate=f.getframerate();assert f.getsampwidth()==2 and f.getnchannels()==1;audio=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
 fig,axes=plt.subplots(3,3,figsize=(16,9),dpi=120,layout='constrained');fig.suptitle('Original AO labels / waveform + spectrum / same timing, conservative height — boundaries unverified',fontsize=14)
 for c,(word,lo,hi) in enumerate([('small',15.2,15.65),('more',18.3,18.75),('all',20.2,20.7)]):
  y=audio[round(lo*rate):round(hi*rate)];axes[0,c].plot(lo+np.arange(len(y))/rate,y,lw=.5,color='#315466');ph=next(p for p in plan['phonemes'] if p['word']==word and p['phone']=='AO');axes[0,c].set_title(f'{word} / existing AO span{(ph["end"]-ph["start"])*1000:.0f}ms')
  starts=np.arange(0,len(y)-399,80);win=np.hanning(400);seg=np.stack([y[i:i+400] for i in starts]);s=(abs(np.fft.rfft(seg*win,n=512))**2/win.sum()**2).T;axes[1,c].pcolormesh(lo+(starts+200)/rate,np.fft.rfftfreq(512,1/rate),10*np.log10(np.maximum(s,1e-10)),shading='auto',vmin=-85,vmax=-25,cmap='magma');axes[1,c].set_ylim(0,7500)
  rr=[r for r in rows if lo<=r['time']<=hi];times=[r['time'] for r in rr];axes[2,c].plot(times,[r['oldAperture'] for r in rr],color='#ba684b',label='Current');axes[2,c].plot(times,[r['newAperture'] for r in rr],color='#315466',label='AO height study');axes[2,c].set_ylim(0,36);axes[2,c].set_xlabel('Original recording seconds');axes[2,c].legend(loc='upper right',fontsize=8)
  for p in plan['phonemes']:
   if p['end']<=lo or p['start']>=hi:continue
   for ax in axes[:,c]:
    ax.axvline(p['start'],color='#65a79f',lw=.7,ls='--')
    if p['phone']=='AO':ax.axvspan(p['start'],p['end'],color='#65c8b6',alpha=.15)
   axes[0,c].text((max(lo,p['start'])+min(hi,p['end']))/2,.85,p['phone'],transform=axes[0,c].get_xaxis_transform(),ha='center',fontsize=8)
  for ax in axes[:,c]:ax.set_xlim(lo,hi)
 axes[0,0].set_ylabel('PCM amplitude');axes[1,0].set_ylabel('Hz /25ms Hann,5ms hop');axes[2,0].set_ylabel('Source control aperture px');fig.savefig(a.output);plt.close(fig)
