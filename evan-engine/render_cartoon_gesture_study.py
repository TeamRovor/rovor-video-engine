"""Pointing-hand narration study; optional, with unresolved shoulder seams."""
import argparse,json,math
import cv2
from pathlib import Path
from PIL import Image,ImageDraw
from cartoon_gesture_body import CartoonGestureBody as CartoonBody
from render_cartoon_head_study import font,HERE

def frame(body,plan,t):
    im=Image.new('RGBA',(1280,720),'#f3eee2');d=ImageDraw.Draw(im)
    d.ellipse((-200,570,650,850),fill='#d9e3dc')
    figure=body.render(t,plan);figure=figure.resize((849,891),Image.Resampling.LANCZOS);im.alpha_composite(figure,(-120,30))
    logo=Image.open(HERE.parent/'evan-character/brand/rovor-mark-black.png').convert('RGBA');logo.thumbnail((52,52));im.alpha_composite(logo,(684,50));d.text((755,62),'ROVOR DIGITAL',font=font(25),fill='#233442')
    d.text((685,158),'Small detail.',font=font(43),fill='#233442');d.text((685,210),'Visible difference.',font=font(43),fill='#233442')
    d.rounded_rectangle((685,350,1195,568),radius=20,fill='#ffffff',outline='#bdc8c6',width=2)
    d.rounded_rectangle((685,350,1195,406),radius=20,fill='#dce6e2');d.rectangle((687,384,1193,406),fill='#dce6e2')
    for x in [708,727,746]:d.ellipse((x,369,x+7,376),fill='#829c99')
    # The narration asks why a globe appears instead of a logo. Keep that
    # actual problem visible; replacing the favicon belongs to a later shot.
    d.rounded_rectangle((778,360,1112,399),radius=9,fill='#ffffff')
    d.ellipse((791,368,814,391),outline='#49717b',width=2);d.arc((797,368,808,391),0,360,fill='#49717b',width=1);d.line((791,379,814,379),fill='#49717b',width=1)
    d.text((826,368),'Your website',font=font(18),fill='#46616b')
    d.text((719,439),'That tiny browser globe?',font=font(26),fill='#314b58');d.text((719,486),'It could be your brand.',font=font(23),fill='#62808a')
    d.text((45,660),'VOWEL ROUNDING STUDY' if getattr(body,'rounding_review',False) else 'ORAL MATERIAL STUDY' if getattr(body,'solid_mouth_review',False) else 'NECK ART STUDY' if getattr(body,'neck_art_review',False) else 'NECK ATTACHMENT STUDY' if getattr(body,'neck_review',False) else 'F/V CONTACT STUDY' if getattr(body,'fv_review',False) else 'UNDERARM JOIN STUDY' if getattr(body,'socket_review',False) else 'POINTING HAND STUDY',font=font(18),fill='#48636d');d.text((685,603),'Independent shoulders, elbows and wrists',font=font(21),fill='#48636d');d.text((685,636),'Phone-driven lip width · audio-driven jaw' if getattr(body,'rounding_review',False) else 'Solid oral cavity · timing unchanged' if getattr(body,'solid_mouth_review',False) else 'Redrawn collar · registered neck overlap' if getattr(body,'neck_art_review',False) else 'Collar-fixed neck · limited cutout tilt' if getattr(body,'neck_review',False) else 'F/V contact candidate · joins still pending' if getattr(body,'fv_review',False) else 'Local underarm cleanup · neck still pending' if getattr(body,'socket_review',False) else 'Separate wrist drawing · shoulder cleanup pending',font=font(18),fill='#657c83')
    return im.convert('RGB')
if __name__=='__main__':
    cv2.setNumThreads(1)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('frames',type=Path);p.add_argument('--start',type=int,default=0);p.add_argument('--end',type=int,default=231);p.add_argument('--sockets',action='store_true');p.add_argument('--expressions',action='store_true');p.add_argument('--fv-contact',action='store_true');p.add_argument('--neck',action='store_true');p.add_argument('--neck-art',action='store_true');p.add_argument('--solid-mouth',action='store_true');p.add_argument('--rounding',action='store_true');a=p.parse_args();plan=json.loads(a.plan.read_text());
    if a.rounding:
        from cartoon_gesture_body import CartoonRoundedBody
        b=CartoonRoundedBody()
    elif a.solid_mouth:
        from cartoon_gesture_body import CartoonSolidMouthBody
        b=CartoonSolidMouthBody()
    elif a.neck_art:
        from cartoon_gesture_body import CartoonNeckArtBody
        b=CartoonNeckArtBody()
    elif a.neck:
        from cartoon_gesture_body import CartoonNeckBody
        b=CartoonNeckBody()
    elif a.fv_contact:
        from cartoon_gesture_body import CartoonFVBody
        b=CartoonFVBody()
    elif a.expressions:
        from cartoon_gesture_body import CartoonExpressionBody
        b=CartoonExpressionBody()
    elif a.sockets:
        from cartoon_gesture_body import CartoonSocketBody
        b=CartoonSocketBody()
    else:b=CartoonBody()
    a.frames.mkdir(parents=True,exist_ok=True)
    for i in range(a.start,a.end):frame(b,plan,i/48).save(a.frames/f'{i:06}.jpg',quality=96)
    print(json.dumps(dict(start=a.start,end=a.end,fps=48)))
