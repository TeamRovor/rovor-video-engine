"""Original instrumental score sketches for Rovor cartoons.

Three deterministic 48k stereo compositions. No third-party sounds, models,
samples or paid tools. These are editorial audition drafts, not finished scores.
Never overwrite music from the user. NumPy is already in Rovor's render venv.
"""
import argparse
import json
import math
from collections import OrderedDict
from pathlib import Path
import wave
import numpy as np
from audio_library import ROOT, init_library, sha256, scan

SR=48000
RATE=SR  # Compat alias for library sample-rate test and future render adapters
BARS=24
SCORES=OrderedDict([
 ("curious-expedition",dict(bpm=96,mood="curious",tags=["curious","explainer","discovery","under-dialogue"],
  chords=[(48,[0,3,7,10]),(53,[0,4,7,9]),(55,[0,3,7,10]),(51,[0,4,7,11])],
  kind="bell",melody=.16,pad=.13,bass=.11,
  description="Warm exploration music with shimmering soft keys, flowing arpeggios and subdued rhythm.")),
 ("playful-mechanics",dict(bpm=120,mood="playful",tags=["playful","comedy","cartoon","action","under-dialogue"],
  chords=[(50,[0,4,7,9]),(55,[0,4,7,11]),(52,[0,3,7,10]),(57,[0,3,7,10])],
  kind="pluck",melody=.24,pad=.08,bass=.17,
  description="Bouncy plucked-note figures, little rhythmic clicks and playful bass motion.")),
 ("quiet-new-ground",dict(bpm=104,mood="inspiring",tags=["inspiring","cinematic","growth","journey","under-dialogue"],
  chords=[(45,[0,3,7,10]),(48,[0,4,7,11]),(53,[0,4,7,9]),(50,[0,4,7,9])],
  kind="soft",melody=.14,pad=.18,bass=.08,
  description="A gentle cinematic progression with soft evolving chords and clear melodic notes.")),
])


def tone(midi,seconds,instrument):
    n=max(2,round(seconds*SR))
    t=np.arange(n,dtype=np.float32)/SR
    hz=440*(2**((midi-69)/12))
    phase=(2*np.pi*hz*t)
    if instrument=="bass":
        sound=np.sin(phase)+.12*np.sin(2*phase)
        env=(1-np.exp(-80*t))*np.exp(-4*t/max(seconds,.1))
    elif instrument=="pad":
        sound=.6*np.sin(phase)+.25*np.sin(2.005*phase)+.16*np.sin(.997*phase)
        env=np.minimum(1,t/.25)*np.minimum(1,(seconds-t)/.32)
    elif instrument=="bell":
        sound=np.sin(phase)+.27*np.sin(2.002*phase)+.12*np.sin(3.98*phase)
        env=(1-np.exp(-120*t))*np.exp(-3.2*t/max(seconds,.1))
    elif instrument=="pluck":
        sound=np.sin(phase)+.32*np.sin(2*phase)+.07*np.sin(3.01*phase)
        env=(1-np.exp(-140*t))*np.exp(-5*t/max(seconds,.1))
    elif instrument=="soft":
        sound=np.sin(phase)+.13*np.sin(2.003*phase)
        env=(1-np.exp(-60*t))*np.exp(-3*t/max(seconds,.1))
    else:
        raise ValueError("Unknown score instrument")
    out=np.asarray(sound*env,dtype=np.float32)
    fade=min(128,n//8)
    if fade>=2:
        ramp=np.linspace(0,1,fade,dtype=np.float32)
        out[:fade]*=ramp
        out[-fade:]*=ramp[::-1]
    return out


def place(mix,event,start,level,pan=0):
    i=round(start*SR)
    if i<0 or i>=len(mix):return
    last=min(len(mix),i+len(event))
    segment=event[:last-i]*level
    left=math.sqrt((1-pan)/2)
    right=math.sqrt((1+pan)/2)
    mix[i:last,0]+=segment*left
    mix[i:last,1]+=segment*right


def render_score(name,bars=BARS):
    if name not in SCORES or isinstance(bars,bool) or not isinstance(bars,int) or not 1<=bars<=BARS:
        raise ValueError("Unknown score or invalid bars")
    cfg=SCORES[name]
    beat=60/cfg["bpm"]
    bar=beat*4
    seconds=bars*bar
    mix=np.zeros((round(seconds*SR),2),dtype=np.float32)
    rng=np.random.default_rng(42)
    for bar_index in range(bars):
        base,offsets=cfg["chords"][bar_index%len(cfg["chords"])]
        pitches=[base+12+offset for offset in offsets]
        start=bar_index*bar
        for j,pitch in enumerate(pitches):
            place(mix,tone(pitch,bar*.98,"pad"),start,
                  cfg["pad"]*(.65 if j else .9),-.6+j*.4)
        for step in range(8):
            pitch=pitches[(step+bar_index//2)%len(pitches)]
            if step==7 and bar_index%4==3:pitch+=12
            place(mix,tone(pitch,beat*.66,cfg["kind"]),
                  start+step*beat/2,cfg["melody"]*(.85 if step%4==0 else .59),
                  -.35 if step%2==0 else .35)
        for step in range(4):
            place(mix,tone(base-12 if base>46 else base,beat*.75,"bass"),
                  start+step*beat,cfg["bass"]*(1.1 if step==0 else .56),-.1)
            if (step+bar_index)%3==0:
                # Original tiny transient, no drum samples.
                n=round(.06*SR)
                x=np.arange(n,dtype=np.float32)/SR
                click=(rng.normal(0,1,n).astype(np.float32)*np.exp(-115*x)+
                       .4*np.sin(2*np.pi*320*x)*np.exp(-80*x))
                place(mix,click,start+step*beat,.012,.2)
    # Small cross-channel room echo; all source samples original.
    delay=round(.19*SR)
    mix[delay:,0]+=mix[:-delay,1].copy()*.09
    mix[delay:,1]+=mix[:-delay,0].copy()*.09
    peak=float(np.max(np.abs(mix)))
    if peak<=0 or not np.isfinite(peak):raise ValueError("Empty or invalid music")
    mix*=min(1.,.46/peak)
    fade=round(.32*SR)
    ramp=np.linspace(0,1,fade,dtype=np.float32)
    mix[:fade]*=ramp[:,None]
    mix[-fade:]*=ramp[::-1,None]
    if not np.isfinite(mix).all() or np.max(np.abs(mix))>.9:
        raise ValueError("Unsafe PCM output")
    return mix,seconds


def write_audio(path,mix):
    pcm=np.rint(mix*32767).clip(-32768,32767).astype("<i2")
    with wave.open(str(path),"wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())


def build(root=ROOT,bars=BARS):
    root=init_library(root)
    folder=root/"BackgroundMusic"
    created=[]
    for key,cfg in SCORES.items():
        filename="rovor-"+key+".wav"
        audio=folder/filename
        sidecar=folder/(filename+".asset.json")
        if audio.is_symlink() or sidecar.is_symlink():
            raise ValueError("Symlinked audio is not accepted")
        mix,seconds=render_score(key,bars)
        temp=folder/(filename+".generated.partial.wav")
        try:
            write_audio(temp,mix)
            expected=sha256(temp)
            if audio.exists():
                if not audio.is_file() or sha256(audio)!=expected:
                    raise ValueError("Existing user music must not be overwritten: "+filename)
            else:
                temp.replace(audio)
                created.append(filename)
        finally:
            if temp.exists():temp.unlink()
        if not sidecar.exists():
            metadata={
                "schemaVersion":1,"category":"background-music",
                "description":cfg["description"],"eventTags":cfg["tags"],
                "mood":cfg["mood"],"vocalContent":"instrumental","loopable":False,
                "bpm":cfg["bpm"],"sourceSha256":expected,
                "generator":"original-rhythmic-instrumental-v1",
                "license":{
                  "kind":"original-owned","ownerConfirmedRights":True,
                  "source":"Rovor original authored notes and deterministic Python/NumPy synthesis in generate_original_music.py; no third-party samples",
                  "evidence":"Source code in private GitHub development repository"
                },
                "listeningReviewStatus":"NOT_ARTISTICALLY_APPROVED",
                "masteringStatus":"NOT_MIXED_WITH_NARRATION",
                "automatedPublishingApproved":False
            }
            pending=sidecar.with_suffix(".pending.json")
            pending.write_text(json.dumps(metadata,indent=2)+"\n")
            pending.replace(sidecar)
        else:
            saved=json.loads(sidecar.read_text())
            if saved.get("sourceSha256")!=expected:
                raise ValueError("Existing score metadata does not match deterministic source")
    return created


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=ROOT)
    args=p.parse_args()
    made=build(args.root)
    catalog=scan(args.root)
    tracks=[x for x in catalog["assets"] if x["category"]=="background-music"]
    if len(tracks)<3:raise SystemExit("Expected three registered original scores")
    print("ROVOR_ORIGINAL_BACKGROUND_MUSIC_CREATED="+str(len(made)))
    for track in tracks:
        print("ROVOR_MUSIC="+track["filename"]+" SECONDS="+str(track["durationSeconds"]))
    print("MUSIC_ARTISTIC_APPROVAL=NO")
    print("ADDITIONAL_COST=0")


if __name__=="__main__":
    main()
