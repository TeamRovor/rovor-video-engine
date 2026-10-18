"""V11 source-faithful animated cloth/contact study for painting film [108,114).

Original secondary painter, NOT Evan's established layered presenter rig. All
geometry in editable SVG. No fabricated customer, brand mark, or recorded audio.
Intended as an artistic development preview, not studio approval.
"""
from __future__ import annotations
import math
import html
from dataclasses import dataclass

SRC_BEGIN=108.0
SRC_END=114.0
FPS=60
SOURCE_SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'


def clamp(x,lo=0.0,hi=1.0):return max(lo,min(hi,x))
def smooth(x):
    x=clamp(x);return x*x*(3-2*x)

@dataclass(frozen=True)
class Layout:
    width:int;height:int
    x:float;y:float;w:float;h:float
    shoulder:tuple[float,float]
    elbow_start:tuple[float,float]
    hand_start:tuple[float,float]
    move_x:float
    move_y:float
    style:str

LAYOUTS={
 'landscape':Layout(960,540,240,211,614,189,(210,234),(290,230),(358,272),115,31,'wide'),
 'portrait':Layout(540,960,46,300,470,374,(111,425),(167,422),(230,432),95,49,'vertical'),
}

def state(t:float,orientation:str)->dict:
    if orientation not in LAYOUTS:raise ValueError('Unknown orientation')
    if not math.isfinite(t) or not 0<=t<6:raise ValueError('Time outside original 6-second excerpt')
    a=LAYOUTS[orientation]
    pull=smooth((t-.28)/2.85)
    tuck=smooth((t-2.5)/1.85)
    release=smooth((t-4.42)/1.2)
    hand_x=a.hand_start[0]+a.move_x*pull-a.move_x*.68*release
    hand_y=a.hand_start[1]+a.move_y*tuck-(a.move_y*.52+100)*release
    # Draping and settling follow physical pull with delayed hem dynamics.
    coverage=.62+.38*smooth((t-.28)/3.2)
    flutter=(1-tuck)*math.sin(t*8.5)*3.5+math.sin(t*4.0)*(1-release)*1.2
    return dict(t=t,pull=pull,tuck=tuck,release=release,coverage=coverage,
        hand=(hand_x,hand_y),elbow=(a.elbow_start[0]+a.move_x*.4*pull,
            a.elbow_start[1]+a.move_y*.36*tuck),flutter=flutter,
        contact=(hand_x+24,hand_y+9+2*release),
        style=orientation)


def _fmt(v):return f'{v:.2f}'
def _poly(points):return ' '.join(f'{_fmt(x)},{_fmt(y)}' for x,y in points)
def _catmull(points,close=False):
    """Smooth SVG path through points, retaining endpoints and organic folds."""
    if len(points)<2:raise ValueError('Need points')
    p=list(points)
    if close:p=[p[-1]]+p+[p[0],p[1]]
    else:p=[p[0]]+p+[p[-1]]
    d=f'M {_fmt(p[1][0])} {_fmt(p[1][1])}'
    for i in range(1,len(p)-2):
        a,b,c,e=p[i-1:i+3]
        c1=(b[0]+(c[0]-a[0])/6,b[1]+(c[1]-a[1])/6)
        c2=(c[0]-(e[0]-b[0])/6,c[1]-(e[1]-b[1])/6)
        d+=f' C {_fmt(c1[0])} {_fmt(c1[1])}, {_fmt(c2[0])} {_fmt(c2[1])}, {_fmt(c[0])} {_fmt(c[1])}'
    if close:d+=' Z'
    return d


def svg_frame(t:float,orientation:str)->str:
    st=state(t,orientation);a=LAYOUTS[orientation]
    W,H=a.width,a.height;x,y,w,h=a.x,a.y,a.w,a.h
    pull,tuck,release=st['pull'],st['tuck'],st['release']
    hx,hy=st['hand']; ex,ey=st['elbow']; sx,sy=a.shoulder
    cloth_end=x+w*(.62+.38*pull)
    hem_top=y+h*.17
    seat_top=y+h*.40
    seat_bot=y+h*.83
    hem_base=y+h*.95
    flutter=st['flutter']
    body=[]
    def add(s):body.append(s)
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    add('''<defs>
    <linearGradient id="room" x1="0" y1="0" x2="0.8" y2="1"><stop stop-color="#fff4df"/><stop offset="1" stop-color="#c9bba9"/></linearGradient>
    <linearGradient id="back" x1="0" y1="0" x2=".9" y2=".9"><stop stop-color="#c1a68b"/><stop offset="1" stop-color="#8b6953"/></linearGradient>
    <linearGradient id="clothFront" x1="0" y1="0" x2=".1" y2="1"><stop stop-color="#fbfaf0"/><stop offset=".38" stop-color="#e2e8df"/><stop offset="1" stop-color="#a9bab7"/></linearGradient>
    <linearGradient id="clothTop" x1="0" y1="0" x2="1" y2=".8"><stop stop-color="#fffff4"/><stop offset=".55" stop-color="#eef0e7"/><stop offset="1" stop-color="#cfdbd3"/></linearGradient>
    <linearGradient id="sleeve" x1="0" y1="0" x2=".2" y2="1"><stop stop-color="#486a7a"/><stop offset="1" stop-color="#233c50"/></linearGradient>
    <filter id="blur"><feGaussianBlur stdDeviation="8"/></filter>
    </defs>''')
    # Filmic held background: actual room, not a slideshow panel.
    add(f'<rect width="{W}" height="{H}" fill="url(#room)"/>')
    add(f'<path d="M 0 {_fmt(H*.25)} L {_fmt(W*.16)} {_fmt(H*.11)} L {_fmt(W*.91)} {_fmt(H*.13)} L {W} {_fmt(H*.26)} V 0 H 0Z" fill="#fdf8eb" opacity=".8"/>')
    add(f'<path d="M 0 {_fmt(H*.80)} L {_fmt(W*.15)} {_fmt(H*.69)} L {_fmt(W*.92)} {_fmt(H*.70)} L {W} {_fmt(H*.82)} V {H} H 0 Z" fill="#988574"/>')
    for q in (0.15,0.30,0.45,0.60,0.75,0.9):
        add(f'<path d="M {_fmt(W*q)} {H} L {_fmt(W*.57)} {_fmt(H*.72)}" stroke="#c1aa92" stroke-width="2" opacity=".43"/>')
    for q in (.82,.90,.97):
        add(f'<path d="M 0 {_fmt(H*q)} L {W} {_fmt(H*q)}" stroke="#b6a08c" stroke-width="2" opacity=".38"/>')
    # A painted window and subtle molding retain source environment identity.
    wx=(W*.72 if orientation=='portrait' else W*.8)
    wy=H*.12 if orientation=='portrait' else H*.09
    ww=W*.14 if orientation=='portrait' else W*.10
    wh=H*.18 if orientation=='portrait' else H*.22
    add(f'<rect x="{_fmt(wx)}" y="{_fmt(wy)}" width="{_fmt(ww)}" height="{_fmt(wh)}" fill="#91bdc7" stroke="#516d75" stroke-width="4"/>')
    add(f'<path d="M {_fmt(wx+ww/2)} {_fmt(wy)} V {_fmt(wy+wh)} M {_fmt(wx)} {_fmt(wy+wh/2)} H {_fmt(wx+ww)}" stroke="#f6f0df" stroke-width="5"/>')
    add(f'<path d="M 0 {_fmt(H*.7)} H {W}" stroke="#ead6b9" stroke-width="7"/>')
    # Shoulder-anchored secondary painter. Head, hair, jacket and apron are
    # intentionally original secondary-actor silhouettes, not regenerated Evan.
    # His torso is behind foreground furniture, but the active arm is in front.
    if orientation=='landscape':
        cx,cy=149,165; tw=132; top=214; bot=523
    else:
        cx,cy=46,289; tw=124; top=345; bot=795
    hair='#253d50';skin='#d7a17e'
    add(f'<path d="M {_fmt(cx-tw*.60)} {_fmt(top+29)} Q {_fmt(cx-tw*.60)} {_fmt(top-8)} {_fmt(cx-tw*.27)} {_fmt(top-3)} L {_fmt(cx+tw*.36)} {_fmt(top-5)} Q {_fmt(cx+tw*.68)} {_fmt(top+17)} {_fmt(cx+tw*.57)} {_fmt(bot)} H {_fmt(cx-tw*.64)} Z" fill="#233e51" stroke="#1e3142" stroke-width="5"/>')
    add(f'<path d="M {_fmt(cx-tw*.42)} {_fmt(top+5)} Q {_fmt(cx-tw*.42)} {_fmt(top+65)} {_fmt(cx-tw*.24)} {_fmt(bot)}" fill="none" stroke="#527b8b" stroke-width="6" opacity=".7"/>')
    add(f'<path d="M {_fmt(cx-tw*.08)} {_fmt(top+9)} L {_fmt(cx+tw*.25)} {_fmt(top+12)} L {_fmt(cx+tw*.33)} {_fmt(bot)} H {_fmt(cx-tw*.28)} Z" fill="#c5b69c" stroke="#7d796b" stroke-width="3"/>')
    add(f'<path d="M {_fmt(cx-tw*.12)} {_fmt(top+38)} L {_fmt(cx+tw*.23)} {_fmt(top+38)} M {_fmt(cx-tw*.25)} {_fmt(top+95)} L {_fmt(cx+tw*.30)} {_fmt(top+95)}" stroke="#88918a" stroke-width="3" opacity=".55"/>')
    add(f'<path d="M {_fmt(cx-23)} {_fmt(top-30)} Q {_fmt(cx)} {_fmt(top+7)} {_fmt(cx+17)} {_fmt(top-30)}" fill="#d8a17e" stroke="#765c4c" stroke-width="3"/>')
    # Slight focus shift toward his physically contacting hand.
    look=5*pull
    add(f'<path d="M {_fmt(cx-36)} {_fmt(cy-30)} Q {_fmt(cx-43)} {_fmt(cy-69)} {_fmt(cx)} {_fmt(cy-71)} Q {_fmt(cx+43)} {_fmt(cy-65)} {_fmt(cx+40)} {_fmt(cy-24)} L {_fmt(cx+35)} {_fmt(cy+12)} Q {_fmt(cx+25)} {_fmt(cy+45)} {_fmt(cx)} {_fmt(cy+46)} Q {_fmt(cx-37)} {_fmt(cy+35)} {_fmt(cx-37)} {_fmt(cy-19)} Z" fill="#dbab85" stroke="#5a5150" stroke-width="4"/>')
    add(f'<path d="M {_fmt(cx-43)} {_fmt(cy-25)} L {_fmt(cx-45)} {_fmt(cy-55)} L {_fmt(cx-25)} {_fmt(cy-82)} L {_fmt(cx-4)} {_fmt(cy-69)} L {_fmt(cx+11)} {_fmt(cy-92)} L {_fmt(cx+29)} {_fmt(cy-67)} L {_fmt(cx+41)} {_fmt(cy-68)} L {_fmt(cx+44)} {_fmt(cy-28)} Q {_fmt(cx+16)} {_fmt(cy-41)} {_fmt(cx+2)} {_fmt(cy-47)} L {_fmt(cx-18)} {_fmt(cy-33)} Z" fill="{hair}" stroke="#243949" stroke-width="3"/>')
    # Brow/eye attitude is understated, and blink pose is a real graphic key.
    for eyex in (cx-15,cx+19):
        add(f'<path d="M {_fmt(eyex-8)} {_fmt(cy-10)} Q {_fmt(eyex)} {_fmt(cy-15)} {_fmt(eyex+8)} {_fmt(cy-7)}" fill="none" stroke="#263746" stroke-width="3.2"/>')
        if int(t*4)%21==9:
            add(f'<path d="M {_fmt(eyex-5)} {_fmt(cy+3)} L {_fmt(eyex+5)} {_fmt(cy+3)}" stroke="#263746" stroke-width="2.5"/>')
        else:
            add(f'<ellipse cx="{_fmt(eyex+look)}" cy="{_fmt(cy+4)}" rx="3.3" ry="4.2" fill="#253746"/>')
    add(f'<path d="M {_fmt(cx+3)} {_fmt(cy+6)} Q {_fmt(cx-1)} {_fmt(cy+17)} {_fmt(cx+4)} {_fmt(cy+21)}" stroke="#a87862" stroke-width="2" fill="none"/>')
    add(f'<path d="M {_fmt(cx-4)} {_fmt(cy+31)} Q {_fmt(cx+8)} {_fmt(cy+35-2*tuck)} {_fmt(cx+16)} {_fmt(cy+29)}" fill="none" stroke="#765b51" stroke-width="2.5"/>')
    # Painter protective workcloth, furniture must visibly have depth underneath.
    add(f'<ellipse cx="{_fmt(x+w*.53)}" cy="{_fmt(y+h*.94)}" rx="{_fmt(w*.53)}" ry="{_fmt(h*.14)}" fill="#554b42" opacity=".20" filter="url(#blur)"/>')
    add(f'<path d="M {_fmt(x+w*.1)} {_fmt(y+h*.16)} Q {_fmt(x+w*.16)} {_fmt(y-h*.07)} {_fmt(x+w*.3)} {_fmt(y+h*.04)} H {_fmt(x+w*.8)} Q {_fmt(x+w*.94)} {_fmt(y+h*.01)} {_fmt(x+w*.94)} {_fmt(y+h*.27)} L {_fmt(x+w*.9)} {_fmt(y+h*.66)} H {_fmt(x+w*.12)} Z" fill="url(#back)" stroke="#5b4a42" stroke-width="5"/>')
    add(f'<rect x="{_fmt(x+w*.05)}" y="{_fmt(y+h*.38)}" width="{_fmt(w*.9)}" height="{_fmt(h*.43)}" rx="{_fmt(h*.095)}" fill="#b58e70" stroke="#634e46" stroke-width="5"/>')
    for f in (.27,.49,.71):
        cc=x+w*f
        add(f'<rect x="{_fmt(cc-w*.10)}" y="{_fmt(y+h*.35)}" width="{_fmt(w*.195)}" height="{_fmt(h*.41)}" rx="{_fmt(h*.07)}" fill="#c49e7e" stroke="#9d8068" stroke-width="3"/>')
    add(f'<path d="M {_fmt(x+w*.1)} {_fmt(y+h*.8)} v {_fmt(h*.13)} M {_fmt(x+w*.9)} {_fmt(y+h*.8)} v {_fmt(h*.13)}" stroke="#493d3a" stroke-width="12" stroke-linecap="round"/>')
    # The cloth hem advances in the direction of the pull and develops geometry.
    # Left portion is already over the furniture at 108.0 (previous shot continuity).
    progress=smooth((t-.28)/3.2)
    cover_x=x+w*(.60+.40*progress)
    # Backrest is progressively draped too: a protected couch cannot finish with
    # the entire brown back exposed behind an otherwise white front cloth.
    back_cover=smooth((t-2.6)/2.8)
    # Surface top and front produce independent shading & a visible rounded edge.
    add(f'<path d="M {_fmt(x+w*.035)} {_fmt(y+h*(.30-.23*back_cover))} Q {_fmt(x+w*.06)} {_fmt(y+h*(.13-.12*back_cover))} {_fmt(x+w*.19)} {_fmt(y+h*(.17-.17*back_cover))} L {_fmt(cover_x-8)} {_fmt(y+h*(.20-.18*back_cover)+flutter*.1)} Q {_fmt(cover_x+19)} {_fmt(y+h*(.28-.06*back_cover))} {_fmt(cover_x+4)} {_fmt(y+h*.42)} L {_fmt(x+w*.06)} {_fmt(y+h*.47)} Z" fill="url(#clothTop)" stroke="#a2ada5" stroke-width="3"/>')
    low=[]
    for i in range(15):
        f=i/14;px=x+w*.06+(cover_x-(x+w*.06))*f
        yy=hem_base+math.sin(f*18.8+t*1.3)*(4.5*(1-release))+6*math.sin(9*f)*(.35+.65*pull)
        if f<.06 or f>.96: yy-=5
        low.append((px,yy))
    top=[(x+w*.06,y+h*.47),(x+w*.25,y+h*.41),(cover_x-16,y+h*.43),(cover_x+4,y+h*.50)]
    outline=_catmull(top+list(reversed(low)),True)
    add(f'<path d="{outline}" fill="url(#clothFront)" stroke="#a3b6b1" stroke-width="3"/>')
    add(f'<path d="{_catmull(low)}" fill="none" stroke="#90a9a4" stroke-width="3" opacity=".6"/>')
    # Volumetric fabric ridges converge toward the grip, with damped recovery.
    for k in range(1,9):
        f=k/10; px=x+w*.08+(cover_x-x-w*.12)*f
        offset=8*math.sin(k*1.43+t*.8)*(1-release)+4*math.cos(k*1.1)
        p=[(px-12,y+h*.46),(px+offset,y+h*.58),(px+offset*.8+4,hem_base-7)]
        add(f'<path d="{_catmull(p)}" fill="none" stroke="{["#bacac5","#fafcf3","#9db4af"][k%3]}" stroke-width="{2 if k%2 else 4}" opacity="{.36+.14*math.sin(k)}"/>')
    # Narrowed grip fold: deformation originates precisely under the fingers.
    grip=st['contact']; gx,gy=grip
    compression=1-release
    add(f'<path d="M {_fmt(gx)} {_fmt(gy+2)} Q {_fmt(gx+20)} {_fmt(gy+12+5*compression)} {_fmt(gx+37)} {_fmt(gy+43)}" fill="none" stroke="#819c96" stroke-width="4" opacity="{.70*compression:.3f}"/>')
    add(f'<path d="M {_fmt(gx)} {_fmt(gy+2)} Q {_fmt(gx-11)} {_fmt(gy+23)} {_fmt(gx-25)} {_fmt(gy+57)}" fill="none" stroke="#ffffff" stroke-width="3" opacity="{.80*compression:.3f}"/>')
    # Arm is one continuous shoulder->elbow->wrist shape with a real cuff and
    # hand; off-frame cropping is intentional close-up composition.
    fore=(hx-3,hy-4)
    # Deliberate TWO articulated sleeve masses (upper arm + forearm), not a
    # bezier tube from offscreen. The elbow patch masks joins under the fabric.
    upper_path=f'M {_fmt(sx)} {_fmt(sy)} Q {_fmt((sx+ex)*.5)} {_fmt((sy+ey)*.5-8)} {_fmt(ex)} {_fmt(ey)}'
    lower_path=f'M {_fmt(ex)} {_fmt(ey)} Q {_fmt((ex+fore[0])*.5)} {_fmt((ey+fore[1])*.5+3)} {_fmt(fore[0])} {_fmt(fore[1])}'
    for path,width in ((upper_path,47),(lower_path,37)):
        add(f'<path d="{path}" fill="none" stroke="#1c3143" stroke-width="{width+7}" stroke-linecap="round"/>')
        add(f'<path d="{path}" fill="none" stroke="url(#sleeve)" stroke-width="{width}" stroke-linecap="round"/>')
    add(f'<circle cx="{_fmt(ex)}" cy="{_fmt(ey)}" r="22" fill="#345768" stroke="#1d384c" stroke-width="3"/>')
    add(f'<path d="M {_fmt(ex-15)} {_fmt(ey+1)} Q {_fmt(ex+2)} {_fmt(ey+15)} {_fmt(ex+19)} {_fmt(ey+2)}" fill="none" stroke="#8fa4a3" stroke-width="2.5" opacity=".7"/>')
    add(f'<path d="{upper_path}" fill="none" stroke="#698996" stroke-width="4" opacity=".63"/>')
    add(f'<path d="{lower_path}" fill="none" stroke="#6f96a6" stroke-width="3.5" opacity=".6"/>')
    # Narrow cuff at wrist, naturally fitted rather than a giant orange dot.
    add(f'<path d="M {_fmt(fore[0]-5)} {_fmt(fore[1]-15)} Q {_fmt(fore[0]+6)} {_fmt(fore[1]-5)} {_fmt(fore[0]+3)} {_fmt(fore[1]+13)}" fill="none" stroke="#d6c6aa" stroke-width="12" stroke-linecap="round"/>')
    # Hand: palm + independently drawn thumb and pinching fingers, real contact.
    # Grip tip derives from same shared coordinates as fabric wrinkles.
    skin='#d7a17e';outline='#6c564c'
    palm=f'M {_fmt(hx-6)} {_fmt(hy-16)} Q {_fmt(hx+7)} {_fmt(hy-26)} {_fmt(hx+15)} {_fmt(hy-8)} L {_fmt(hx+22)} {_fmt(hy+7)} Q {_fmt(hx+19)} {_fmt(hy+20)} {_fmt(hx+4)} {_fmt(hy+18)} L {_fmt(hx-8)} {_fmt(hy+5)} Z'
    add(f'<path d="{palm}" fill="{skin}" stroke="{outline}" stroke-width="2.8"/>')
    finger_x,finger_y=grip
    add(f'<path d="M {_fmt(hx+12)} {_fmt(hy-5)} Q {_fmt(hx+23)} {_fmt(hy-3)} {_fmt(finger_x)} {_fmt(finger_y)}" fill="none" stroke="{outline}" stroke-width="10" stroke-linecap="round"/>')
    add(f'<path d="M {_fmt(hx+12)} {_fmt(hy-5)} Q {_fmt(hx+23)} {_fmt(hy-3)} {_fmt(finger_x)} {_fmt(finger_y)}" fill="none" stroke="{skin}" stroke-width="7" stroke-linecap="round"/>')
    add(f'<path d="M {_fmt(hx+6)} {_fmt(hy+8)} Q {_fmt(hx+16)} {_fmt(hy+17)} {_fmt(finger_x-2)} {_fmt(finger_y+4)}" fill="none" stroke="{outline}" stroke-width="9" stroke-linecap="round"/>')
    add(f'<path d="M {_fmt(hx+6)} {_fmt(hy+8)} Q {_fmt(hx+16)} {_fmt(hy+17)} {_fmt(finger_x-2)} {_fmt(finger_y+4)}" fill="none" stroke="{skin}" stroke-width="6" stroke-linecap="round"/>')
    # No dashboard, no subtitle; close on material change. Stage-safe frame.
    add('</svg>')
    return ''.join(body)

if __name__=='__main__':
    import argparse,pathlib
    p=argparse.ArgumentParser();p.add_argument('--t',type=float,default=2.4);p.add_argument('--view',choices=LAYOUTS,default='landscape');p.add_argument('--out',required=True)
    args=p.parse_args();pathlib.Path(args.out).write_text(svg_frame(args.t,args.view))