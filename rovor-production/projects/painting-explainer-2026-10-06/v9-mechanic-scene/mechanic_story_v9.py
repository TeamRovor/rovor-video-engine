#!/usr/bin/env python3
"""Rovor illustrated mechanic analogy, source [144.8,156.28), storyboard-art WIP.
Authored vector objects; landscape and portrait separately staged; no fake client
and no voice edits. All shot timing provisional, pending source listening.
"""
from __future__ import annotations
import math, io, os, hashlib
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape
import cairosvg
from PIL import Image

FPS=60; START_FRAME=8688; CUT_FRAME=9032; END_FRAME=9377
START=START_FRAME/FPS; CUT=CUT_FRAME/FPS; END=END_FRAME/FPS
SOURCE_SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'
ORIGINAL=Path(os.getenv('ROVOR_ORIGINAL_MP3','/mnt/data/rovor_v4_audit/ElevenLabs_2026-10-06T01_10_34_Big Steppa Evan _ivc_sp100_s50_sb75_v4.mp3'))

def f(x): return f'{x:.3f}'
def tclamp(x): return max(0., min(1.,x))
def smooth(x):
 x=tclamp(x);return x*x*(3-2*x)
def lerp(a,b,t):return a+(b-a)*t

def path(d, fill='none', stroke='none', sw=0, extra=''):
 return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def rect(x,y,w,h,fill,rx=0,stroke='none',sw=0,extra=''):
 return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'
def ell(cx,cy,rx,ry,fill,stroke='none',sw=0,extra=''):
 return f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'
def line(x1,y1,x2,y2,color='#263b46',sw=2,extra=''):
 return path(f'M{f(x1)} {f(y1)} L{f(x2)} {f(y2)}',stroke=color,sw=sw,extra=extra)
def txt(x,y,s,size=15,color='#f8e9d6',weight=600,anchor='start'):
 return f'<text x="{f(x)}" y="{f(y)}" fill="{color}" font-family="DejaVu Sans,Arial,sans-serif" font-weight="{weight}" font-size="{f(size)}" text-anchor="{anchor}">{escape(s)}</text>'

DEF='''<defs>
<linearGradient id="shop" x2="0" y2="1"><stop stop-color="#304856"/><stop offset=".58" stop-color="#152e38"/><stop offset="1" stop-color="#091f29"/></linearGradient>
<linearGradient id="metal" x2=".92" y2=".75"><stop stop-color="#c3d2ca"/><stop offset=".22" stop-color="#8ca8ad"/><stop offset=".48" stop-color="#4d6774"/><stop offset=".78" stop-color="#253f4d"/><stop offset="1" stop-color="#172936"/></linearGradient>
<linearGradient id="overalls" x2=".86" y2=".9"><stop stop-color="#55818c"/><stop offset=".48" stop-color="#345765"/><stop offset="1" stop-color="#193b4b"/></linearGradient>
<linearGradient id="gold" x2=".9" y2=".4"><stop stop-color="#ffd99c"/><stop offset=".6" stop-color="#d6a86d"/><stop offset="1" stop-color="#9e6f49"/></linearGradient>
<linearGradient id="sheet" x2=".05" y2="1"><stop stop-color="#fffaf1"/><stop offset="1" stop-color="#ded4c2"/></linearGradient>
<linearGradient id="bench" x2=".1" y2="1"><stop stop-color="#a87752"/><stop offset=".25" stop-color="#76553f"/><stop offset=".93" stop-color="#433c37"/></linearGradient>
<radialGradient id="stage"><stop stop-color="#587c79" stop-opacity=".38"/><stop offset="1" stop-color="#254e54" stop-opacity="0"/></radialGradient>
<filter id="blur"><feGaussianBlur stdDeviation="8"/></filter>
<filter id="paper-shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="5"/></filter>
<pattern id="grain" width="17" height="17" patternUnits="userSpaceOnUse"><path d="M1 3h1m6 9h1m2-10h1M4 16h1" stroke="#f5dab4" stroke-width=".65" opacity=".13"/></pattern>
</defs>'''

@dataclass(frozen=True)
class Stage:
 portrait: bool
 @property
 def w(self): return 540 if self.portrait else 960
 @property
 def h(self): return 960 if self.portrait else 540


def environment(st):
 w,h=st.w,st.h
 # two different original stage designs: vertical camera pulls counter down rather than cropping horizontally.
 bench=h*.75 if st.portrait else h*.77
 shelfy=220 if st.portrait else 112
 s=[rect(0,0,w,h,'url(#shop)'),ell(w*.53,h*.30,w*.65,h*.52,'url(#stage)'),rect(0,0,w,h,'url(#grain)')]
 s += [rect(0,shelfy,w,13,'#0b2834'),rect(0,shelfy-3,w,3,'#58717a')]
 for i in range(5 if st.portrait else 8):
  x=40+i*(w-80)/(4 if st.portrait else 7)
  s += [rect(x,shelfy-42,27,37,'#314751',3,'#59747a',1.5),rect(x+7,shelfy-36,13,3,'#97afb2',1)]
 # Hanging bulb cast with triangular pool of muted, warm light.
 bx=w*.78 if st.portrait else w*.65
 s += [line(bx,0,bx,41,'#97a6a5',3),ell(bx,46,30,11,'#ccad78','#4f5251',3),ell(bx,59,21,8,'#e3c899',extra='opacity=".65"'),
       path(f'M{f(bx-29)} 52 L{f(bx-220)} {f(bench)} L{f(bx+170)} {f(bench)} L{f(bx+29)} 52 Z','#dfbd85',extra='opacity=".065"')]
 # Long counter has true perspective edge, not floating cards.
 s += [path(f'M0 {f(bench)} L{f(w)} {f(bench)} L{f(w)} {f(h)} L0 {f(h)} Z','url(#bench)'),
       rect(0,bench,w,14,'#c08c5d'),rect(0,bench+17,w,7,'#413e3a'),line(0,bench,w,bench,'#efc795',2)]
 for k in range(12):
  yy=bench+40+k*20
  s.append(path(f'M0 {f(yy)} q{f(w*.3)} {-1-k%3} {f(w)} 0',stroke='#d4a47a',sw=1,extra='opacity=".17"'))
 return ''.join(s)


def mechanic(st,x,y,scale=1,head_turn=0,attitude=0):
 """Portrait mechanic, authored hair/face and sleeved body. This is a hypothetical actor, not Evan."""
 s=[f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">']
 # Counter occludes waist and no disconnected walking stick legs.
 s += [path('M-108 218 L-98 91 Q-90 48 -44 42 L-28 34 L28 34 L62 48 Q104 54 108 105 L111 218 Z','url(#overalls)','#101e2a',4),
       path('M-28 42 L-2 67 L25 43','none','#d3d2ba',5),
       rect(-20,73,40,102,'#263e4b',8,'#1b3040',2),
       rect(-15,123,30,35,'#547484',4,'#9da6a1',1),
       line(-75,76,-65,191,'#7097a0',3),line(74,80,82,196,'#183545',4)]
 # neck, face and thick expressive hair: actor is non-identical to narrator Evan.
 s += [rect(-21,25,42,38,'#a8755b',11),ell(-44,-34,8,13,'#c89b76','#392f2d',2),ell(44,-34,8,13,'#c89b76','#392f2d',2),
       path('M-46 -63 Q-37 -114 6 -111 Q49 -100 45 -55 L45 -10 Q32 28 1 38 Q-31 30 -46 -10 Z','#c18c68','#242e31',3),
       path('M-49 -62 Q-60 -122 -17 -133 L-2 -150 L24 -130 L43 -125 L54 -85 L44 -54 Q30 -71 19 -89 Q0 -67 -12 -88 Q-32 -64 -49 -62 Z','#1a2b34','#152129',3),
       path('M-39 -81 Q-24 -110 -2 -115','none','#4c5a5e',4),
       path('M12 -101 Q34 -115 41 -83','none','#4a575f',3),
       path('M-30 -56 q13 -9 22 0','none','#47352e',3),path('M10 -58 q14 -8 24 2','none','#47352e',3),
       ell(-18+head_turn*1.5,-44,3,4,'#142936'),ell(20+head_turn*1.5,-45,3,4,'#142936'),
       path('M1 -42 q-5 20 3 19','none','#9d6350',2),
       path(f'M-14 -9 Q2 {f(-7+attitude*3)} 20 -11','none','#66443d',3),
       path('M-20 8 Q0 23 20 7','none','#ac765d',2,extra='opacity=".55"'),
       path('M-20 -1 Q-28 10 -33 11','none','#a6725b',2)]
 s.append('</g>')
 return ''.join(s)


def customer(st,x,y,scale=1,confusion=0):
 # Three-quarter customer reaction close-up, neutral hypothetical.
 s=[f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">']
 s += [path('M-103 194 Q-105 81 -65 54 L-23 35 L23 35 Q87 65 105 197 Z','#ba866b','#543f3c',4),
       rect(-17,27,34,36,'#b9785e',8),
       path('M-48 -69 Q-36 -119 3 -120 Q45 -113 47 -63 L45 -7 Q31 30 -3 35 Q-42 23 -48 -14 Z','#d8ac87','#483739',3),
       path('M-52 -50 Q-69 -111 -40 -129 Q-20 -145 1 -136 Q41 -150 56 -100 L53 -42 Q38 -83 24 -90 Q-6 -71 -52 -50 Z','#332b32','#2b252c',4),
       path('M-52 -43 Q-69 10 -45 57','none','#3b333b',14),path('M50 -34 Q72 15 46 66','none','#3a3038',12),
       path(f'M-33 {-48-confusion*4} q13 {-4-confusion*3} 21 1','none','#5d4139',3),
       path(f'M12 {-48+confusion*4} q12 {-4+confusion*3} 20 2','none','#5d4139',3),
       ell(-23,-39,3,4,'#2e2d33'),ell(22,-38,3,4,'#2e2d33'),
       path('M-2 -32 q-7 17 0 19','none','#ad7964',2),
       path(f'M-16 2 Q3 {f(1+confusion*6)} 19 0','none','#8d5d51',3)]
 s.append('</g>')
 return ''.join(s)


def receipt(st,t):
 p=st.portrait;w=st.w;h=st.h
 u=smooth((t-145.3)/2.6)
 if p:
  xx,yy,ww,hh=145,637,290,245
 else:
  xx,yy,ww,hh=392,348,350,190
 # It originates in the mechanic's hand, unrolls onto workbench with slight physical curve.
 length=lerp(45,hh,u)
 tilt=2*math.sin(min(1.,u)*math.pi)
 paper=[f'<g transform="translate({f(xx)} {f(yy)}) rotate({f(tilt)})">',
  rect(8,8,ww,length,'#142b31',8,extra='opacity=".25" filter="url(#paper-shadow)"'),
  rect(0,0,ww,length,'url(#sheet)',5,'#7f7567',1.5),
  txt(22,30,'SERVICE ESTIMATE',18 if p else 17,'#314953',700)]
 labels=['Part reference','Assembly labor','Additional hardware','Service allowance','Shop supplies']
 for i,l in enumerate(labels):
  y=63+i*32
  if y+10<length:
   paper += [rect(22,y-13,10,10,'none',2,'#c2b8a5',1),txt(42,y,l,13,'#6a6f6b',500),line(ww-86,y-3,ww-24,y-3,'#9aa49f',2)]
 paper.append('</g>')
 # Physical gloved hand grips top edge, naturally overlapping the paper.
 paper += [path(f'M{f(xx+24)} {f(yy+2)} Q{f(xx+7)} {f(yy-18)} {f(xx+23)} {f(yy-31)} Q{f(xx+35)} {f(yy-41)} {f(xx+48)} {f(yy-30)} L{f(xx+61)} {f(yy-9)} Q{f(xx+58)} {f(yy+9)} {f(xx+42)} {f(yy+13)} Z','#859d93','#283d42',3),
  path(f'M{f(xx+29)} {f(yy-20)} Q{f(xx+44)} {f(yy-13)} {f(xx+48)} {f(yy+2)}','none','#c9d4c4',2)]
 return ''.join(paper)


def shot_service(st,t):
 w,h=st.w,st.h;p=st.portrait
 # Wide counter dialogue turns to tall two-person composition without horizontal crop.
 s=[environment(st)]
 if p:
  s += [mechanic(st,165,391,.98,-.5),customer(st,414,406,.75,confusion=smooth((t-147.1)/1.7))]
 else:
  s += [mechanic(st,300,279,1.1,-.5),customer(st,750,291,.87,confusion=smooth((t-147.1)/1.7))]
 # Contact invariant: the mechanic's sleeve runs from their shoulder to the wrist
 # visibly gripping the receipt. It is BEHIND the receipt and its glove, not a
 # detached mitten floating above the paper. Stage-specific authored silhouettes.
 if p:
  armshape='M220 468 C246 470 268 527 255 565 Q229 617 169 627 L161 615 Q204 574 224 556 Q225 520 199 486 Z'
  seam='M218 490 Q235 537 228 564 Q195 609 170 620'
 else:
  armshape='M352 343 C379 330 397 344 402 359 Q412 353 422 341 L432 355 Q406 379 386 381 Q367 377 345 371 Z'
  seam='M358 355 Q383 343 402 365 Q417 353 422 350'
 s += [path(armshape,'url(#overalls)','#172d3a',3.8),path(seam,'none','#7f9aa0',2.3)]
 s.append(receipt(st,t))
 # customer fingers hover over the technical words and stop: controlled reaction, no random idle bounce.
 if p:
  xx=lerp(507,427,smooth((t-147.4)/1.2));yy=lerp(810,735,smooth((t-147.4)/1.2))
 else:
  xx=lerp(815,702,smooth((t-147.4)/1.2));yy=lerp(491,400,smooth((t-147.4)/1.2))
 # hand enters from off-screen and settles by the text, eliminating floating elbow lines.
 s += [path(f'M{f(w+20)} {f(yy+35)} Q{f(xx+80)} {f(yy+15)} {f(xx+42)} {f(yy+7)} Q{f(xx+21)} {f(yy-6)} {f(xx+11)} {f(yy+3)} Q{f(xx+12)} {f(yy+16)} {f(xx+28)} {f(yy+18)} L{f(w+20)} {f(yy+82)} Z','#cba082','#4e4a47',3)]
 return ''.join(s)


def brake_diagram(st,t):
 """Object-first physical mechanism view: brake rotor/caliper, not a generic infographic panel."""
 w,h=st.w,st.h;p=st.portrait
 s=[environment(st)]
 # camera pushes into workbench object; the rear mechanic is only a subtle acting anchor.
 if p:
  s.append(mechanic(st,105,345,.72,1))
  cx,cy,rad=272,627,158
 else:
  s.append(mechanic(st,126,303,.72,1))
  cx,cy,rad=548,302,168
 # Warm object-local spotlight against blue workshop shadows.
 s += [ell(cx,cy,rad*1.7,rad*1.7,'url(#stage)'),ell(cx,cy+rad*.7,rad*1.03,rad*.28,'#041a22',extra='opacity=".37" filter="url(#blur)"')]
 # No inventing a specific broken brake: schematic example only. Disc details are physically consistent.
 s += [ell(cx+6,cy+10,rad*1.02,rad*1.02,'#0c242e'),ell(cx,cy,rad,rad,'url(#metal)','#d3e0d4',6),
       ell(cx,cy,rad*.8,rad*.8,'#2c4754','#77939b',4),ell(cx,cy,rad*.7,rad*.7,'url(#metal)','#607f84',7)]
 for i in range(14):
  a=2*math.pi*i/14
  ex=cx+math.cos(a)*rad*.59;ey=cy+math.sin(a)*rad*.59
  s.append(ell(ex,ey,rad*.035,rad*.035,'#1c3b48','#9ba9a8',1))
 s += [ell(cx,cy,rad*.23,rad*.23,'#192d37','#8697a0',7),ell(cx,cy,rad*.14,rad*.14,'#7e9b9b','#233f4b',4)]
 for i in range(5):
  a=2*math.pi*i/5
  ex=cx+math.cos(a)*rad*.185;ey=cy+math.sin(a)*rad*.185
  s.append(ell(ex,ey,rad*.025,rad*.025,'#d4d7ca','#405962',1.5))
 # Caliper physically eases outward from rotor revealing pad; movement tied to separate part layer.
 u=smooth((t-151.55)/3.6); shift=lerp(0,rad*.32,u)
 x=cx+rad*.59+shift;y=cy-rad*.48
 s += [f'<g transform="translate({f(x)} {f(y)})">',
       path(f'M0 0 Q{f(rad*.36)} {f(-rad*.08)} {f(rad*.38)} {f(rad*.23)} L{f(rad*.4)} {f(rad*.65)} Q{f(rad*.29)} {f(rad*.89)} {f(-rad*.05)} {f(rad*.77)} L{f(-rad*.17)} {f(rad*.59)} L{f(-rad*.1)} {f(rad*.1)} Z','#cc9c65','#3c4d4e',5),
       rect(rad*.02,rad*.13,rad*.22,rad*.39,'#4a4e4b',4,'#d4b080',2),
       path(f'M{f(rad*.08)} {f(rad*.10)} Q{f(rad*.22)} {f(rad*.05)} {f(rad*.31)} {f(rad*.15)}','none','#fff0b6',3),
       '</g>']
 # Dust motes are timed to actual moving assembly, restrained.
 for i in range(8):
  v=(i*7)%9
  s.append(ell(cx+rad*.95+shift*.45+v*5,cy-42+i*13,1.5+(i%3)*.5,1.5+(i%3)*.5,'#f3dbb2',extra=f'opacity="{f(.05+.16*u)}"'))
 # No disconnected pointing stick: focus instead on the physically moving caliper
 # and make the exposed working surface itself the action. Hand/prop layers can
 # be added only when physically anchored in the final perspective rig.
 return ''.join(s)


def svg_at(t,portrait=False):
 assert START<=t<END, 'outside original source interval'
 st=Stage(bool(portrait))
 parts=[DEF]
 if t < CUT: parts.append(shot_service(st,t))
 else: parts.append(brake_diagram(st,t))
 # Original hand-lettered minimal scene title; purpose is storytelling not info slides.
 label='A LIST OF PARTS' if t<CUT else 'WHAT THE PART DOES'
 parts.append(txt(28 if st.portrait else 38,75 if st.portrait else 51,label,14 if st.portrait else 15,'#efcc94',700))
 parts.append(rect(28 if st.portrait else 38,82 if st.portrait else 59,138 if st.portrait else 176,2,'#daa96f'))
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{st.w*2}" height="{st.h*2}" viewBox="0 0 {st.w} {st.h}">'+''.join(parts)+'</svg>'


def frame_at(t,portrait=False,size='native'):
 assert size in {'native','half'}
 st=Stage(bool(portrait));scale=2 if size=='native' else 1
 png=cairosvg.svg2png(bytestring=svg_at(t,portrait).encode('utf8'),output_width=st.w*scale,output_height=st.h*scale)
 return Image.open(io.BytesIO(png)).convert('RGB')

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--time',type=float,default=149.0);p.add_argument('--portrait',action='store_true');p.add_argument('--out',type=Path,required=True)
 args=p.parse_args()
 if args.out.suffix.lower()=='.svg':args.out.write_text(svg_at(args.time,args.portrait))
 else:frame_at(args.time,args.portrait).save(args.out)

def physical_contact_samples(portrait:bool):
 """Actual SVG authoring controls used in shot_service—not approval of drawing quality.
 Each sample refers to the same grip at the top edge of the receipt and cuff.
 This track is source-specific; reusable validator lives in contact_audit.py.
 """
 from contact_audit import P,Pose
 if portrait:
  shoulder,elbow,wrist,hand=P(220,468),P(255,565),P(169,627),P(169,635)
 else:
  shoulder,elbow,wrist,hand=P(352,343),P(402,359),P(422,341),P(416,350)
 # Receipt top is locked, unrolls down; both hand/grip and sleeve are static.
 return [Pose(i,shoulder,elbow,wrist,hand,hand) for i in range(START_FRAME,CUT_FRAME,12)]