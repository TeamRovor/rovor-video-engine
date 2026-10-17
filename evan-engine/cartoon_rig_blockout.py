"""Editable SVG engineering blockout for cartoon Evan (NOT approved character art).

The flattened design sheet is *not* cropped into faux parts. Every visible joint,
oral component and facial expression here is a separate registered vector group.
Use the official Rovor PNG if accessible in the repo checkout; text fallback is
explicitly a placeholder, not a substitute for a verified logo.

Optional speech-plan JSON consumes the same six continuous controls used by the
existing English articulation pipeline. Without one, the scene uses synthetic,
NON-NARRATION mouth motion only for a rig demonstration.
"""
from __future__ import annotations
import argparse
import base64
from dataclasses import dataclass
from cartoon_hand_deform import isolated_pose, render_hand
from cartoon_mouth_surfaces import mouth_svg
from cartoon_secondary_motion import secondary_at
import json
import math
from pathlib import Path

CONTROLS = ('jawOpen', 'lipSeal', 'lipRound', 'lipSpread', 'lowerLipContact', 'tongueVisible')
SIZE = (1280, 720)
BRAND_PATH=Path(__file__).resolve().parent.parent/'evan-character/brand/rovor-mark-black.png'
SKIN='#D69B73'; SKIN_SHADE='#BC7859'; HAIR='#20232B'; INK='#26303D'; SHIRT='#243F64'; SHIRT_SHADOW='#142C4B'; TIE='#101820'


def clamp(value, lo=0, hi=1):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Nonfinite rig control')
    return max(lo,min(hi,value))


def smooth(u):
    u=clamp(u)
    return u*u*(3-2*u)


def keyed(time, stops):
    """Cubic ease between held animation poses; keyed anticipation and settle."""
    if time<=stops[0][0]:return stops[0][1]
    if time>=stops[-1][0]:return stops[-1][1]
    for (a,v),(b,w) in zip(stops,stops[1:]):
        if a<=time<=b:
            u=smooth((time-a)/(b-a))
            return v*(1-u)+w*u
    raise AssertionError('Unreachable animation interval')


@dataclass
class State:
    jawOpen:float=.04
    lipSeal:float=0.
    lipRound:float=0.
    lipSpread:float=.15
    lowerLipContact:float=0.
    tongueVisible:float=0.
    headTilt:float=0.
    headNod:float=0.
    bodyLean:float=0.
    browL:float=0.
    browR:float=0.
    shoulderL:float=25.
    shoulderR:float=-25.
    elbowL:float=0.
    elbowR:float=0.
    wristL:float=0.
    wristR:float=0.
    handL:str='relaxed'
    handR:str='relaxed'
    smile:float=.2


def controls_at(t,plan):
    if plan is None:
        # Synthetic mouth targets for engineering review, not speech alignment.
        samples=[(0, (.04,0,0,.15,0,0)),(.30,(.60,0,.3,.2,0,0)),
                 (.49,(0,1,0,0,0,0)),(.64,(.85,0,.15,.5,0,0)),
                 (1.10,(.2,0,.05,.3,1,0)),(1.52,(.50,0,.1,.35,0,1)),
                 (1.80,(.08,0,0,.15,0,0)),(2.62,(.78,0,.85,0,0,0)),
                 (3.11,(.68,0,.2,.45,0,0)),(3.75,(.04,0,0,.15,0,0))]
        return dict(zip(CONTROLS,[keyed(t,[(when,v[i]) for when,v in samples]) for i in range(6)]))
    frames=plan.get('controls')
    if not frames:raise ValueError('Speech plan has no continuous controls. Run finalize_plan first')
    times=[float(f['time']) for f in frames]
    if times != sorted(times):raise ValueError('Speech control sample times must be monotone')
    import bisect
    k=bisect.bisect_left(times,t)
    if k<=0: return {c:clamp(frames[0][c]) for c in CONTROLS}
    if k>=len(frames):return {c:clamp(frames[-1][c]) for c in CONTROLS}
    a,b=frames[k-1],frames[k];span=b['time']-a['time']
    if span<=0:raise ValueError('Repeated speech sample timestamp')
    mix=clamp((t-a['time'])/span)
    return {c:clamp(a[c]*(1-mix)+b[c]*mix) for c in CONTROLS}


def state_at(t,plan=None,direction=None):
    c=controls_at(t,plan)
    s=State(**c)
    s.bodyLean=keyed(t,[(0,-2),(.5,-2),(.7,3),(1.25,6),(1.5,4),(2,0),(2.6,-2),(3.1,1),(3.7,-1),(4.1,-1)])
    s.headTilt=keyed(t,[(0,1),(.43,1),(.6,-5),(1.1,-5),(1.5,3),(1.9,3),(2.48,0),(2.71,8),(3.06,3),(3.7,0)])
    s.headNod=keyed(t,[(0,0),(.5,0),(.68,5),(.95,2),(1.3,-1),(1.65,3),(2.1,0),(2.6,-6),(3.1,4),(3.7,0)])
    s.shoulderL=keyed(t,[(0,25),(.68,25),(1.1,92),(1.5,105),(2.2,18),(3.7,25)])
    s.shoulderR=keyed(t,[(0,-25),(.42,-25),(.7,-123),(1.2,-95),(1.45,-25),(2.36,-25),(2.64,-130),(3.05,-114),(3.7,-25)])
    s.elbowL=keyed(t,[(0,0),(.68,0),(1.1,78),(1.5,95),(2.2,-8),(3.7,0)])
    s.elbowR=keyed(t,[(0,0),(.42,0),(.7,65),(1.2,85),(1.45,0),(2.36,0),(2.64,68),(3.05,78),(3.7,0)])
    s.wristL=keyed(t,[(0,0),(1,-5),(1.4,16),(2.2,0),(3.7,0)])
    s.wristR=keyed(t,[(0,0),(.68,-20),(1.15,-5),(1.45,0),(2.64,-12),(3.1,-18),(3.7,0)])
    s.handR='open' if .58<=t<1.35 else 'point' if 2.48<=t<3.38 else 'relaxed'
    s.handL='explain' if .93<=t<1.88 else 'relaxed'
    s.browL=keyed(t,[(0,0),(.55,0),(.69,-7),(1.13,-7),(1.42,1),(2.6,-10),(2.95,-10),(3.5,0)])
    s.browR=keyed(t,[(0,0),(.55,0),(.69,-2),(1.13,-2),(1.42,4),(2.6,-10),(2.95,-10),(3.5,0)])
    s.smile=keyed(t,[(0,.18),(.55,.18),(1.1,.7),(1.5,.5),(2,0),(2.6,-.18),(3,.4),(3.7,.2)])
    if direction is not None:
        from studio_performance import direction_pose
        for channel,value in direction_pose(t,direction).items():
            setattr(s,channel,value)
    return s


def capsule(length,radius,fill,stroke=INK):
    return (f'<path d="M {-radius},0 L {-radius},{length} Q {-radius},{length+radius} 0,{length+radius} '
            f'Q {radius},{length+radius} {radius},{length} L {radius},0 Q {radius},{-radius} 0,{-radius} '
            f'Q {-radius},{-radius} {-radius},0 Z" fill="{fill}" stroke="{stroke}" stroke-width="5"/>')


def hand_svg(style):
    """Shared registered source construction."""
    return isolated_pose(style,SKIN,INK)


def hand_exposures(side,t,direction=None):
    """Cross-dissolve pose drawings in a shared wrist coordinate system."""
    if direction is not None:
        from studio_performance import directed_hand_exposures
        return directed_hand_exposures(side,t,direction)
    timeline = ([(0,'relaxed'),(.58,'open'),(1.35,'relaxed'),(2.48,'point'),(3.38,'relaxed')]
                if side == 'R' else
                [(0,'relaxed'),(.93,'explain'),(1.88,'relaxed')])
    previous=timeline[0][1]
    for when,new in timeline[1:]:
        # 120 ms registration-safe overlap around the named pose change.
        if when-.06 <= t < when+.06:
            weight=smooth((t-(when-.06))/.12)
            return [(previous,1-weight),(new,weight)]
        if t < when-.06:break
        previous=new
    return [(previous,1.)]



def arm_svg(side,s,t,direction=None):
    sign=-1 if side=='L' else 1
    shoulder=s.shoulderL if side=='L' else s.shoulderR
    elbow=s.elbowL if side=='L' else s.elbowR
    wrist=s.wristL if side=='L' else s.wristR
    hand=s.handL if side=='L' else s.handR
    # Local +y bones; the hierarchy rotates around physically independent joints.
    layers=hand_exposures(side,t,direction)
    hand_markup=render_hand(layers,SKIN,INK,prefix=f'hand-{side}-')
    return (f'<g id="arm-{side}" data-layer="arm-{side}" transform="translate({108*sign},-4) rotate({shoulder})">'
            f'<g id="upper-arm-{side}" data-layer="upper-arm-{side}">{capsule(103,30,SHIRT)}</g>'
            f'<g id="elbow-{side}" transform="translate(0,103) rotate({elbow})">'
            f'<circle r="24" fill="{SHIRT_SHADOW}" stroke="{INK}" stroke-width="5" />'
            f'<g id="forearm-{side}" data-layer="forearm-{side}">{capsule(91,24,SHIRT)}</g>'
            f'<g id="wrist-{side}" transform="translate(0,91) rotate({wrist})">'
            f'<g id="hand-{side}" data-layer="hand-{side}" data-hand-pose="{hand}">{hand_markup}</g>'
            '</g></g></g>')


def face_svg(s,secondary=None):
    """Independent jaw, oral cavity, lip boundaries, teeth, tongue and brows."""
    opening=clamp(s.jawOpen)*(1-clamp(s.lipSeal))
    jaw_dy=13*opening
    hairTilt=secondary.hairTilt if secondary is not None else 0.
    hairShift=secondary.hairShift if secondary is not None else 0.
    return (
        f'<g id="head" data-layer="head" transform="translate(0,{-118+s.headNod:.2f}) rotate({s.headTilt:.2f})">'
        # Hair understructure and stable upper face.
        f'<g id="hair-back" data-layer="hair-back"><path d="M -103,-60 Q -125,-118 -73,-159 '
        f'Q -45,-192 0,-165 Q 40,-189 86,-150 Q 122,-117 99,-55 L 90,24 L -88,24 Z" '
        f'fill="{HAIR}" stroke="{INK}" stroke-width="6" /></g>'
        f'<g id="upper-face" data-layer="upper-face"><path d="M -95,-78 Q -90,-142 0,-139 '
        f'Q 89,-142 95,-78 L 92,23 Q 80,66 0,68 Q -84,66 -94,23 Z" '
        f'fill="{SKIN}" stroke="{INK}" stroke-width="6" />'
        f'<path d="M -94,-23 Q -116,-35 -111,-7 Q -109,14 -91,13 M 94,-23 '
        f'Q 116,-35 111,-7 Q 109,14 91,13" fill="{SKIN}" stroke="{INK}" stroke-width="5"/></g>'
        f'<g id="jaw" data-layer="jaw" transform="translate(0,{jaw_dy:.2f})">'
        f'<path d="M -84,13 Q -96,69 -46,99 Q 0,123 46,99 Q 96,69 84,13 '
        f'L 73,-3 Q 0,6 -73,-3 Z" fill="{SKIN}" stroke="none" />'
        f'<path d="M -84,19 Q -88,76 -46,99 Q 0,123 46,99 Q 88,76 84,19" '
        f'fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round" />'
        f'{mouth_svg(s)}'
        '</g>'
        # Nose, stable sunglasses and independent eyebrow expression.
        f'<g id="nose" data-layer="nose"><path d="M -5,-7 Q -8,7 6,10" fill="none" stroke="{SKIN_SHADE}" stroke-width="4"/></g>'
        f'<g id="brow-left" data-layer="brow-left" transform="translate(0,{s.browL:.2f})">'
        f'<path d="M -78,-77 Q -50,-95 -18,-76" stroke="{HAIR}" stroke-width="8" fill="none"/></g>'
        f'<g id="brow-right" data-layer="brow-right" transform="translate(0,{s.browR:.2f})">'
        f'<path d="M 18,-76 Q 50,-95 78,-77" stroke="{HAIR}" stroke-width="8" fill="none"/></g>'
        f'<g id="glasses" data-layer="glasses"><path d="M -85,-64 Q -45,-76 -10,-59 L -6,-38 '
        f'Q -40,-13 -79,-35 Z M 10,-59 Q 45,-76 85,-64 L 79,-35 Q 40,-13 6,-38 Z" '
        f'fill="#111A27" stroke="{INK}" stroke-width="6" />'
        f'<path d="M -10,-57 Q 0,-65 10,-57" stroke="{INK}" stroke-width="7" fill="none" /></g>'
        f'<g id="hair-front" data-layer="hair-front" '
        f'transform="translate(0,-118) rotate({hairTilt:.3f}) translate({hairShift:.3f},118)"><path d="M -95,-93 ' 
        f'Q -120,-131 -72,-155 Q -74,-175 -37,-162 Q -18,-189 8,-168 '
        f'Q 38,-193 54,-166 Q 87,-175 96,-137 Q 111,-125 95,-85 '
        f'Q 82,-111 67,-119 Q 48,-100 29,-119 Q -6,-100 -22,-120 '
        f'Q -63,-97 -95,-93 Z" fill="{HAIR}" stroke="{INK}" stroke-width="6"/></g>'
        '</g>')


def official_brand_markup(path):
    if path and Path(path).is_file():
        raw=Path(path).read_bytes()
        suffix=Path(path).suffix.lower()
        mime={'png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}.get(suffix.lstrip('.'))
        if not mime:raise ValueError('Use a standard raster Rovor mark')
        uri=f'data:{mime};base64,{base64.b64encode(raw).decode("ascii")}'
        return f'<image id="official-rovor-mark" href="{uri}" x="1038" y="34" width="120" height="120" preserveAspectRatio="xMidYMid meet"/>',True
    # Fallback marked as placeholder in the SVG metadata and on-screen.
    return ('<g id="unverified-text-brand-placeholder"><text x="997" y="96" font-family="sans-serif" '
            'font-size="44" font-weight="900" fill="#243F64">ROVOR</text>'
            '<text x="999" y="119" font-family="sans-serif" font-size="15" letter-spacing="5" '
            'fill="#243F64">DIGITAL</text></g>'),False


def frame_svg(t,plan=None,brand=None,direction=None):
    if t<0:raise ValueError('Negative scene time')
    s=state_at(t,plan,direction)
    secondary=secondary_at(t,lambda at:state_at(at,plan,direction))
    if brand is None and BRAND_PATH.exists():brand=BRAND_PATH
    mark,verified=official_brand_markup(brand)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
      width="1280" height="720" viewBox="0 0 1280 720" data-art-status="engineering-blockout"
      data-official-brand={json.dumps(str(verified).lower())} data-performance-status="{'editorial-beat-blockout' if direction else 'synthetic-timeline'}" data-speech-status="{'speech-plan-controls' if plan else 'synthetic-test-only'}">
      <metadata>Cartoon Evan joint/face engineering blockout. Not approved source art or completed animation.</metadata>
      <rect id="background" width="1280" height="720" fill="#F3F3ED" />
      <path d="M 0,598 Q 600,553 1280,610 L 1280,720 L 0,720 Z" fill="#DCE5E5"/>
      {mark}
      <text x="750" y="232" font-family="sans-serif" font-size="23" fill="#54717C">NEW GROUND FOR YOUR BUSINESS</text>
      <text x="750" y="296" font-family="sans-serif" font-weight="bold" font-size="43" fill="#223E5D">BEYOND THE ORDINARY</text>
      <text x="752" y="336" font-family="sans-serif" font-size="21" fill="#42596A">Expressive character rig motion study</text>
      <g id="character" data-layer="character" transform="translate(391,382) rotate({s.bodyLean:.2f})">
         <ellipse id="cast-shadow" cx="0" cy="267" rx="166" ry="19" fill="#768E9B" opacity=".27" />
         <g id="neck" data-layer="neck"><path d="M -45,-82 L -45,6 Q 0,37 45,6 L 45,-82" fill="{SKIN_SHADE}" stroke="{INK}" stroke-width="6"/></g>
         {arm_svg('L',s,t,direction)}{arm_svg('R',s,t,direction)}
         <g id="torso" data-layer="torso"><path d="M -103,-22 Q -145,5 -127,92 L -108,231
           Q 0,252 108,231 L 127,92 Q 145,5 103,-22 L 45,-41 Q 0,4 -45,-41 Z"
           fill="{SHIRT}" stroke="{INK}" stroke-width="7" />
           <path d="M -45,-41 L 0,3 L 45,-41 L 29,18 L 0,40 L -29,18 Z" fill="#E7EEF2" stroke="{INK}" stroke-width="5" />
           <g id="tie-secondary" data-layer="tie-secondary"
              transform="translate(0,16) rotate({secondary.tieTilt:.3f}) translate(0,{-16-secondary.tieLift:.3f})">
           <path d="M 0,7 L -16,28 L 0,45 L 17,28 Z M 0,45 L -17,160 L 0,187 L 17,160 Z"
           fill="{TIE}" stroke="{INK}" stroke-width="4" /></g>
           <path d="M -99,72 Q -83,168 -97,225 M 99,72 Q 83,168 97,225" fill="none"
           stroke="{SHIRT_SHADOW}" stroke-width="5" opacity=".8"/></g>
         {face_svg(s,secondary)}
      </g>
      <g id="review-watermark" opacity=".85"><text x="42" y="688" fill="#62727A" font-family="sans-serif" font-size="14">
      ENGINEERING BLOCKOUT — not approved source art, studio animation or lip-sync validation
      </text></g>
      {'<text x="1005" y="142" font-family="sans-serif" font-size="10" fill="#7C888E">brand placeholder</text>' if not verified else ''}
    </svg>'''


def render_demo(output,plan=None,brand=None,frames=96,fps=24,direction=None):
    """Save SVG frames and normal/half-speed films. No Moho involvement."""
    if fps<1 or frames<1:raise ValueError('fps and frames must be positive')
    if brand is None and BRAND_PATH.exists():brand=BRAND_PATH
    try:
        import cairosvg
    except ImportError as e:
        raise RuntimeError('Install cairosvg for PNG rendering') from e
    import subprocess
    output=Path(output); png=output/'frames';svg=output/'editable-svg';png.mkdir(parents=True,exist_ok=True);svg.mkdir(parents=True,exist_ok=True)
    # Keep original SVG per frame; each independently articulated component remains editable.
    for i in range(frames):
        xml=frame_svg(i/fps,plan,brand,direction)
        (svg/f'{i:04}.svg').write_text(xml,encoding='utf-8')
        cairosvg.svg2png(bytestring=xml.encode('utf-8'),write_to=str(png/f'{i:04}.png'))
    normal=output/'cartoon-blockout-normal.mp4';slow=output/'cartoon-blockout-half-speed.mp4'
    for path,ratio in ((normal,'1'),(slow,'2')):
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(fps),'-i',str(png/'%04d.png'),'-vf',f'setpts={ratio}*PTS','-an','-c:v','libx264','-pix_fmt','yuv420p','-crf','20','-movflags','+faststart',str(path)]
        subprocess.run(cmd,check=True)
    manifest={'sourceType':'independent SVG component blockout','animationReady':False,'brandAssetVerified':bool(brand and Path(brand).is_file()),
              'speechSource':'existing continuous control samples' if plan else 'synthetic motion fixture, no narration',
               'performanceSource':'editorial-authored beats, construction blockout' if direction else 'legacy synthetic timed poses',
              'components':['neck','torso','head','jaw','oral-interior','upper-teeth','tongue','upper-lip','lower-lip','glasses','brow-left','brow-right','upper-arm-L','forearm-L','hand-L','upper-arm-R','forearm-R','hand-R'],
              'handPoses':['relaxed','open','point','explain','fist'],'frames':frames,'fps':fps,
              'limitations':['Construction artwork is not matched to design-sheet-v1.png','No native Moho rig','No actual narration audio used unless the plan is supplied','No visual quality approval']}
    (output/'blockout-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--speech-plan',type=Path)
    p.add_argument('--brand',type=Path);p.add_argument('--direction',type=Path,help='Editorial acting-beat JSON, independent of speech plan');p.add_argument('--fps',type=int,default=24);p.add_argument('--frames',type=int,default=96)
    a=p.parse_args()
    plan=json.loads(a.speech_plan.read_text()) if a.speech_plan else None
    direction=json.loads(a.direction.read_text()) if a.direction else None
    print(json.dumps(render_demo(a.output,plan,a.brand,a.frames,a.fps,direction),indent=2))