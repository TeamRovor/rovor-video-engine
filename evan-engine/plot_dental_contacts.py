"""Waveform/spectrogram context for existing DH/TH anchors; no retiming."""
import argparse,json,wave
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('output',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text())
 with wave.open(str(a.wav)) as f:rate=f.getframerate();assert f.getnchannels()==1 and f.getsampwidth()==2;x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
 fig,axes=plt.subplots(4,1,figsize=(16,9),dpi=120,layout='constrained');fig.suptitle('Original recording / existing dental-phone anchors — boundaries not independently verified',fontsize=15)
 for k,(lo,hi,word,target) in enumerate([(1.6,2.1,'that','DH'),(6.5,7.05,'thing','TH')]):
  y=x[round(lo*rate):round(hi*rate)];t=lo+np.arange(len(y))/rate;axes[2*k].plot(t,y,lw=.5,color='#315466');axes[2*k].set_ylabel('Waveform');axes[2*k].set_title(f'{word} / {target}: waveform +25ms Hann,5ms hop spectrogram; labels are existing alignment')
  starts=np.arange(0,len(y)-399,80);window=np.hanning(400);segments=np.stack([y[start:start+400] for start in starts]);s=(np.abs(np.fft.rfft(segments*window[None,:],n=512,axis=1))**2/window.sum()**2).T;f=np.fft.rfftfreq(512,1/rate);tt=(starts+200)/rate;axes[2*k+1].pcolormesh(tt+lo,f,10*np.log10(np.maximum(s,1e-10)),shading='auto',vmin=-85,vmax=-25,cmap='magma');axes[2*k+1].set_ylim(0,7500);axes[2*k+1].set_ylabel('Hz');axes[2*k+1].set_xlabel('Original recording seconds')
  for ph in plan['phonemes']:
   if ph['end']<=lo or ph['start']>=hi:continue
   for ax in axes[2*k:2*k+2]:
    ax.axvline(ph['start'],color='#69a8a3',lw=.7,ls='--');ax.set_xlim(lo,hi)
    if ph['phone']==target:ax.axvspan(ph['start'],ph['end'],color='#65c8b6',alpha=.15)
   axes[2*k].text((max(lo,ph['start'])+min(hi,ph['end']))/2,.85,ph['phone'],transform=axes[2*k].get_xaxis_transform(),ha='center',fontsize=9)
 fig.savefig(a.output);plt.close(fig)
