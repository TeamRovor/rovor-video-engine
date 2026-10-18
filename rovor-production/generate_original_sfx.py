"""Generate quiet original Rovor cartoon Foley / UI sounds without purchases.

Entirely procedural 48 kHz PCM: no samples, samples of songs, synthesizer
plugins or downloaded third-party content. Non-destructive, deterministic,
rights-tagged, and intentionally subject to editorial listening approval.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import wave

from audio_library import ROOT, init_library, sha256

RATE = 48000
TWO_PI = 2*math.pi
SOUNDS = {
    "soft-browser-click.wav": ("browser-click", ["browser-click","interface","subtle"],
                              "Dry, subdued browser click with a short wooden transient", .135),
    "button-pop.wav": ("button", ["button","interface","notification"],
                      "Soft, pitched tactile confirmation pop", .22),
    "cartoon-tabletop-tap.wav": ("object-impact", ["object-impact","comic-reaction","foley"],
                                "Subtle damped impact for a prop landing on a table", .38),
    "animated-whoosh.wav": ("whoosh", ["whoosh","transition"],
                           "Smooth, filtered air movement accompanying an object move", .72),
    "logo-shimmer.wav": ("logo-reveal", ["logo-reveal","notification"],
                         "Three gently overlapping original bright chime partials", 1.10),
    "paper-slide.wav": ("paper", ["paper","foley"],
                        "Short textured slide for an illustrated paper prop", .64),
    "two-cartoon-footsteps.wav": ("footsteps", ["footsteps","foley","comic-reaction"],
                                  "Two muted quick rubbery footsteps", .70),
}


def render(kind,t,randomizer,state):
    # All sound characteristics derive from mathematical synthesis, not media.
    if kind=="browser-click":
        return .38*math.exp(-73*t)*randomizer.uniform(-1,1) + .34*math.exp(-35*t)*math.sin(TWO_PI*840*t)
    if kind=="button":
        return .55*math.exp(-23*t)*math.sin(TWO_PI*(320*t+200*t*t)) + .10*math.exp(-55*t)*randomizer.uniform(-1,1)
    if kind=="object-impact":
        return (.64*math.exp(-14*t)*math.sin(TWO_PI*(205*t-58*t*t))+
                .16*math.exp(-52*t)*randomizer.uniform(-1,1))
    if kind=="whoosh":
        # Smoothed noise for airy sweep; envelope is a true physical event.
        white=randomizer.uniform(-1,1)
        state["lp"]=state["lp"]*.925+white*.075
        u=t/.72
        env=(math.sin(math.pi*min(1.,max(0.,u)))**1.8)
        return state["lp"]*1.3*env + .06*env*math.sin(TWO_PI*(200*t+680*t*t))
    if kind=="logo-reveal":
        value=0.
        for offset,f in ((.00,740),(.17,988),(.35,1480)):
            x=t-offset
            if x>=0:
                env=(1-math.exp(-120*x))*math.exp(-6.5*x)
                value+=.3*env*(math.sin(TWO_PI*f*x)+.22*math.sin(TWO_PI*2.005*f*x))
        return value
    if kind=="paper":
        white=randomizer.uniform(-1,1)
        state["lp"]=state["lp"]*.72+white*.28
        u=t/.64
        env=max(0.,math.sin(math.pi*u))*(.45+.25*math.sin(2*math.pi*17*t)**2)
        return state["lp"]*env
    if kind=="footsteps":
        value=0.
        for offset in (.03,.32):
            x=t-offset
            if x>=0:
                value+=.46*math.exp(-24*x)*math.sin(TWO_PI*(128*x-55*x*x))
                if x<.06:
                    value+=.19*math.exp(-60*x)*randomizer.uniform(-1,1)
        return value
    raise ValueError("Unknown local original sound type")


def samples(kind, duration, seed):
    rng=random.Random(seed)
    state={"lp":0.}
    n=round(duration*RATE)
    x=[render(kind,i/RATE,rng,state) for i in range(n)]
    peak=max(abs(v) for v in x) if x else 0.
    if peak<1e-5:
        raise ValueError("Procedural audio unexpectedly silent")
    gain=min(1.,.55/peak)
    smooth=min(160,n//10)
    ints=[]
    for i,v in enumerate(x):
        fade=min(1., i/max(1,smooth), (n-1-i)/max(1,smooth))
        value=max(-.99,min(.99,v*gain*fade))
        ints.append(round(value*32767))
    if not any(ints):
        raise ValueError("Silent output after PCM quantization")
    return ints


def write_pcm(path, values):
    with wave.open(str(path),"wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(struct.pack("<"+str(len(values))+"h",*values))


def produce(root=ROOT):
    root=init_library(root)
    folder=root/"SoundEffects"
    created=[]
    for index,(name,(kind,tags,description,duration)) in enumerate(SOUNDS.items(),1):
        output=folder/name
        meta=folder/(name+".asset.json")
        values=samples(kind,duration,index*1531)
        # Create candidate atomically; never overwrite something supplied or edited by owner.
        if not output.exists():
            temporary=output.with_suffix(".partial.wav")
            write_pcm(temporary,values)
            temporary.replace(output)
            created.append(name)
        if not meta.exists():
            metadata={
                "schemaVersion":1,
                "category":"sound-effect",
                "description":description,
                "eventTags":tags,
                "mood":"playful" if kind in ("object-impact","footsteps") else "subtle",
                "sourceSha256":sha256(output),
                "license":{
                    "kind":"original-owned",
                    "ownerConfirmedRights":True,
                    "source":"Generated for Rovor by original procedural synthesis in generate_original_sfx.py; no third-party samples or music",
                    "evidence":"Source code and deterministic sound construction in Rovor private development branch"
                },
                "listeningReviewStatus":"NOT_ARTISTICALLY_APPROVED",
                "automatedPublishingApproved":False,
            }
            tmp=meta.with_suffix(".partial.json")
            tmp.write_text(json.dumps(metadata,indent=2)+"\n")
            tmp.replace(meta)
    return created


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root",type=Path,default=ROOT)
    args=ap.parse_args()
    created=produce(args.root)
    print("ORIGINAL_ROVOR_SFX_CREATED="+str(len(created)))
    for name in created:
        print("ORIGINAL_SFX="+name)
    print("NO_EXTERNAL_SAMPLES=YES")
    print("CREATIVE_LISTENING_APPROVAL=NOT_YET")


if __name__=="__main__":
    main()
