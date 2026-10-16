"""Opt-in source-art performance study. Never used by the approved renderer.
Requires Pillow and NumPy. Rebuildable layered PNG/SVG rig and review frames.
Shoulder overlaps and reconstructed lip skin REQUIRE artist review.
"""
import argparse, json, math, time
from pathlib import Path
import numpy as np
from build_layered_character import split_pose, POSES
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT=Path(__file__).resolve().parent.parent
S=2 # Work at 2x the 408px source. This is supersampling, not new detail.
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def ease(x):
    x=max(0,min(1,x)); return x*x*(3-2*x)

def track(t,keys):
    if t<=keys[0][0]: return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b: return x+(y-x)*ease((t-a)/(b-a))
    return keys[-1][1]

# Semantic control values: width, aperture, rounding; shared path topology.
SHAPES={'X':(1,0,0),'A':(.94,0,0),'B':(1.05,.14,0),
        'C':(1,.42,0),'D':(.92,.82,0),'E':(.66,.60,1),
        'F':(.51,.32,1),'G':(.94,.08,0),'H':(1,.29,0)}

def speech(t,cues):
    """60ms transitions, bounded by half the current exposure.
    A closure receives its complete target at cue start, never averaged away.
    """
    for i,c in enumerate(cues):
        if c['start']<=t<c['end']:
            v=SHAPES[c['value']]
            prev=SHAPES[cues[i-1]['value']] if i else SHAPES['X']
            blend=ease((t-c['start'])/min(.06,(c['end']-c['start'])/2))
            if c['value']=='A': blend=1
            return tuple(a+(b-a)*blend for a,b in zip(prev,v))
    return SHAPES['X']

def masked(src,poly):
    mask=Image.new('L',src.size); ImageDraw.Draw(mask).polygon(poly,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(.6)); out=src.copy()
    out.putalpha(Image.fromarray((np.asarray(src.getchannel('A'),dtype=float)*np.asarray(mask)/255).astype('uint8')))
    return out

def rig(out):
    src=Image.open(ROOT/'evan-character/v3-assets/present.png').convert('RGBA')
    # The original sheets offer no clean torso underneath these sleeves.
    # Source-texture overlaps allow only a restrained shoulder range.
    left=[(1,263),(50,253),(93,306),(97,346),(165,372),(168,426),(102,457),(0,467)]
    right=[(292,269),(320,275),(332,321),(355,287),(407,282),(408,454),(317,474),(274,420)]
    torso,head=split_pose(src,POSES['present'])
    # Remove source motion marks, which would otherwise move as facial artwork.
    hd=ImageDraw.Draw(head); hd.rectangle((270,178,315,217),fill=(0,0,0,0))
    # Clean mouth bed by interpolating sampled skin above/below the source lips.
    # Limited local reconstruction; artist replacement is mandatory for final.
    a=np.array(head); yy,xx=np.mgrid[:src.height,:src.width]
    u=(xx-228)*.94+(yy-155)*.342; v=-(xx-228)*.342+(yy-155)*.94
    # Harmonic fill follows surrounding skin tones instead of a flat skin sticker.
    region=(abs(u)<28)&(abs(v)<14)&((u/28)**2+(v/14)**2<1)
    rgb=a[:,:,:3].astype(float)
    rgb[region]=[252,174,118]
    for _ in range(700):
        avg=(np.roll(rgb,1,0)+np.roll(rgb,-1,0)+np.roll(rgb,1,1)+np.roll(rgb,-1,1))/4
        rgb[region]=avg[region]
    a[:,:,:3]=rgb.astype('uint8')
    a[region,3]=255
    head=Image.fromarray(a)
    # Retain source neck behind the separate head. Hide arms with torso masks,
    # rather than leaving duplicate stationary hands under animated hands.
    alpha=np.asarray(torso.getchannel('A')).copy()
    cuts=Image.new('L',src.size)
    for poly in [left,right]: ImageDraw.Draw(cuts).polygon(poly,fill=255)
    # Erode the removal masks to leave source-texture overlaps at cut boundaries.
    cuts=cuts.filter(ImageFilter.MinFilter(15))
    alpha[np.asarray(cuts)>0]=0
    torso.putalpha(Image.fromarray(alpha))
    layers={'torso':torso,'head':head,
            'arm_left':masked(src,left),'arm_right':masked(src,right)}
    out.mkdir(parents=True,exist_ok=True)
    for name,im in layers.items(): im.save(out/(name+'.png'))
    manifest={'status':'experimental, requires artist cleanup','source':'v3-assets/present.png',
      'source_dimensions':list(src.size),'pivots':{'head':[224,224],'arm_left':[62,278],'arm_right':[294,290]},
      'limitations':['Flattened source; narrow source overlaps, no hidden shoulder drawings','No independent elbow or wrist art',
       'Jaw warp approximates volume; no head turn','Sunglasses conceal eyes; brows need redrawing','No native Moho project verified']}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
    # Export nine editable, same-topology mouth vector shapes for artist revision.
    for key,value in SHAPES.items(): (out/('mouth_'+key+'.svg')).write_text(mouth_svg(*value))
    return layers

def mouth_svg(width,opening,rounding):
    w=22*width; h=1+15*opening
    # Three cubic segments, equal topology for all shapes. Interior is clipped.
    path=f'M {-w},0 C {-w*.6},{-h*.5} {w*(.5-.2*rounding)},{-h*.6} {w},0 C {w*.8},{h*.8} {w*.45},{h} 0,{h} C {-w*.4},{h} {-w*.8},{h*.6} {-w},0 Z'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="110" viewBox="-40 -35 80 55"><defs><clipPath id="m"><path d="{path}"/></clipPath></defs><path d="{path}" fill="#421f20" stroke="#793b2d" stroke-width="1.5"/><g opacity="{1-rounding}" clip-path="url(#m)"><path d="M -24,-5 Q 0,4 24,-4 L 24,3 Q 0,7 -24,2 Z" fill="#fff2dd"/><ellipse cx="0" cy="{h+2}" rx="13" ry="6" fill="#ad5351"/></g></svg>'

def curve(points,n=14):
    a,b,c,d=points
    return [tuple((1-t)**3*a[j]+3*(1-t)**2*t*b[j]+3*(1-t)*t*t*c[j]+t**3*d[j] for j in (0,1)) for t in np.linspace(0,1,n)]

def lips(w,o,r):
    # Compatible contour matches exported editable SVG topology.
    im=Image.new('RGBA',(160*S,110*S)); d=ImageDraw.Draw(im)
    width=22*w; h=1+15*o
    pts=curve([(-width,0),(-width*.6,-h*.5),(width*(.5-.2*r),-h*.6),(width,0)])
    pts+=curve([(width,0),(width*.8,h*.8),(width*.45,h),(0,h)])
    pts+=curve([(0,h),(-width*.4,h),(-width*.8,h*.6),(-width,0)])
    xy=[((x+80)*S,(y+45)*S) for x,y in pts]
    d.polygon(xy,fill='#421f20'); d.line(xy+[xy[0]],fill='#793b2d',width=3)
    mask=Image.new('L',im.size); ImageDraw.Draw(mask).polygon(xy,fill=255)
    inside=Image.new('RGBA',im.size); q=ImageDraw.Draw(inside)
    if o>.07 and r<.5:
        tooth=curve([(-24,-1),(-8,4),(10,5),(24,0)])+curve([(24,0),(12,8),(-10,6),(-24,2)])
        q.polygon([((x+80)*S,(y+45)*S) for x,y in tooth],fill='#fff2dd')
        q.ellipse(((80-13)*S,(45+h-4)*S,(80+13)*S,(45+h+8)*S),fill='#ad5351')
    inside.putalpha(Image.fromarray(np.minimum(np.asarray(inside.getchannel('A')),np.asarray(mask))))
    im.alpha_composite(inside)
    return im.rotate(-20,resample=Image.Resampling.BICUBIC,center=(80*S,45*S))

def character(layers,t,cues):
    w,o,r=speech(t,cues)
    head=layers['head'].resize((408*S,524*S),Image.Resampling.LANCZOS)
    # Jaw skin and beard displace together; top of skull stays fixed.
    jaw=5*o
    mesh=[]
    for y in range(0,524*S,12):
        y2=min(y+12,524*S); y0=y/S; y1=y2/S
        f=lambda z: z*S-jaw*S*max(0,min(1,(z-157)/31))*max(0,min(1,(228-z)/31))
        mesh.append(((0,y,408*S,y2),(0,f(y0),0,f(y1),408*S,f(y1),408*S,f(y0))))
    head=head.transform(head.size,Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)
    m=lips(w,o,r); head.alpha_composite(m,(round((228-80)*S),round((155-45)*S)))
    tilt=track(t,[(0,0),(.5,-1.6),(1.2,.7),(2.2,0),(3.0,-2.2),(3.5,1.2),(4.5,0),(5.4,-1),(6.2,0)])
    head=head.rotate(tilt,Image.Resampling.BICUBIC,center=(224*S,224*S))
    out=layers['torso'].resize(head.size,Image.Resampling.LANCZOS)
    # Authored anticipation, statement accent, overshoot, settle. No idle sine bob.
    for name,pivot,sign in [('arm_left',(62,278),1),('arm_right',(294,290),-1)]:
        angle=track(t,[(0,0),(.5,-2),(1.1,6),(1.35,4),(2.3,0),(2.8,-2),(3.4,7),(3.65,5),(4.5,0),(5.3,3),(6.2,0)])*sign*.45
        arm=layers[name].resize(head.size,Image.Resampling.LANCZOS)
        out.alpha_composite(arm.rotate(angle,Image.Resampling.BICUBIC,center=(pivot[0]*S,pivot[1]*S)))
    out.alpha_composite(head)
    return out

def render(layers,t,cues,baseline=None):
    im=Image.new('RGB',(1080,1920),'#eeeae3'); d=ImageDraw.Draw(im)
    d.text((126,62),'ROVOR DIGITAL',font=ImageFont.truetype(BOLD,28),fill='#23374d')
    logo=Image.open(ROOT/'evan-character/brand/rovor-mark-black.png').convert('RGBA'); logo.thumbnail((60,60)); im.paste(logo,(58,48),logo)
    d.text((60,137),('PERFORMANCE STUDY / DEVELOPMENT' if baseline is None else baseline.upper()+' / CONTROLLED PRESENT-POSE BASELINE'),font=ImageFont.truetype(FONT,22),fill='#6d7177')
    d.rounded_rectangle((60,220,1020,650),radius=26,fill='#fffdfa')
    d.text((100,254),'A small mark. A clear identity.',font=ImageFont.truetype(BOLD,37),fill='#23374d')
    # Narration-aligned demonstration: unmarked tab -> marked tab -> connection.
    for i,label in enumerate(['Your website','ROVOR']):
        x=110+i*435; d.rounded_rectangle((x,345,x+390,555),radius=16,fill='#e1e6eb')
        d.rounded_rectangle((x+12,360,x+310,409),radius=10,fill='white')
        d.text((x+62,373),label,font=ImageFont.truetype(FONT,20),fill='#23374d')
        if i==0 and t<2.4: d.ellipse((x+23,374,x+43,394),fill='#a1a8af')
        else:
            a=ease((t-(2.4 if i==0 else 0))/.35)
            icon=logo.resize((28,28)); icon.putalpha(icon.getchannel('A').point(lambda p:int(p*a)))
            im.paste(icon,(x+20,369),icon)
    if t>3.2:
        a=ease((t-3.2)/.7); d.line((500,473,500+int(35*a),473),fill='#bc8d53',width=7)
    if baseline:
        shape=next((c['value'] for c in cues if c['start']<=t<c['end']),'X')
        names={'X':'rest','A':'MBP','B':'AE','C':'L','D':'open','E':'O','F':'O','G':'FV','H':'UW'} if baseline=='v3' else {'X':'rest','A':'rest','B':'AE','C':'rest','D':'open','E':'open','F':'open','G':'rest','H':'rest'}
        # Frozen V3 mapping and V4 default subtle mapping. Compare releases,
        # not the corrected draft mapping, under matched pose/camera/scene.
        char=Image.open(ROOT/('evan-character/'+baseline+'-assets/present_'+names[shape]+'.png')).convert('RGBA')
        char=char.resize((1000,1284),Image.Resampling.LANCZOS)
    else: char=character(layers,t,cues)
    char=char.resize((1000,1284),Image.Resampling.LANCZOS)
    im.paste(char,(35,650),char)
    text='A small mark helps people recognize your website.' if t<3.1 else 'Keep that identity consistent, wherever they find you.'
    d.rounded_rectangle((60,1740,1020,1860),radius=20,fill='#23374d')
    words=text.split(); line=''; lines=[]
    for word in words:
        if len(line+' '+word)>45: lines.append(line); line=word
        else: line=(line+' '+word).strip()
    lines.append(line)
    for i,line in enumerate(lines): d.text((95,1762+39*i),line,font=ImageFont.truetype(BOLD,30),fill='white')
    return im

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True); p.add_argument('--cues',type=Path,required=True); p.add_argument('--duration',type=float,default=7); p.add_argument('--frames',action='store_true'); p.add_argument('--baseline',choices=['v3','v4']); a=p.parse_args()
    data=json.loads(a.cues.read_text()); cues=data['mouthCues'];
    if not cues or max(c['end'] for c in cues)<=0: raise ValueError('Empty speech cues; check narration audio')
    layers=rig(a.output/'rig'); begin=time.monotonic()
    if a.frames:
        (a.output/'frames').mkdir(exist_ok=True)
        for i in range(math.ceil(a.duration*24)): render(layers,i/24,cues,a.baseline).save(a.output/'frames'/f'{i:06}.jpg',quality=95)
    else:
        for t in [.5,1.2,2.8,3.4,4.2,5.5]: render(layers,t,cues,a.baseline).save(a.output/f'frame-{t}.png')
    print(json.dumps({'elapsed_seconds':round(time.monotonic()-begin,2),'duration':a.duration,'size':[1080,1920],'fps':24}))
