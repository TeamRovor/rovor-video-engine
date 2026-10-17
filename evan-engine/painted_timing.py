"""Continuous speech coarticulation and velocity-continuous authored motion."""
from functools import lru_cache
import math
import numpy as np

SYMBOLS='XABCDEFGH'

def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)

@lru_cache(maxsize=8)
def anchors(rows):
    # Very brief recognizer alternations should not throw the entire jaw open.
    # Preserve contact sounds; short vowels share neighbouring articulations.
    result=[]
    for start,end,symbol in rows:
        if end-start<.04 and symbol not in 'AXG':continue
        center=(start+end)/2
        result.append((center,symbol,start,end))
    return result

def speech_weights(t,cues):
    rows=tuple((float(c['start']),float(c['end']),c['value']) for c in cues)
    a=anchors(rows);out=np.zeros(9,np.float32);out[0]=.055
    if not a:out[0]=1;return out
    # Compact temporal kernels overlap neighbouring gestures. Anticipation is
    # 25ms, rather than restarting a new previous->target tween at every boundary.
    for center,symbol,start,end in a:
        radius=max(.09,min(.16,(end-start)/2+.075))
        distance=abs((t+.025-center)/radius)
        if distance<1:out[SYMBOLS.index(symbol)]+=(1-distance*distance)**2
    if out.sum()<1e-8:out[0]=1
    else:out/=out.sum()
    # A real lip closure is reached around the middle of MBP, approached and
    # released continuously. No instant jump to a fully closed source image.
    closure=0.
    for center,symbol,start,end in a:
        if symbol!='A':continue
        radius=max(.045,min(.095,(end-start)/2+.035))
        distance=abs(t-center)
        hold=min(.012,(end-start)*.18)
        envelope=1-float(ease((distance-hold)/max(.001,radius-hold)))
        closure=max(closure,envelope)
    out*=1-closure;out[1]+=closure
    # Conversational jaw range: wide-AH is an accent, not the default vowel.
    # Retain its painted shape while reducing the sustained maximum opening.
    out[3]+=out[4]*.30;out[4]*=.70
    return out

def flowing_track(t,keys):
    """Monotone cubic Hermite: pass through keys without stopping at each key."""
    if len(keys)==1 or t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    times=np.array([p[0] for p in keys],float);values=np.array([p[1] for p in keys],float)
    slopes=np.diff(values)/np.diff(times);tangents=np.zeros(len(keys))
    for i in range(1,len(keys)-1):
        if slopes[i-1]*slopes[i]>0:
            h0=times[i]-times[i-1];h1=times[i+1]-times[i]
            w0=2*h1+h0;w1=h1+2*h0
            tangents[i]=(w0+w1)/(w0/slopes[i-1]+w1/slopes[i])
    j=int(np.searchsorted(times,t)-1);h=times[j+1]-times[j];u=(t-times[j])/h
    return float((2*u**3-3*u*u+1)*values[j]+(u**3-2*u*u+u)*h*tangents[j]+(-2*u**3+3*u*u)*values[j+1]+(u**3-u*u)*h*tangents[j+1])
