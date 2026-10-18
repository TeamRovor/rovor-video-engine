#!/usr/bin/env python3
"""Rovor painting film, native SVG NEW continuation [132.0,144.8), 60fps.
ORIGINAL narration remains private and unmodified. Secondary characters are hypothetical,
not actual customers. Three deliberately directed shots, independently composed for
landscape and portrait. WIP visual blocking, no word alignment/artist approval.
"""
from __future__ import annotations
import math,io,hashlib,argparse,os
from pathlib import Path
from dataclasses import dataclass
import cairosvg
from PIL import Image
SOURCE_START=132.0; SOURCE_END=144.8; FPS=60
SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'
BASE=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('ROVOR_ORIGINAL_MP3', str(BASE.parent/'rovor_v5_work'/'ElevenLabs_2026-10-06T01_10_34_Big Steppa Evan _ivc_sp100_s50_sb75_v4.mp3')))
INK='#233b46'; GREY='#556b72'; PAINT='#4b8796'; LIGHT='#f6eedf'; NAVY='#284f60'
def clamp(x):return max(0.,min(1.,x))
def sm(x):x=clamp(x);return x*x*(3-2*x)
def mx(a,b,u):return a+(b-a)*u
def f(x):return f'{x:.2f}'
def esc(text):return (text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'))
def rect(x,y,w,h,fill,rx=0,stroke='none',sw=0,extra=''):
 return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'
def ell(x,y,rx,ry,fill,stroke='none',sw=0,extra=''):
 return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" {extra}/>'
def path(d,fill='none',stroke='none',sw=0,extra=''):
 return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{f(sw)}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def line(x1,y1,x2,y2,color=INK,sw=2,extra=''):
 return path(f'M{f(x1)} {f(y1)} L{f(x2)} {f(y2)}','none',color,sw,extra)
def txt(x,y,t,size=14,color=INK,weight='600',anchor='start',letter=None):
 return f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" fill="{color}" font-family="DejaVu Sans,Arial,sans-serif" font-weight="{weight}" text-anchor="{anchor}" {("letter-spacing="+repr(letter)) if letter else ""}>{esc(t)}</text>'
def poly(points,fill,stroke='none',sw=0):return path('M'+' L'.join(f'{f(a)} {f(b)}' for a,b in points)+' Z',fill,stroke,sw)

DEFS='''<defs>
<linearGradient id="wall" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#f9f1e1"/><stop offset=".67" stop-color="#eae0ce"/><stop offset="1" stop-color="#dacdb9"/></linearGradient>
<linearGradient id="wood" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#a67d5f"/><stop offset=".55" stop-color="#805d4a"/><stop offset="1" stop-color="#664d40"/></linearGradient>
<linearGradient id="paper" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#fffefa"/><stop offset="1" stop-color="#eee5d8"/></linearGradient>
<linearGradient id="navy" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#4d7a8a"/><stop offset=".7" stop-color="#305768"/><stop offset="1" stop-color="#213f51"/></linearGradient>
<linearGradient id="skin" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#eac29f"/><stop offset=".6" stop-color="#d29a76"/><stop offset="1" stop-color="#b67b5f"/></linearGradient>
<filter id="paperShadow" x="-25%" y="-25%" width="160%" height="160%"><feGaussianBlur stdDeviation="7"/></filter>
<filter id="softShadow" x="-20%" y="-40%" width="160%" height="180%"><feGaussianBlur stdDeviation="9"/></filter>
</defs>'''

@dataclass
class Stage:
 portrait:bool
 @property
 def w(self):return 540 if self.portrait else 960
 @property
 def h(self):return 960 if self.portrait else 540
 @property
 def desk_y(self):return 675 if self.portrait else 422

def room(st):
 w,h=st.w,st.h; x=40 if st.portrait else 104
 s=[rect(0,0,w,h,'url(#wall)'),rect(0,0,w,h*.09,'#e7d6bd'),line(0,h*.09,w,h*.09,'#fdf6eb',5)]
 # Deep-set studio window: geometry, 2 panes, recognizable warm interior continuity.
 ww=150 if st.portrait else 204;wy=130 if st.portrait else 72;wh=300 if st.portrait else 220
 s += [rect(x-11,wy-12,ww+24,wh+25,'#b5aa97',7),rect(x,wy,ww,wh,'#e8eee7',4,'#5e7781',7),rect(x+9,wy+9,ww-18,wh-18,'#a4c7c4')]
 s.append(poly([(x+13,wy+12),(x+ww-10,wy+12),(x+ww-10,wy+wh*.48),(x+13,wy+wh*.75)],'#d8e5d9'))
 s += [line(x+ww*.5,wy+9,x+ww*.5,wy+wh-9,'#5a7983',5),line(x+9,wy+wh*.52,x+ww-9,wy+wh*.52,'#5a7983',5)]
 # Room paint trim with a tiny patched imperfection, background decor unobtrusive.
 s.append(line(0,h*.89,w,h*.89,'#fff7e8',9));s.append(line(0,h*.895,w,h*.895,'#b4a790',1.5))
 for i in range(4):
  xx= w*.72+i*24
  s.append(path(f'M{f(xx)} {f(h*.23)} q5 -4 12 2','none','#e0d5c4',.7))
 return ''.join(s)

def arm(ax,ay,ex,ey,hx,hy,jacket=True,rad=10):
 # Subtly bent sleeve/forearm with rounded elbow contour and a taper to the hand;
 # no rigid polygonal rod or detached wrist. Elbow is a directing control point.
 c='#30596b' if jacket else '#c78f6c';shade='#244251' if jacket else '#9f6950'
 # Distinct curves are pinned to a single end effector.
 curve=f'M{f(ax)} {f(ay)} Q{f(ex)} {f(ey)} {f(hx)} {f(hy)}'
 a=[path(curve,'none',shade,rad+7),path(curve,'none',c,rad+1)]
 if jacket:
  a.append(path(f'M{f(ax-2)} {f(ay-3)} Q{f(ex-3)} {f(ey-4)} {f(hx-2)} {f(hy-2)}','none','#76929a',2))
  # Cuff follows end effector and covers the limb-to-hand attachment.
  a.append(ell(hx,hy,rad*.55,rad*.63,'#284a58','#203844',1.2))
 return ''.join(a)

def glove_hand(x,y,rotation=0,scale=1,index=False):
 a=[f'<g transform="translate({f(x)} {f(y)}) rotate({f(rotation)}) scale({f(scale)})">',
    path('M-10 -11 Q-2 -17 7 -10 L20 -3 Q24 8 10 14 L-10 10 Z','url(#skin)','#6c544b',2),
    path('M1 -7 Q12 -15 18 -8','none','#9e6d55',1.4)]
 if index:
  a+=[path('M10 -3 Q24 -9 40 -5 Q46 1 37 5 L11 7 Z','url(#skin)','#6c544b',2.2),
      line(17,0,28,0,'#c08161',1.1)]
 else:
  for i in range(3):a.append(line(5,2+i*3,16,3+i*3,'#ad775a',1.4))
 a.append('</g>')
 return ''.join(a)

def actor(st,x,y,scale,person='painter',look=0,react=0):
 # Half body portrait drawn as separate coherent shapes with subtle eyebrow/neck/shoulder acting.
 s=[f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">']
 # neck then body silhouette, purposeful outfit distinction, not Evan's source rig.
 skin='url(#skin)' if person=='painter' else '#bc876e'
 shirt='url(#navy)' if person=='painter' else '#b87861'
 s += [rect(-17,37,34,51,skin,9),path('M-61 75 Q-75 75 -85 124 L-102 246 L100 246 L84 121 Q72 77 57 75 L24 63 L-20 63 Z',shirt,'#2a4148',3.8)]
 s.append(path('M-23 68 L3 95 L28 70','none','#e9e0d0',5))
 if person=='painter':
  s += [rect(-30,112,60,99,'#b4a489',8,'#59696a',2),line(-28,146,30,146,'#d5c29f',2),rect(-19,163,38,26,'#d6c6ac',5,'#8b907b',1.5),
        path('M-58 89 Q-66 130 -75 197','none','#668c96',4)]
 else:
  s += [path('M-52 106 Q-29 115 -28 156','none','#e2a58e',4),path('M61 110 Q44 135 50 195','none','#935d4f',4)]
 # face, ears, detailed hair and facial performance.
 s.extend([ell(-43,-1,9,15,skin,'#344b50',2.1),ell(44,-1,9,15,skin,'#344b50',2.1),
           path('M-43 -28 Q-45 -61 2 -63 Q46 -60 45 -20 L43 26 Q34 61 2 65 Q-34 57 -43 22 Z',skin,'#33464a',3.5)])
 if person=='painter':
  s += [path('M-48 -23 Q-47 -69 -18 -67 L-6 -85 L16 -73 L32 -75 L51 -49 L43 -22 Q23 -43 13 -35 Q-5 -28 -10 -40 Q-24 -22 -48 -23 Z','#253944','#182d36',3),
        path('M-23 -60 Q-7 -71 14 -58','none','#506b75',3)]
 else:
  s += [path('M-44 -19 Q-56 -69 -22 -80 Q0 -94 20 -81 Q55 -64 47 -13 Q36 -34 25 -51 Q-3 -32 -44 -19 Z','#3b3030','#2a282d',3),
        path('M-45 -9 Q-64 51 -45 104','none','#443238',13),
        path('M44 -10 Q63 50 45 115','none','#443238',12),
        path('M-31 -62 Q-2 -86 24 -57','none','#755751',3)]
 ey=-2+look*2
 for xx in (-22,22):
  s += [path(f'M{f(xx-10)} {f(ey-15)} q11 {f(-5-react*2)} 22 0','none','#59463f',2.6),
        ell(xx+look*3,ey,3.2,5,'#263b44'),ell(xx-1+look*3,ey-1.6,1,1.3,'#fffcf2')]
 s += [path('M3 1 q-4 15 3 18','none','#ad715d',2.1),
       path(f'M-10 35 Q2 {f(38+react*2)} 16 32','none','#7d5146',2.3),
       ell(27,24,10,4,'#daaa89',extra='opacity=".65"')]
 s.append('</g>')
 return ''.join(s)

def clipboard(cx,cy,size=1,tilt=0,hand=False):
 s=[f'<g transform="translate({f(cx)} {f(cy)}) rotate({f(tilt)}) scale({f(size)})">',
    rect(-65,-80,130,172,'#4a6268',9),rect(-59,-70,118,155,'url(#paper)',4),rect(-20,-85,40,13,'#6c7775',5),
    txt(-47,-38,'WORK SCOPE',12,INK,'700'),line(-46,-29,44,-29,'#c9c7bb',1),
    line(-46,-10,38,-10,'#b8bdba',2),line(-46,7,39,7,'#b8bdba',2),line(-46,24,20,24,'#b8bdba',2),
    rect(-44,37,13,13,'#e1f3ef',3,'#689b94',1.5),path('M-41 43 l3 4 l7 -9','none','#367b74',2.2),
    rect(-44,58,13,13,'#e1f3ef',3,'#689b94',1.5),path('M-41 63 l3 4 l7 -8','none','#367b74',2.2),
    line(-26,44,36,44,'#99a6a0',2),line(-26,64,27,64,'#99a6a0',2)]
 s.append('</g>');return ''.join(s)

def sheet(st,x,y,w,h,which='a',rotation=0,appearing=1):
 # Quotes are explicit hypothetical illustrations. Avoid invented prices or clients.
 items=['WALLS','TRIM','PATCHES','COVERING','CLEANUP']
 ss=[f'<g transform="translate({f(x)} {f(y)}) rotate({f(rotation)})" opacity="{f(appearing)}">',
     rect(6,8,w,h,'#594c3e',8,extra='filter="url(#paperShadow)" opacity=".30"'),
     rect(0,0,w,h,'url(#paper)',6,'#a9ac9f',1.8),
     txt(20,37,'ESTIMATE',18,'#2c4753','700'),
     txt(w-18,37,which.upper(),14,'#4c7782','700','end'),line(18,50,w-18,50,'#9ca9a7',1.7)]
 row_h=(h-105)/5
 for i,item in enumerate(items):
  yy=75+i*row_h
  filled=(which=='b' or i==0)
  ss.append(rect(19,yy-12,16,16,'#dceae7' if filled else '#fffefa',3,'#92aba6',1.5))
  if filled:ss.append(path(f'M22 {f(yy-5)} l4 4 l8 -9','none','#337d75',2.4))
  ss.append(txt(44,yy+1,item,11.5 if st.portrait else 12.5,INK,'600'))
  ss.append(line(44,yy+12,w-20,yy+12,'#dddcd1',1))
 ss += [line(20,h-27,w-25,h-27,'#ddd6c9',1),txt(20,h-12,'Illustrative scope, not a real quote',8,'#9a9990','400')]
 ss.append('</g>');return ''.join(ss)

def set_table(st):
 y=st.desk_y;w=st.w;h=st.h
 s=[ell(w*.52,y+12,w*.55,28,'#70584b',extra='filter="url(#softShadow)" opacity=".22"'),
    poly([(0,y-5),(w,y-5),(w,y+22),(0,y+22)],'#c29d7b','#624a3d',2),
    rect(0,y+20,w,h-y,'url(#wood)'),line(0,y+23,w,y+23,'#dec3a6',4)]
 for k in range(8):
  yy=y+45+k*35
  s.append(path(f'M0 {f(yy)} Q{f(w*.35)} {f(yy-5)} {f(w*.7)} {f(yy)} T{f(w)} {f(yy-2)}','none','#d3a984',1,extra='opacity=".23"'))
 return ''.join(s)

def shot_one(st,t):
 u=sm((t-132)/2.88)
 s=[room(st)]
 p=st.portrait;w=st.w;dy=st.desk_y
 # actors visibly beside the paper, no floaty info cards.
 if p:
  painter=(149,464,.91);customer=(384,463,.91);cx=268;cy=678;cs=.84
 else:
  painter=(259,278,1.12);customer=(690,276,1.11);cx=481;cy=431;cs=.80
 # end customer leans to see clipboard; painter's gaze leads hand.
 s += [actor(st,painter[0],painter[1]-4*sm((t-132.5)/1.2),painter[2],'painter',look=.7),
       actor(st,customer[0]-4*u,customer[1]+3*u,customer[2],'customer',look=-.55,react=u*.3),
       set_table(st),clipboard(cx,cy-20*sm((t-132)/1),cs,-7)]
 # Painter rests pointer tip on the clipboard edge; elbow travels slightly; keep anatomy connected.
 ax=painter[0]+53*painter[2]; ay=painter[1]+81*painter[2]
 hx=cx-23*cs;hy=cy-6*cs; ex=mx(ax,hx,.45); ey=ay+(-15 if p else -31)
 s += [arm(ax,ay,ex,ey,hx,hy,True,11*painter[2]),glove_hand(hx,hy,135,.66,index=True)]
 # Customer gently braces board with her hand.
 ax=customer[0]-52*customer[2];ay=customer[1]+75*customer[2]
 hx=cx+25*cs;hy=cy+32*cs;ex=mx(ax,hx,.47);ey=ay-4
 s += [arm(ax,ay,ex,ey,hx,hy,False,9*customer[2]),glove_hand(hx,hy,120,.65)]
 return ''.join(s)

def shot_two(st,t):
 # Bird's-eye physical tabletop scene: two clearly different quotes compare SCOPE not a winner.
 u=sm((t-134.88)/4.95)
 w,h=st.w,st.h;p=st.portrait
 s=[rect(0,0,w,h,'url(#wood)')]
 for i in range(22):
  y=(i*71)%h
  s.append(path(f'M-30 {f(y)} Q{f(w*.4)} {f(y-14)} {f(w+30)} {f(y+2)}','none','#d0a17a',1.7,extra='opacity=".19"'))
 if p:
  sy=250;sheet_w=245;sheet_h=370; a=(33,sy);b=(282,sy+5)
  # Portrait deliberately stages B arriving from below the screen rather than cropping desktop.
  shift=mx(340,0,sm((t-135)/1.2));b=(b[0]-155,b[1]+shift)
  aa=(a[0]-10,a[1]-18)
 else:
  sy=79;sheet_w=280;sheet_h=365; a=(173,sy);b=(507,sy+6); aa=a
 # cast paper shadows and physical slide motion, not magical static text panels.
 s += [rect(40,40,w-80,h-80,'#ece0cf',10,extra='opacity=".10"')]
 if p:
  # A is partially behind the overlapping B on vertical; alternate physical camera composition.
  s.append(sheet(st,aa[0],aa[1],sheet_w,sheet_h,'a',-6))
  s.append(sheet(st,b[0],b[1],sheet_w,sheet_h,'b',5))
 else:
  s.append(sheet(st,a[0],a[1],sheet_w,sheet_h,'a',-4))
  s.append(sheet(st,b[0],b[1]+mx(85,0,sm((t-135.1)/1.0)),sheet_w,sheet_h,'b',3))
 # Inspecting fingertip tracks included wall repair / protection check boxes on B.
 hx=(b[0]+58 if p else b[0]+68); hy=(b[1]+128 if p else b[1]+160)
 startx=w*.92; starty=h*.92
 uhand=sm((t-136.2)/1.3)
 px=mx(startx,hx,uhand);py=mx(starty,hy,uhand)
 s += [arm(startx+15,starty+70,mx(startx,px,.48),mx(starty,py,.48)+20,px,py,False,12),glove_hand(px,py,-80,.75,index=True)]
 # Separate non-distracting pencil, not a magic pointer.
 s += [line(px+20,py-3,px+61,py-14,'#36515c',4),line(px+61,py-14,px+70,py-17,'#dba66d',4)]
 return ''.join(s)

def shot_three(st,t):
 # Grounded close detail where lines of work are made legible by physically folding confusing extra text away.
 w,h=st.w,st.h;p=st.portrait
 s=[rect(0,0,w,h,'url(#wood)')]
 for i in range(14):
  y=(i*99)%h;s.append(path(f'M0 {f(y)} q{f(w*.4)} -8 {f(w)} 4','none','#d3aa86',1.8,extra='opacity=".16"'))
 if p:
  x=60;y=195;sw=410;sh=590
 else:
  x=218;y=36;sw=528;sh=468
 s += [rect(x+16,y+20,sw,sh,'#554337',9,extra='filter="url(#paperShadow)" opacity=".30"'),
       rect(x,y,sw,sh,'url(#paper)',8,'#a9aa9e',2),txt(x+27,y+56,'WHAT THE WORK INCLUDES',18 if p else 21,INK,'700'),
       line(x+24,y+68,x+sw-24,y+68,'#a2b4b0',2)]
 # meaningful customer-readable explanation, no invented case-study names.
 titles=['Protect the room','Repair the surface','Finish and clean up']
 subs=['Move & cover furniture','Fill damage before coating','Check edges & leave it tidy']
 for i,(title,sub) in enumerate(zip(titles,subs)):
  yy=y+(120 if p else 117)+i*(137 if p else 105)
  s += [rect(x+26,yy-26,39,39,'#e0f0eb',8,'#81aaa1',1.6),path(f'M{f(x+35)} {f(yy-6)} l10 9 l18 -23','none','#4f8d7f',4),
        txt(x+85,yy-5,title,18 if p else 22,INK,'700'),txt(x+85,yy+21,sub,12.5 if p else 15,GREY,'400')]
 # Small paper flap actually folds out of shot, revealing work underneath; keep it on top then fold away.
 u=sm((t-140.4)/2.65)
 flap_w= sw*.47*(1-u)
 if flap_w>3:
  xx=x+sw-flap_w
  s += [poly([(xx,y+74),(x+sw,y+74),(x+sw,y+sh-25),(xx+13,y+sh-25)],'#e8e1d6','#c1b9ad',1.5),
        path(f'M{f(xx+13)} {f(y+92)} v{f(sh-130)}','none','#b6a99b',2)]
  for k in range(8):
   yy=y+108+k*(sh-170)/8
   s.append(line(xx+17,yy,x+sw-18,yy,'#b4b2a8',1.3,extra='opacity=".75"'))
  s.append(txt(xx+20,y+95,'DETAILS',9,GREY,'600'))
 # Painter's forearm enters with actual paper edge pinched. Hand stays connected to flap during change.
 hx=mx(x+sw*.53,x+sw+20,u);hy=y+sh*.70
 ax=(x+sw+130 if not p else x+sw+100); ay=hy+190
 s += [arm(ax,ay,mx(ax,hx,.53),hy+47,hx,hy,True,12),glove_hand(hx,hy,175,.9)]
 return ''.join(s)

def vector_frame(sec,portrait=False):
 assert SOURCE_START<=sec<SOURCE_END,(sec,SOURCE_START,SOURCE_END)
 st=Stage(portrait)
 if sec<134.88:layers=shot_one(st,sec)
 elif sec<139.83:layers=shot_two(st,sec)
 else:layers=shot_three(st,sec)
 # high-resolution scalable source; all drawn content is original and editable.
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{st.w}" height="{st.h}" viewBox="0 0 {st.w} {st.h}">{DEFS}{layers}</svg>'

def render_frame(sec,portrait=False,native=True):
 assert SOURCE_START<=sec<SOURCE_END
 w,h=(1080,1920) if portrait else (1920,1080)
 if not native:w//=2;h//=2
 data=cairosvg.svg2png(bytestring=vector_frame(sec,portrait).encode(),output_width=w,output_height=h)
 return Image.open(io.BytesIO(data)).convert('RGB')
if __name__=='__main__':
 pa=argparse.ArgumentParser();pa.add_argument('--at',type=float,default=133.7);pa.add_argument('--portrait',action='store_true');pa.add_argument('--output',type=Path,required=True);pa.add_argument('--svg',action='store_true');args=pa.parse_args()
 args.output.parent.mkdir(parents=True,exist_ok=True)
 (args.output.write_text(vector_frame(args.at,args.portrait)) if args.svg else render_frame(args.at,args.portrait).save(args.output))