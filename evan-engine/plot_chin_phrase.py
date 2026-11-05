"""Real waveform/spectrum plus oral/chin control curves; no retiming."""
import argparse,json,wave
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from duration_cartoon_head import duration_jaw_weights
from drawn_dental_cartoon_head import DrawnDentalCartoonHead
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('wav',type=Path);p.add_argument('audit',type=Path);p.add_argument('output',type=Path);a=p.parse_args();plan=json.loads(a.plan.read_text());rows=json.loads(a.audit.read_text())['rows'];lo=rows[0]['time'];hi=rows[-1]['time']+1/48
 with wave.open(str(a.wav)) as f:rate=f.getframerate();assert f.getnchannels()==1 and f.getsampwidth()==2;x=np.frombuffer(f.readframes(f.getnframes()),'<i2').astype(float)/32768
 y=x[round(lo*rate):round(hi*rate)];t=lo+np.arange(len(y))/rate;fig,axes=plt.subplots(4,1,figsize=(16,9),dpi=120,layout='constrained');fig.suptitle('Original voice / oral contacts unchanged / independent chin control — not anatomical measurements',fontsize=15)
 axes[0].plot(t,y,lw=.5,color='#315466');axes[0].set_ylabel('PCM amplitude')
 starts=np.arange(0,len(y)-399,80);window=np.hanning(400);segments=np.stack([y[s:s+400] for s in starts]);s=(abs(np.fft.rfft(segments*window[None,:],n=512,axis=1))**2/window.sum()**2).T;freq=np.fft.rfftfreq(512,1/rate);tt=(starts+200)/rate
 axes[1].pcolormesh(tt+lo,freq,10*np.log10(np.maximum(s,1e-10)),shading='auto',vmin=-85,vmax=-25,cmap='magma');axes[1].set_ylim(0,7500);axes[1].set_ylabel('Hz /25ms Hann')
 h=DrawnDentalCartoonHead();openings=np.array([h.geometry[k][7]-h.geometry[k][6] for k in 'XABCDEFGH']);times=np.array([r['time'] for r in rows]);oral=np.array([duration_jaw_weights(t,plan)@openings for t in times]);axes[2].plot(times,oral,color='#315466',label='Same oral aperture in both renders');axes[2].set_ylabel('Oral aperture px');axes[2].legend(loc='upper right')
 axes[3].plot(times,[r['oldChinY']-393 for r in rows],color='#ba684b',label='Current chin');axes[3].plot(times,[r['newChinY']-393 for r in rows],color='#315466',label='Independent chin anchors');axes[3].set_ylabel('Chin Y−rest px');axes[3].set_xlabel('Original recording seconds');axes[3].legend(loc='upper right')
 for ph in plan['phonemes']:
  if ph['value'] not in 'AG' or ph['end']<=lo or ph['start']>=hi:continue
  for ax in axes:ax.axvspan(ph['start'],ph['end'],color='#65c8b6',alpha=.16)
  axes[0].text((ph['start']+ph['end'])/2,.85,ph['phone'],transform=axes[0].get_xaxis_transform(),ha='center',fontsize=9)
 for w in plan['words']:
  if w['end']<=lo or w['start']>=hi:continue
  axes[1].text((max(lo,w['start'])+min(hi,w['end']))/2,.85,w['word'],transform=axes[1].get_xaxis_transform(),ha='center',color='white',fontsize=8)
 for ax in axes:ax.set_xlim(lo,hi)
 fig.savefig(a.output);plt.close(fig)
