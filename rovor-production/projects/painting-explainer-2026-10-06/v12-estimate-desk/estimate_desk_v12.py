"""Original, editable hand-illustrated 2D tabletop scene for the Oct 2026 Rovor painter film.

Source seconds [29.2,41.4), 60 fps: quotes are placed then the same generic
promises are physically stamped onto each. This is a *development art pass*.
Portrait is independently staged; no live action, external stock or fake customers.
"""
import math
from xml.sax.saxutils import escape
FPS=60
START_FRAME=1752
END_FRAME=2484
FRAME_COUNT=END_FRAME-START_FRAME
SOURCE_SHA='346c9ea17f2ca4a7dea5b19248e6cddc113ae1a4e27b37b31049567ed2e47e45'

def clamp(x,a=0,b=1):return max(a,min(b,x))
def sm(x):x=clamp(x);return x*x*(3-2*x)
def lerp(a,b,x):return a+(b-a)*x

def paper(cx,cy,w,h,rotation,letter,appearance,side,stamped):
    # title and ruled sections are original drawn art; intentionally no invented quote prices.
    return f'''<g opacity="{appearance:.4f}" transform="translate({cx:.3f} {cy:.3f}) rotate({rotation:.3f})">
    <rect x="{-w/2+7}" y="{-h/2+12}" width="{w}" height="{h}" rx="5" fill="#102e3e" opacity=".22"/>
    <path d="M {-w/2} {-h/2+4} Q {-w/2} {-h/2} {-w/2+5} {-h/2} L {w/2-5} {-h/2} Q {w/2} {-h/2} {w/2} {-h/2+6} L {w/2} {h/2-6} Q {w/2} {h/2} {w/2-5} {h/2} L {-w/2+5} {h/2} Q {-w/2} {h/2} {-w/2} {h/2-5} Z" fill="#fff9eb" stroke="#213f4b" stroke-width="2.2"/>
    <path d="M {-w/2+17} {-h/2+39} H {w/2-17}" stroke="#ddcdb0" stroke-width="1"/>
    <text x="{-w/2+20}" y="{-h/2+27}" font-family="DejaVu Sans" font-size="16" letter-spacing="2" font-weight="bold" fill="#133b46">ESTIMATE {letter}</text>
    <text x="{w/2-18}" y="{-h/2+25}" font-family="DejaVu Sans" font-size="9" text-anchor="end" fill="#87959a">PAINTING</text>
    <g stroke="#929a93" stroke-width="2" stroke-linecap="round" opacity=".7">
    <path d="M {-w/2+22} {-h/2+64} h {w-44}"/><path d="M {-w/2+22} {-h/2+83} h {w-66}"/>
    <path d="M {-w/2+22} {-h/2+105} h {w-49}"/><path d="M {-w/2+22} {-h/2+124} h {w-83}"/>
    <path d="M {-w/2+22} {-h/2+147} h {w-62}"/>
    </g>
    <rect x="{-w/2+20}" y="{-h/2+158}" width="{w-40}" height="{h*.20}" rx="4" fill="#f0e9d8" stroke="#d1c9b6" stroke-width="1"/>
    <text x="{-w/2+30}" y="{-h/2+183}" font-family="DejaVu Sans" font-size="12" letter-spacing=".2" fill="#8a877e">Work scope:</text>
    <path d="M {-w/2+30} {-h/2+197} H {w/2-27}" stroke="#c1c3b9" stroke-width="2" stroke-dasharray="7 6" />
    <g stroke="#c4b8a3" stroke-width="2" opacity=".9">
       <path d="M {-w/2+25} {h/2-66} H {w/2-24}"/>
       <path d="M {-w/2+25} {h/2-48} H {w/2-60}"/>
    </g>
    <path d="M {-w/2+24} {h/2-23} h 64" stroke="#8199a0" stroke-width="2.1"/>
    <text x="{-w/2+22}" y="{h/2-83}" font-family="DejaVu Sans" font-size="8" fill="#b6ac97">DETAILS NOT PROVIDED</text>
    {seal(w,h,stamped)}
    </g>'''

def seal(w,h,stamped):
    if stamped<=0:return ''
    op=sm(stamped)
    # physical print—not a label floating separately from the estimate.
    return f'''<g transform="translate(0 {h*.065:.1f}) rotate(-7)" opacity="{op:.3f}">
        <rect x="{-w*.36:.1f}" y="-27" width="{w*.72:.1f}" height="70" rx="5" fill="none" stroke="#b95b4d" stroke-width="3.7"/>
        <text x="0" y="-1" text-anchor="middle" font-family="DejaVu Sans" font-size="17" font-weight="bold" fill="#b95b4d">QUALITY WORK</text>
        <path d="M {-w*.29:.1f} 10 H {w*.29:.1f}" stroke="#b95b4d" stroke-width="2"/>
        <text x="0" y="31" text-anchor="middle" font-family="DejaVu Sans" font-size="15" font-weight="bold" fill="#b95b4d">FREE ESTIMATES</text>
        </g>'''

def cloth_prop(w,h):
    return f'''<g transform="translate(29 35) rotate(-7)">
      <path d="M0 4 Q5 -4 15 3 L108 2 Q115 9 109 20 L17 25 Q-5 25 0 4" fill="#eee0c2" stroke="#bca98d" stroke-width="3"/>
      <path d="M17 5 Q40 22 68 10 Q94 22 105 6" fill="none" stroke="#c9b995" stroke-width="1.7"/>
      <path d="M25 6 v16 M82 6 l6 14" stroke="#fff6df" stroke-width="3" opacity=".6"/>
      </g>'''

def desk_background(w,h,portrait=False):
    # Edges vary gently, organic grain, drafting objects cast their own shadows.
    grad='''<defs>
     <linearGradient id="oak" x1="0" y1="0" x2=".8" y2="1"><stop offset="0" stop-color="#b99a75"/><stop offset=".48" stop-color="#9a785b"/><stop offset="1" stop-color="#785843"/></linearGradient>
     <linearGradient id="daylight" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff1c0" stop-opacity=".20"/><stop offset=".65" stop-color="#fef5e4" stop-opacity=".015"/><stop offset="1" stop-color="#172b36" stop-opacity=".12"/></linearGradient>
     <linearGradient id="cup" x1="0" y1="0" x2=".7" y2="1"><stop offset="0" stop-color="#d4f0e9"/><stop offset="1" stop-color="#427d7a"/></linearGradient>
     <filter id="shadow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
     </defs>'''
    s=f'''{grad}<rect width="{w}" height="{h}" fill="url(#oak)"/>
    <rect width="{w}" height="{h}" fill="url(#daylight)"/>'''
    for j in range(18):
      yy=(h*.07+j*h*.059)
      s+=f'<path d="M -30 {yy:.2f} Q {w*.19:.1f} {yy+3+3*math.sin(j*2):.2f} {w*.41:.1f} {yy-1:.2f} T {w+35:.1f} {yy+3:.2f}" stroke="{("#dac3a6" if j%3==0 else "#49382e")}" stroke-width="{1.0+(j%3)*.5}" opacity="{.1+(j%3)*.03}" fill="none"/>'
    for x,y,r in [(w*.06,h*.21,13),(w*.88,h*.83,8),(w*.69,h*.09,6),(w*.37,h*.87,5)]:
      s+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="#4b7d76" opacity=".17"/><circle cx="{x-2:.1f}" cy="{y-2:.1f}" r="{r*.5:.1f}" fill="#d5aa6b" opacity=".25"/>'
    s+=cloth_prop(w,h)
    cupx=w-54 if not portrait else w-48;cupy=45 if not portrait else 130
    s+=f'''<ellipse cx="{cupx+8}" cy="{cupy+12}" rx="40" ry="34" fill="#112e3e" opacity=".17" filter="url(#shadow)"/>
     <circle cx="{cupx}" cy="{cupy}" r="39" fill="#467571" stroke="#21484a" stroke-width="4"/>
     <ellipse cx="{cupx}" cy="{cupy}" rx="29" ry="28" fill="#f5eed9" stroke="#bed3cd" stroke-width="4"/>
     <ellipse cx="{cupx}" cy="{cupy}" rx="22" ry="20" fill="#704e38" stroke="#be9c67" stroke-width="2"/>
     <path d="M {cupx-10} {cupy-6} Q {cupx} {cupy-11} {cupx+9} {cupy-2}" stroke="#d2ab75" stroke-width="2" fill="none" opacity=".6"/>
    '''
    # old paint tools at edge, a distinct workshop not generic infographic chrome
    if not portrait:
      s+='''<g transform="translate(798 439) rotate(-28)"><rect x="-11" y="-110" width="22" height="160" rx="8" fill="#c4a27a" stroke="#263f42" stroke-width="3"/><rect x="-17" y="-132" width="34" height="53" rx="5" fill="#7197a0" stroke="#263f42" stroke-width="3"/><path d="M-13 -117 H14" stroke="#ecded0" stroke-width="4"/><path d="M-10 -84 H11" stroke="#e8d2b9" stroke-width="3"/></g>'''
    else:
      s+='''<g transform="translate(450 838) rotate(-34)"><rect x="-10" y="-105" width="20" height="148" rx="7" fill="#c4a27a" stroke="#263f42" stroke-width="3"/><rect x="-17" y="-129" width="34" height="55" rx="5" fill="#7197a0" stroke="#263f42" stroke-width="3"/><path d="M-10 -110 H12" stroke="#ecded0" stroke-width="4"/></g>'''
    return s

def hand_from_edge(x,y,ang=0,size=1,side='left',grasp=.5):
  # Deliberate 3/4-hand silhouette with connected cuff, fingers and thumbnail.
  # Comes from off-screen as a cropped, coherent forearm, not floating fingertips.
  flip=-1 if side=='right' else 1
  return f'''<g transform="translate({x:.2f} {y:.2f}) rotate({ang:.1f}) scale({flip*size:.3f} {size:.3f})">
    <path d="M -174 -22 Q -118 -28 -77 -18 L -23 -19 L 0 -5 Q 11 9 -3 22 L -65 22 L -170 29 Z" fill="#304f5a" stroke="#213947" stroke-width="3"/>
    <path d="M -172 -17 Q -125 -23 -76 -14" fill="none" stroke="#608391" stroke-width="4" opacity=".7"/>
    <path d="M -31 -18 Q -21 -24 -9 -18 L -7 24 Q -20 28 -30 20 Z" fill="#eee6d2" stroke="#294451" stroke-width="3"/>
    <path d="M -4 -17 Q 14 -26 27 -18 L 49 -8 Q 57 -1 52 8 L 41 13 Q 43 28 31 33 L 9 33 Q -3 30 -6 17 L -11 -1 Z" fill="#be825a" stroke="#513d38" stroke-width="2.4"/>
    <path d="M 12 -11 Q 21 -15 30 -10 L 48 -2 Q 51 2 48 5 L 25 1" fill="none" stroke="#e6b085" stroke-width="3"/>
    <path d="M 14 11 Q 28 13 39 10 M 9 19 Q 25 23 32 19" fill="none" stroke="#8f5e48" stroke-width="1.4" opacity=".8"/>
    <path d="M 31 -9 Q 42 -12 46 -5" stroke="#f2c29a" stroke-width="4" stroke-linecap="round" fill="none" opacity=".7"/>
    </g>'''

def stamp(x,y,theta=0,shadow=True):
    return f'''<g transform="translate({x:.2f} {y:.2f}) rotate({theta:.2f})">
       {'<ellipse rx="49" ry="20" cy="22" fill="#172f36" opacity=".20" filter="url(#shadow)"/>' if shadow else ''}
       <rect x="-68" y="4" width="137" height="19" rx="7" fill="#2f5358" stroke="#173743" stroke-width="3"/>
       <path d="M -40 2 L -33 -14 L 34 -14 L 42 2" fill="#b96d4d" stroke="#5b3d32" stroke-width="3"/>
       <path d="M -16 -15 Q -28 -42 -17 -65 Q 0 -82 17 -66 Q 29 -45 15 -14 Z" fill="#bc8c60" stroke="#58412f" stroke-width="3"/>
       <path d="M-9 -55 Q -6 -67 6 -64" fill="none" stroke="#f0c494" stroke-width="4" opacity=".7"/>
       </g>'''

def stamp_arm(x,stamp_y,view):
    """One connected upper-frame forearm, cuff, palm and curled stamp grip."""
    hand_y=stamp_y-51
    scale=.88 if view=='portrait' else 1.0
    # Body extends all the way past the picture boundary, preventing a floating fist.
    return f'''<g transform="translate({x:.2f} 0) scale({scale})">
      <path d="M -79 -45 Q -60 14 -57 50 Q -55 83 -30 {hand_y-29:.2f} L -6 {hand_y-32:.2f} Q -27 38 -24 -35 Z" fill="#355665" stroke="#24424a" stroke-width="3"/>
      <path d="M -58 -30 Q -44 35 -42 78" fill="none" stroke="#6b8794" stroke-width="5" opacity=".6"/>
      <path d="M-31 {hand_y-43:.1f} Q -18 {hand_y-48:.1f} -7 {hand_y-38:.1f} L -2 {hand_y-20:.1f} L -29 {hand_y-17:.1f} Z" fill="#ebe7d7" stroke="#344f59" stroke-width="2.6"/>
      <path d="M-19 {hand_y-26:.2f} Q -11 {hand_y-40:.2f} 4 {hand_y-35:.2f} Q 18 {hand_y-32:.2f} 21 {hand_y-15:.2f} Q 24 {hand_y+7:.2f} 11 {hand_y+10:.2f} L 2 {hand_y+2:.2f} Q -13 {hand_y+16:.2f} -22 {hand_y+1:.2f} Z" fill="#bd805c" stroke="#604537" stroke-width="2.7"/>
      <path d="M-2 {hand_y-10:.1f} Q 15 {hand_y-12:.1f} 19 {hand_y-7:.1f} M-4 {hand_y-2:.1f} Q 13 {hand_y-3:.1f} 17 {hand_y+1:.1f}" stroke="#815c47" fill="none" stroke-width="1.3"/>
      <path d="M-8 {hand_y-23:.2f} Q 6 {hand_y-30:.2f} 12 {hand_y-19:.2f}" stroke="#e8ac85" stroke-width="2.7" fill="none"/>
      </g>'''

def frame(t,view='landscape'):
    assert view in ('landscape','portrait')
    # t relative to 29.2 sec
    assert 0<=t<=FRAME_COUNT/FPS+1e-7
    port=view=='portrait';w,h=(540,960) if port else (960,540)
    if port:
        ax,ay,aw,ah=(274,315,344,326);bx,by,bw,bh=(278,693,344,326)
    else:
        ax,ay,aw,ah=(322,267,285,340);bx,by,bw,bh=(652,259,285,340)
    # controlled camera drift on the actual desk surface, not on a UI frame.
    camx=2.3*math.sin(t/8*math.pi);camy=1.2*math.sin(t/5*math.pi)
    a_in=sm((t-.23)/1.45);b_in=sm((t-1.68)/1.48)
    aposx=ax+(1-a_in)*(-w*.77);bposx=bx+(1-b_in)*(w*.78)
    aposy=ay+(1-a_in)*(-26);bposy=by+(1-b_in)*(26)
    # subtle settling of papers after a firm hand release
    arot=-4.2 + (1-a_in)*(-8.0) + 1.1*math.sin((t-1.8)*9)*math.exp(-max(0,t-1.8)*4) if t>1.7 else -4.2+(1-a_in)*(-8.0)
    brot=5.1 + (1-b_in)*(9.5) + 1.1*math.sin((t-3.12)*10)*math.exp(-max(0,t-3.12)*4) if t>3.1 else 5.1+(1-b_in)*9.5
    # two stamp strikes on the actual sheets, not captions
    a_ink=sm((t-7.06)/.18);b_ink=sm((t-9.50)/.19)
    hold=1-sm((t-3.6)/1)
    first_hand=sm((t-.12)/.38)*(1-sm((t-1.8)/.55))
    second_hand=sm((t-1.45)/.43)*(1-sm((t-3.36)/.55))
    # painter/writer arm enters with each paper; hand leads a sheet edge
    px1=aposx-aw*.42;py1=aposy+ah*.34
    px2=bposx+bw*.42;py2=bposy+bh*.35
    # lift/press stamp with visible impact and recovery
    active=(t>=5.25 and t<11.0)
    # Raise and travel between papers while holding the same stamp; never teleport.
    travel=sm((t-7.75)/1.33)
    tx=lerp(aposx,bposx,travel)
    ty=lerp(aposy+ah*.065,bposy+bh*.065,travel)
    press1=sm((t-6.65)/.36)*(1-sm((t-7.12)/.44))
    press2=sm((t-9.12)/.33)*(1-sm((t-9.58)/.47))
    press=max(press1,press2)
    sy=ty-53*(1-press)
    head=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    out=[head,desk_background(w,h,port),f'<g transform="translate({camx:.2f} {camy:.2f})">']
    # only objects on real tabletop
    out.append(paper(aposx,aposy,aw,ah,arot,'A',max(.001,a_in),'left',a_ink))
    out.append(paper(bposx,bposy,bw,bh,brot,'B',max(.001,b_in),'right',b_ink))
    if first_hand>.02:
      handx=lerp(px1-140,px1-12,first_hand)
      out.append(f'<g opacity="{first_hand:.2f}">{hand_from_edge(handx,py1+2,ang=-7,size=.84 if port else .9,side="left")}</g>')
    if second_hand>.02:
      handx=lerp(px2+140,px2+17,second_hand)
      out.append(f'<g opacity="{second_hand:.2f}">{hand_from_edge(handx,py2+6,ang=9,size=.83 if port else .9,side="right")}</g>')
    if active:
      # after second stamp hand and stamp lift clear to reveal what the paper says
      visible=sm((t-5.22)/.44)*(1-sm((t-10.17)/.62))
      out.append(f'<g opacity="{visible:.3f}">{stamp(tx,sy,theta=-7)}</g>')
      # hand gripping upper stamp shaft, keeps stamp attached during press
      out.append(f'<g opacity="{visible:.3f}">{stamp_arm(tx+5,sy,view)}</g>')
      # ink compression smoke/dust subtle, only at physical event
      event=max(0,1-abs(t-7.09)/.21)+max(0,1-abs(t-9.55)/.21)
      if event>0:
        out.append(f'<ellipse cx="{tx:.1f}" cy="{ty+20:.1f}" rx="{60+12*event:.2f}" ry="{18+8*event:.2f}" fill="#e7caa3" opacity="{.12*event:.3f}"/>')
    # lower-left pencil cast shadow, frames rather than caption bar
    if not port:
      out.append('''<g transform="translate(78 456) rotate(28)"><rect x="-8" y="-89" width="14" height="175" rx="3" fill="#de9d53" stroke="#614735" stroke-width="2"/><rect x="-8" y="-92" width="14" height="28" fill="#345d60"/><path d="M-8 86 l7 22 l7 -22" fill="#ebd1a1" stroke="#584a3b" stroke-width="2"/></g>''')
    else:
      out.append('''<g transform="translate(92 815) rotate(40)"><rect x="-8" y="-70" width="14" height="153" rx="3" fill="#de9d53" stroke="#614735" stroke-width="2"/><rect x="-8" y="-72" width="14" height="28" fill="#345d60"/><path d="M-8 84 l7 22 l7 -22" fill="#ebd1a1" stroke="#584a3b" stroke-width="2"/></g>''')
    out+=['</g>','</svg>']
    return '\n'.join(out)

if __name__=='__main__':
 import sys
 print(frame(float(sys.argv[1]) if len(sys.argv)>1 else 6.0,sys.argv[2] if len(sys.argv)>2 else 'landscape'))