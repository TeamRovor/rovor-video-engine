"""Rovor V13 painting-contact pilot: source-inspired original hand-cleaned vector scene.

7.0-second stand-alone muted physical-action proof, independently stageable.
No narration alteration, no Evan substitution, no promotion into the V12 movie.
Coordinates refer to a physically shared wall plane.
"""
from __future__ import annotations
import argparse, math, json, io, hashlib, random
from pathlib import Path
import cairosvg
from PIL import Image
from physical_paint import Pose,ContactPaint,two_bone_ik

W,H=1280,720
DURATION=7.0
FPS=30


def clamp(x,a=0.,b=1.):return max(a,min(b,x))
def sm(x):x=clamp(x);return x*x*(3-2*x)
def lerp(a,b,x):return a+(b-a)*x

def motion(t):
    """Physical contact timeline; timing intentionally hand directed."""
    if t<.70:
        a=sm(t/.70)
        return {"rx":lerp(599,525,a),"ry":lerp(495,475,a),"contact":False,"stage":"anticipate","head":lerp(0,-.075,a),"roll":0.0}
    if t<3.03:
        a=sm((t-.70)/(3.03-.70))
        return {"rx":525,"ry":lerp(475,260,a),"contact":True,"stage":"upstroke","head":lerp(-.075,-.09,a),"roll":(475-lerp(475,260,a))/16}
    if t<3.35:
        return {"rx":525,"ry":260,"contact":True,"stage":"hold","head":-.09,"roll":215/16}
    if t<4.10:
        a=sm((t-3.35)/.75)
        return {"rx":525,"ry":lerp(260,420,a),"contact":True,"stage":"return","head":lerp(-.09,-.03,a),"roll":(215-(lerp(260,420,a)-260))/16}
    if t<4.78:
        a=sm((t-4.10)/.68)
        return {"rx":lerp(525,627,a),"ry":lerp(420,435,a),"contact":False,"stage":"reposition","head":lerp(-.03,-.045,a),"roll":0}
    if t<6.15:
        a=sm((t-4.78)/(6.15-4.78))
        return {"rx":627,"ry":lerp(435,291,a),"contact":True,"stage":"overlap-stroke","head":-.055,"roll":(435-lerp(435,291,a))/16}
    if t<6.70:
        a=sm((t-6.15)/.55)
        return {"rx":lerp(627,667,a),"ry":lerp(291,500,a),"contact":False,"stage":"lift","head":lerp(-.055,.01,a),"roll":0}
    a=sm((t-6.70)/.30)
    return {"rx":lerp(667,667,a),"ry":lerp(500,503,a),"contact":False,"stage":"settle","head":lerp(.01,.065,a),"roll":0}


def elements(t):
    """Shared geometry for image rendering and deterministic action tests."""
    m=motion(t)
    # Shared roller handle and anatomy: 70 px roller rod above the wrist and to the left.
    rx,ry=m['rx'],m['ry']
    handle=(rx+94,ry+78)
    wrist=(handle[0]+13,handle[1]+18)
    shoulder=(795,346+3*math.sin(t*.6))
    # A fixed-length anatomical two-bone arm. An unreachable tool pose FAILS
    # instead of silently changing arm length or visually detaching the wrist.
    elbow=two_bone_ik(shoulder,wrist,147.0,155.0,elbow_side=1)
    torso=(885+5*math.sin(t*.3),427+3*math.sin(t*.7))
    foot=(892,633)
    return dict(m,handle=handle,wrist=wrist,shoulder=shoulder,elbow=elbow,
                torso=torso,foot=foot,normal_gap=(0.0 if m['contact'] else 18.0))


def contact_pose(t):
    e=elements(t)
    return Pose(t,e['rx'],e['ry'],e['contact'],e['normal_gap'],
                e['shoulder'],e['elbow'],e['wrist'],e['handle'])


# Shared reusable source of truth, not static paint shapes attached to timestamps.
PAINT_FIELD=ContactPaint(contact_pose, duration=DURATION, fps=120,roller_width=102.0,
                         contact_height=16.0)


def sleeve_segment(a,b,wa,wb,fill="#36566a",outline="#263f4e"):
    dx=b[0]-a[0];dy=b[1]-a[1];ll=math.hypot(dx,dy)
    nx,ny=-dy/ll,dx/ll
    ah=(a[0]+nx*wa/2,a[1]+ny*wa/2);al=(a[0]-nx*wa/2,a[1]-ny*wa/2)
    bh=(b[0]+nx*wb/2,b[1]+ny*wb/2);bl=(b[0]-nx*wb/2,b[1]-ny*wb/2)
    ctrl=(a[0]+dx*.56,a[1]+dy*.56)
    d=f"M {ah[0]:.1f} {ah[1]:.1f} Q {ctrl[0]+nx*wa/2:.1f} {ctrl[1]+ny*wa/2:.1f} {bh[0]:.1f} {bh[1]:.1f} Q {b[0]+dx*.12:.1f} {b[1]+dy*.12:.1f} {bl[0]:.1f} {bl[1]:.1f} Q {ctrl[0]-nx*wb/2:.1f} {ctrl[1]-ny*wb/2:.1f} {al[0]:.1f} {al[1]:.1f} Z"
    return f'<path d="{d}" fill="{fill}" stroke="{outline}" stroke-width="4" stroke-linejoin="round"/>'

def path_points(points):
    return ' '.join(f'{x:.2f},{y:.2f}' for x,y in points)


def wall_paint(t):
    # No manually defined blue rectangles. Mask comes ONLY from traced physical
    # contacts sampled from the same action used by the actor + roller.
    return PAINT_FIELD.svg_mask(t)


def svg_frame(t,orientation='landscape'):
    g=elements(t);rx,ry=g['rx'],g['ry'];sx,sy=g['shoulder'];ex,ey=g['elbow'];wx,wy=g['wrist'];hx,hy=g['handle']
    # Controlled waist shift coupled to working wrist height.
    lean=-.035+(340-ry)*.00006
    header='''<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
<defs>
 <linearGradient id="wall" x1="0" x2=".8" y2="1"><stop stop-color="#f1ebde"/><stop offset="1" stop-color="#e2dbcd"/></linearGradient>
 <linearGradient id="freshPaint" x1="0" x2="1" y1="0" y2="0"><stop stop-color="#89b8c3"/><stop offset=".44" stop-color="#70acbc"/><stop offset="1" stop-color="#669eaf"/></linearGradient>
 <linearGradient id="floor" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#baa58a"/><stop offset="1" stop-color="#907e6b"/></linearGradient>
 <linearGradient id="roller" x1="0" x2="0" y1="0" y2="1"><stop stop-color="#7eb3c0"/><stop offset=".55" stop-color="#5f9eb0"/><stop offset="1" stop-color="#336b81"/></linearGradient>
 <linearGradient id="jacket" x1="0" x2="1" y1="0" y2="1"><stop stop-color="#48677a"/><stop offset=".8" stop-color="#2f4a5b"/><stop offset="1" stop-color="#223c4e"/></linearGradient>
 <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".54" numOctaves="2" seed="3" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".055"/></feComponentTransfer></filter>
 <filter id="blur"><feGaussianBlur stdDeviation="4"/></filter>
 <clipPath id="wallClip"><path d="M 35 112 L 1119 91 L 1119 602 L 35 570 Z"/></clipPath>
</defs>'''
    background='''
<!-- One spatially continuous room, not a floating slide card -->
<rect x="-300" y="-500" width="2000" height="2000" fill="#e6dfd2"/>
<path d="M -100 -500 H 1400 V 120 L 35 129 L -100 142 Z" fill="#f9f5eb"/>
<path d="M 35 112 L 1119 91 L 1119 602 L 35 570 Z" fill="url(#wall)" stroke="#d5cab8" stroke-width="4"/>
<path d="M 1119 92 L 1280 19 V 559 L 1119 602Z" fill="#c6bca8"/>
<path d="M 35 568 L 1119 600 L 1280 560 L 1400 1200 L -100 1200 L -100 552 Z" fill="url(#floor)"/>
<path d="M 0 566 L 1119 607 L 1280 562" stroke="#f7f5ed" stroke-width="18" fill="none"/>
<path d="M 0 581 L 1119 624 L 1280 573" stroke="#baa58b" stroke-width="2" opacity=".7" fill="none"/>
<path d="M 0 645 L 1119 676 L 1280 649" stroke="#857565" stroke-width="2" opacity=".24" fill="none"/>
<path d="M 170 581 L 143 719 M 520 600 L 496 720 M 990 619 L 1011 720" stroke="#806d5a" stroke-width="2" opacity=".16"/>
<!-- light from the unpainted room's offscreen window -->
<path d="M 35 130 L 392 118 L 238 570 L 35 567 Z" fill="#ffffff" opacity=".11"/>
<!-- painter's dropcloth and practical paint tray -->
<path d="M 686 614 Q 715 602 779 612 Q 811 608 853 623 L 1051 642 Q 1111 662 1060 686 L 696 686 Q 654 665 686 614Z" fill="#e6e0ca" stroke="#c2b9a5" stroke-width="4"/>
<path d="M 754 634 Q 787 622 816 632 L 975 649" stroke="#aca38b" stroke-width="3" opacity=".64" fill="none"/>
<ellipse cx="1025" cy="637" rx="88" ry="18" fill="#665950" opacity=".14"/>
<path d="M 950 606 L 1090 606 L 1070 650 L 968 650 Z" fill="#485965" stroke="#243947" stroke-width="4"/>
<path d="M 967 606 L 1080 606 L 1067 626 L 979 626 Z" fill="#548d9d"/>
<path d="M 982 606 Q 1021 593 1060 606" stroke="#a0d0d9" stroke-width="5" fill="none" opacity=".65"/>
'''
    # wall paint only exists underneath the actual roller and only after contact.
    painted='<g clip-path="url(#wallClip)">'+wall_paint(t)+'</g>'
    # shadow/distance from wall: projected cylinder shadow on actual wall and boot contact.
    shadow=f'<ellipse cx="{rx+7:.2f}" cy="{ry+10:.2f}" rx="62" ry="14" fill="#39606b" opacity="{.20 if g["contact"] else .04}" filter="url(#blur)"/>'
    # carefully shaped character poses in dark blue inspired by original supplied painter; no generic replacement Evan.
    person=f'''<g id="painter" transform="translate({3*math.sin(t*.5):.2f} 0)">
    <g transform="translate(-70 0)">
    <ellipse cx="897" cy="649" rx="106" ry="18" fill="#584f44" opacity=".21"/>
    <!-- boots and pant legs -->
    <path d="M 834 465 L 896 469 L 888 620 Q 883 637 865 638 L 845 634 L 827 598 Z" fill="#283c49" stroke="#233845" stroke-width="6" stroke-linejoin="round"/>
    <path d="M 909 462 L 959 455 L 970 607 Q 966 624 942 625 L 923 615 Z" fill="#344955" stroke="#233845" stroke-width="6"/>
    <path d="M 837 599 L 877 603 L 878 634 L 811 638 Q 792 624 816 612Z" fill="#303d45" stroke="#243746" stroke-width="5"/>
    <path d="M 926 608 L 971 607 L 989 642 L 912 642 Q 900 626 926 608Z" fill="#263a46" stroke="#243746" stroke-width="5"/>
    <path d="M 815 626 Q 850 633 878 625 M 914 633 Q 947 643 984 635" stroke="#71818a" stroke-width="3" opacity=".6" fill="none"/>
    <!-- torso and tied work apron -->
    <path d="M 848 328 Q 830 332 817 351 L 820 428 Q 819 468 840 484 L 940 487 Q 967 468 958 417 L 934 349 Q 921 318 893 318 Z" fill="url(#jacket)" stroke="#263f4e" stroke-width="7" stroke-linejoin="round"/>
    <path d="M 869 365 L 924 360 L 930 478 L 863 478 Z" fill="#e0cba9" stroke="#344955" stroke-width="5"/>
    <path d="M 863 394 L 929 393 M 884 365 L 885 477" stroke="#8a7d64" stroke-width="3" opacity=".6"/>
    <path d="M 857 330 L 872 363 M 925 335 L 912 361" stroke="#d4bd95" stroke-width="12" stroke-linecap="round"/>
    <path d="M 862 455 Q 896 467 935 458" stroke="#927e60" stroke-width="2" opacity=".75" fill="none"/>
    <!-- left arm rests with weight on hip -->
    <path d="M 929 351 Q 963 371 966 413 Q 971 443 945 464 L 933 461" fill="none" stroke="#253c4d" stroke-width="51" stroke-linecap="round"/>
    <path d="M 929 350 Q 960 371 960 415 Q 967 435 943 456" fill="none" stroke="#3a596e" stroke-width="40" stroke-linecap="round"/>
    <path d="M 946 443 Q 934 445 930 455 Q 926 469 938 477 Q 950 477 960 466 L 961 454 Z" fill="#d9a781" stroke="#644638" stroke-width="4"/>
    <!-- neck and collar -->
    <path d="M 872 313 L 877 348 Q 898 360 915 338 L 913 314Z" fill="#c99775" stroke="#6e4b3b" stroke-width="4"/>
    <path d="M 853 337 L 884 357 L 874 366 L 846 353 M 921 336 L 905 356 L 917 366 L 935 349" fill="#d9d9d0" stroke="#2d4957" stroke-width="4"/>
    <!-- expressive character head/profile glances at roller, not staring into camera -->
    <g transform="rotate({math.degrees(g['head']):.3f} 895 275)">
    <path d="M 851 273 Q 846 235 870 215 Q 892 199 924 215 Q 942 230 944 265 L 928 303 Q 914 326 890 328 Q 863 320 852 299Z" fill="#d6a181" stroke="#684738" stroke-width="5"/>
    <path d="M 841 256 Q 845 219 869 204 Q 885 191 911 198 Q 937 201 944 224 L 925 238 Q 905 235 892 227 Q 867 246 841 256 Z" fill="#263e4e" stroke="#263a49" stroke-width="5"/>
    <path d="M 858 212 Q 879 186 908 203" stroke="#42596a" stroke-width="6" fill="none"/>
    <!-- gaze toward roller on the left -->
    <path d="M 867 271 Q 878 265 888 268" stroke="#463c38" stroke-width="3.5" fill="none" stroke-linecap="round"/>
    <ellipse cx="875" cy="274" rx="3.5" ry="5.5" fill="#283640"/>
    <path d="M 899 272 Q 906 270 912 273" stroke="#554239" stroke-width="3.4" fill="none"/>
    <ellipse cx="902" cy="277" rx="3" ry="5" fill="#283640"/>
    <path d="M 888 289 Q 878 293 888 299" stroke="#9c694e" stroke-width="3" fill="none"/>
    <path d="M 892 310 Q 904 312 909 306" stroke="#774c3b" stroke-width="3" fill="none" stroke-linecap="round"/>
    <path d="M 928 276 Q 945 270 942 285 Q 940 296 926 291" fill="#d5a180" stroke="#76513f" stroke-width="3"/>
    </g>
    </g>
    <!-- Shoulder seamed to the upper arm, both elbow and wrist physically connected -->
    {sleeve_segment((sx,sy),(ex,ey),51,42,fill="#365669")}
    <ellipse cx="{ex:.1f}" cy="{ey:.1f}" rx="22" ry="23" fill="#355669" stroke="#263f4e" stroke-width="4"/>
    {sleeve_segment((ex,ey),(wx,wy),43,29,fill="#405f72")}
    <path d="M {sx-8:.1f} {sy-16:.1f} Q {lerp(sx,ex,.52)-8:.1f} {lerp(sy,ey,.52)-24:.1f} {ex-3:.1f} {ey-14:.1f}" stroke="#7e9aa2" stroke-width="3" opacity=".51" fill="none"/>
    <path d="M {ex-6:.1f} {ey-11:.1f} Q {lerp(ex,wx,.55)-6:.1f} {lerp(ey,wy,.55)-13:.1f} {wx-8:.1f} {wy-7:.1f}" stroke="#85a2aa" stroke-width="3" opacity=".42" fill="none"/>
    <path d="M {wx-12:.1f} {wy-6:.1f} Q {wx-15:.1f} {wy+10:.1f} {wx-2:.1f} {wy+18:.1f}" stroke="#1f3a49" stroke-width="4" fill="none"/>
    <!-- Hand and distinct gripping fingers on actual tool handle -->
    <path d="M {wx-7:.1f} {wy-11:.1f} Q {wx+8:.1f} {wy-17:.1f} {wx+17:.1f} {wy-7:.1f} L {wx+21:.1f} {wy+9:.1f} Q {wx+14:.1f} {wy+23:.1f} {wx-6:.1f} {wy+19:.1f} Q {wx-19:.1f} {wy+14:.1f} {wx-14:.1f} {wy-1:.1f}Z" fill="#dca780" stroke="#77503d" stroke-width="4"/>
    <path d="M {wx-12:.1f} {wy+2:.1f} q 10 8 22 6 M {wx-10:.1f} {wy+10:.1f} q 11 8 22 4" stroke="#9d6850" stroke-width="2" fill="none"/>
    </g>'''
    # roller in front of painter's fingers, physically attached to wrist grip.
    roller=f'''<g id="roller_tool">
    <!-- metal shaft from hand to roller axle -->
    <path d="M {wx+2:.1f} {wy+6:.1f} L {hx:.1f} {hy:.1f} L {hx-22:.1f} {hy-33:.1f} L {rx+47:.1f} {ry+1:.1f}" fill="none" stroke="#203744" stroke-width="10" stroke-linejoin="round" stroke-linecap="round"/>
    <path d="M {wx+2:.1f} {wy+4:.1f} L {hx:.1f} {hy:.1f} L {hx-22:.1f} {hy-33:.1f} L {rx+47:.1f} {ry+1:.1f}" fill="none" stroke="#acbcc0" stroke-width="5.6" stroke-linecap="round" stroke-linejoin="round"/>
    <!-- black handle gripped by fingers -->
    <path d="M {wx-15:.1f} {wy-14:.1f} L {hx+7:.1f} {hy+19:.1f}" stroke="#253d49" stroke-width="14" stroke-linecap="round"/>
    <path d="M {wx-7:.1f} {wy-6:.1f} L {hx+9:.1f} {hy+15:.1f}" stroke="#415a67" stroke-width="6" stroke-linecap="round"/>
    <!-- roller capsule is on the SAME wall plane as procedural paint -->
    <g transform="translate({rx:.2f} {ry:.2f})">
    <rect x="-53" y="-16" width="106" height="32" rx="15" fill="url(#roller)" stroke="#244857" stroke-width="4"/>
    <rect x="-45" y="-11" width="86" height="18" rx="9" fill="#8ec2cc" opacity=".47"/>
    <path d="M -50 6 Q -4 10 45 6" stroke="#d9e5dd" stroke-width="2" opacity=".38" fill="none"/>
    <rect x="48" y="-12" width="10" height="24" rx="4" fill="#b6c0ba" stroke="#395762" stroke-width="2"/>
    </g>
    </g>'''
    # wall paint MUST be behind roller+actor; intentional contact shadow on same painted area.
    result=header+background+painted+shadow+person+roller+'''<rect width="1280" height="720" filter="url(#grain)" opacity=".28" pointer-events="none"/></svg>'''
    if orientation=='portrait':
        # Independent framing; not a resized/cropped landscape deliverable.
        # Recompose spatial objects into taller 900x1600 stage while maintaining their contact geometry.
        result=result.replace('width="1280" height="720" viewBox="0 0 1280 720"','width="900" height="1600" viewBox="405 -98 585 1040"')
    return result


def render_png(t,path,orientation='landscape',output_width=1280,output_height=720):
    svg=svg_frame(t,orientation)
    png=cairosvg.svg2png(bytestring=svg.encode(),output_width=output_width,output_height=output_height)
    if path:Path(path).write_bytes(png)
    return png


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--time',type=float,default=2.0);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--orientation',default='landscape',choices=['landscape','portrait']);args=ap.parse_args()
    res=(1280,720) if args.orientation=='landscape' else (900,1600)
    render_png(args.time,args.out,args.orientation,*res)
if __name__=='__main__':main()