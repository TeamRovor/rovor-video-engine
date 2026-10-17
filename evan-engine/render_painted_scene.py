"""Opt-in 1920x1080 painted Evan shot renderer, driven by an editable scene JSON.

Production defaults stay unchanged. Requires Pillow, NumPy and OpenCV. Head is
registered painted facial art; body is a continuous three-joint-per-arm mesh.
"""
import argparse,json,math,time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from painted_character import PaintedCharacter,sample_track,smooth
from painted_timing import flowing_track
import numpy as np
import cv2

HERE=Path(__file__).resolve().parent
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def font(size,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)

def wrap(text,width,size):
    words=text.split();rows=[];line=''
    for word in words:
        test=(line+' '+word).strip()
        if ImageDraw.Draw(Image.new('RGB',(1,1))).textlength(test,font=font(size))>width:
            rows.append(line);line=word
        else:line=test
    if line:rows.append(line)
    return rows

def control_state(t,scene):
    tracks=scene.get('performanceTracks',{})
    if not tracks:
        state={'head':0.,'left':np.zeros(3),'right':np.zeros(3)}
        for g in scene.get('gestures',[]):
            start,end=float(g['start']),float(g['end'])
            keys=[(start-.25,0),(start+.18,1),(start+.45,.72),(max(start+.46,end-.12),.5),(max(start+.5,end+.24),0)]
            side='right' if g.get('kind') in ('point','pinch') else 'left'
            sign=-1 if side=='right' else 1
            state[side]+=np.array([sign*flowing_track(t,keys),sign*8*flowing_track(t-.035,keys),sign*2*flowing_track(t-.085,keys)])
            state['head']+=-.7*flowing_track(t-.035,keys)
        # A future zero-valued gesture must not erase the current gesture.
        for side in ('left','right'):state[side]=tuple(np.clip(state[side],[-4,-18,-7],[4,18,7]))
        state['head']=float(np.clip(state['head'],-2,2))
        state['body_roll']=.16*np.sin(t*1.45)+.13*state['head']
        return state
    state={'head':flowing_track(t-.035,tracks.get('head',[(0,0)]))}
    for name in ('left','right'):
        channels=tracks.get(name,{})
        state[name]=tuple(flowing_track(t-delay,channels.get(j,[(0,0)])) for j,delay in [('shoulder',0),('elbow',.035),('wrist',.085)])
    state['body_roll']=.16*np.sin(t*1.45)+.13*state['head']
    return state

class PaintedScene:
    def __init__(self,scene):
        self.scene=scene;self.character=PaintedCharacter()
        self.logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA')
        self.icons={size:self.logo.resize((size,round(size*self.logo.height/self.logo.width)),Image.Resampling.LANCZOS) for size in (32,48,76,120)}
        self.base=Image.new('RGBA',(1920,1080),'#eeeae3')
        d=ImageDraw.Draw(self.base);d.rectangle((1045,0,1920,1080),fill='#f6f3ee')
        d.line((1045,100,1045,980),fill='#ddd9d1',width=2)
        self.base.alpha_composite(self.icons[48],(1110,78))
        d.text((1178,81),'ROVOR DIGITAL',font=font(28,True),fill='#26384a')

    def render(self,t):
        s=self.scene;im=self.base.copy();d=ImageDraw.Draw(im)
        title=s.get('title', 'A small detail.\nA clear identity.' if (s.get('demonstration') or any(p.get('kind')=='favicon' for p in s.get('scenePlan',[]))) else 'A minute with Evan.')
        d.multiline_text((1110,170),title,font=font(49,True),fill='#22364b',spacing=8)
        is_favicon=bool(s.get('demonstration')) or any(p.get('kind')=='favicon' for p in s.get('scenePlan',[]))
        if not is_favicon:
            active=next((p for p in s.get('scenePlan',[]) if p['start']<=t<p['end']),{})
            d.rounded_rectangle((1100,345,1840,785),radius=24,fill='white',outline='#d1d8df',width=2)
            label=active.get('title') or next((r['text'] for r in s.get('segments',[]) if r['start']<=t<r['end']),'')
            for i,line in enumerate(wrap(label,625,36)):
                d.text((1150,410+i*52),line,font=font(36),fill='#344c61')
            return self.presenter(im,t)
        # A single coherent browser prop persists throughout the explanation.
        x,y,w,h=1100,345,740,440
        d.rounded_rectangle((x+4,y+10,x+w+4,y+h+10),radius=22,fill='#e1ddd5')
        d.rounded_rectangle((x,y,x+w,y+h),radius=22,fill='white',outline='#d1d8df',width=2)
        d.rounded_rectangle((x+1,y+1,x+w-1,y+61),radius=21,fill='#e6ebef')
        d.rectangle((x+1,y+35,x+w-1,y+62),fill='#e6ebef')
        for dx,c in [(24,'#c9b2ac'),(45,'#d7c69e'),(66,'#b5c5b2')]:d.ellipse((x+dx,y+22,x+dx+10,y+32),fill=c)
        d.rounded_rectangle((x+100,y+10,x+445,y+61),radius=13,fill='white')
        d.text((x+159,y+25),'Your website',font=font(24),fill='#34465a')
        # Model the actual described globe -> branded favicon event. All times
        # live in the scene; no random topic cards or fabricated customer data.
        beats=s.get('demonstration',{});replace=beats.get('replaceIcon',8.7)
        reveal=float(smooth((t-replace)/.45))
        gx,gy=x+125,y+35
        if reveal<1:
            g=Image.new('RGBA',im.size);q=ImageDraw.Draw(g);col=(114,135,151,round(255*(1-reveal)))
            q.ellipse((gx-13,gy-13,gx+13,gy+13),outline=col,width=2)
            q.ellipse((gx-6,gy-13,gx+6,gy+13),outline=col,width=2);q.line((gx-13,gy,gx+13,gy),fill=col,width=2)
            im.alpha_composite(g)
        if reveal>0:
            icon=self.icons[32].copy();icon.putalpha(icon.getchannel('A').point(lambda a:round(a*reveal)))
            im.alpha_composite(icon,(gx-16,gy-16))
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((x+35,y+91,x+w-35,y+128),radius=10,fill='#f4f6f7')
        d.text((x+57,y+98),'yourwebsite.example',font=font(18),fill='#71808b')
        # Simple webpage composition, not invented business results.
        d.rounded_rectangle((x+35,y+155,x+355,y+381),radius=14,fill='#e9eef0')
        d.text((x+391,y+183),'Your brand.',font=font(29,True),fill='#26384a')
        for dy,length in [(240,225),(268,190),(296,210)]:d.rounded_rectangle((x+392,y+dy,x+392+length,y+dy+10),radius=5,fill='#dce2e6')
        d.rounded_rectangle((x+391,y+339,x+573,y+380),radius=9,fill='#344b61')
        d.text((x+413,y+348),'Explore',font=font(20,True),fill='white')
        # Magnified detail arrives on 'tiny little globe'; inset is connected
        # to the exact tab position rather than a disconnected icon slideshow.
        focus=float(smooth((t-beats.get('focusGlobe',2.1))/.6))
        if focus>0:
            cx,cy=x+196,y+266
            d.line((gx+5,gy+17,cx-55,cy-95),fill='#b48f61',width=3)
            radius=round(83*focus)
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill='#fbfaf7',outline='#b48f61',width=3)
            if focus>.9:
                if reveal<.5:
                    d.ellipse((cx-34,cy-34,cx+34,cy+34),outline='#70899c',width=4)
                    d.ellipse((cx-16,cy-34,cx+16,cy+34),outline='#70899c',width=3)
                    d.line((cx-33,cy,cx+33,cy),fill='#70899c',width=3)
                else:im.alpha_composite(self.icons[76],(cx-38,cy-26))
        if t>replace+.4:
            d=ImageDraw.Draw(im);d.text((1110,823),'A favicon carries your identity into the tab.',font=font(25,True),fill='#344c61')
        return self.presenter(im,t)

    def presenter(self,im,t):
        s=self.scene
        # Authored asymmetric acting and a subtle continuous camera push.
        controls=control_state(t,s);char=self.character.render(t,[] if s.get('mouthMode')=='still' else s.get('mouthCues',[]),controls)
        scale=flowing_track(t,s.get('cameraScale',[(0,.86),(15,.88)]))
        root_x=flowing_track(t,s.get('rootX',[(0,-80)]))
        root_y=flowing_track(t,s.get('rootY',[(0,45)]))
        # Subpixel camera composition avoids integer resize/placement steps and
        # the fine hair/cloth shimmer those steps caused.
        raw=np.asarray(char).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
        matrix=np.array([[scale,0,root_x],[0,scale,root_y]],np.float32)
        warped=cv2.warpAffine(raw,matrix,(1920,1080),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        warped[:,:,:3]=np.clip(warped[:,:,:3]*255/np.maximum(warped[:,:,3:4],1),0,255)
        im.alpha_composite(Image.fromarray(np.clip(warped,0,255).astype('uint8')))
        d=ImageDraw.Draw(im)
        active=next((row for row in s.get('segments',[]) if row['start']<=t<row['end']),None)
        if active:
            for i,row in enumerate(wrap(active['text'],715,27)):
                d.text((1110,903+i*38),row,font=font(27),fill='#52606a')
        return im.convert('RGB')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('frames',type=Path);p.add_argument('start',type=int,nargs='?',default=0);p.add_argument('end',type=int,nargs='?');p.add_argument('--budget',type=float,default=23);p.add_argument('--stills',action='store_true');a=p.parse_args()
    scene=json.loads(a.scene.read_text());fps=scene.get('fps',24);end=a.end or math.ceil(scene['duration']*fps)
    renderer=PaintedScene(scene);a.frames.mkdir(parents=True,exist_ok=True);begin=time.monotonic();i=a.start
    if a.stills:
        for t in [0,.6,2.8,4.2,6.4,8.7,10.5,13.8]:renderer.render(t).save(a.frames/f'still-{t}.png')
    else:
        while i<end and (time.monotonic()-begin<a.budget or i==a.start):
            target=a.frames/f'{i:06}.jpg';tmp=a.frames/f'{i:06}.writing.jpg'
            renderer.render(i/fps).save(tmp,quality=95);tmp.replace(target);i+=1
    print(json.dumps({'nextFrame':i,'totalFrames':end,'complete':i==end,'elapsed_seconds':round(time.monotonic()-begin,3)}))
if __name__=='__main__':main()
