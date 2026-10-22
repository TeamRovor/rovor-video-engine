"""Editable blank artist templates with native references and separate guides.

Construction curves are guide proposals, not substitute mouth artwork.
No new generation, source pixel extraction or runtime changes.
"""
import argparse,json,hashlib
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from psd_tools import PSDImage
from face_art_contract import SIZE,PLANES,POSES,CORNERS,IDENTITY
from maxillary_cartoon_head import MaxillaryCartoonHead
from render_cartoon_head_study import font
from audit_face_art_psd import audit


def guides(pose):
    spec=POSES[pose];im=Image.new('RGBA',SIZE);d=ImageDraw.Draw(im)
    # Guide lines mark interfaces/registration, not final painted lip shapes.
    upper=spec['upper'];lower=spec['lower'];corners=spec.get('corners',CORNERS);left=corners['left'];right=corners['right']
    d.line([tuple(left),tuple(upper),tuple(right)],fill='#007d80',width=1)
    d.line([tuple(left),tuple(lower),tuple(right)],fill='#cb3959',width=1)
    d.line([(181,375),tuple(spec['chin']),(278,spec['chin'][1]-22),(328,355)],fill='#8960aa',width=1)
    anchors={**IDENTITY,**{k+'Corner':v for k,v in corners.items()},'upperLipCenter':upper,'lowerLipCenter':lower,'chin':spec['chin']}
    if 'toothTips' in spec:
        a,b=spec['toothTips'];d.rectangle((a[0],spec['toothTop'],b[0],a[1]),outline='#a86e00',width=1)
        d.line(((a[0]+b[0])/2,spec['toothTop'],(a[0]+b[0])/2,a[1]),fill='#a86e00',width=1)
        anchors.update(incisorLeftTip=a,incisorRightTip=b,incisorTopCenter=[(a[0]+b[0])/2,spec['toothTop']])
    for name,(x,y) in anchors.items():
        d.line((x-2,y,x+2,y),fill='#066c85',width=1);d.line((x,y-2,x,y+2),fill='#066c85',width=1)
    return im,anchors


def build(plan_path,output):
    output.mkdir(parents=True,exist_ok=True);plan=json.loads(plan_path.read_text());head=MaxillaryCartoonHead();rows=[];overview=Image.new('RGB',(1600,900*((len(POSES)+2)//3)+20),'#f3eee2');d=ImageDraw.Draw(overview)
    for i,(pose,spec) in enumerate(POSES.items()):
        column=i%3;offset=(i//3)*900
        reference=head.at(spec['referenceFrame']/48,plan);guide,anchors=guides(pose)
        psd=PSDImage.frompil(Image.new('RGBA',SIZE))
        ref=psd.create_pixel_layer(reference,name='REFERENCE__Current experimental head - not target mouth');ref.visible=False
        for name in PLANES:psd.create_pixel_layer(Image.new('RGBA',SIZE),name='ART__'+name)
        g=psd.create_pixel_layer(guide,name='GUIDE__Proposed registration - hide for artwork export');g.visible=False
        for plane,box in PLANES.items():
            envelope=Image.new('RGBA',SIZE);ed=ImageDraw.Draw(envelope);ed.rectangle(box,outline=(0,125,128,150),width=1);ed.text((box[0]+2,box[1]+2),plane,font=font(10),fill=(0,90,100,200))
            g=psd.create_pixel_layer(envelope,name='GUIDE__Envelope__'+plane);g.visible=False
        path=output/f'{pose}-Drawing-Template.psd';psd.save(path)
        opened=PSDImage.open(path);assert opened.size==SIZE;assert [l.name for l in opened]==[l.name for l in psd]
        np.testing.assert_array_equal(np.array(opened[0].topil().convert('RGBA')),np.array(reference))
        np.testing.assert_array_equal(np.array(opened[10].topil().convert('RGBA')),np.array(guide))
        assert not any(l.visible for l in opened if l.name.startswith(('REFERENCE__','GUIDE__')))
        assert all(not np.asarray(l.topil().convert('RGBA'))[:,:,3].any() for l in opened if l.name.startswith('ART__'))
        report=audit(path,pose);assert not report['structuralPass'];assert not report['animationReady']
        (output/f'{pose}-Blank-Import-Check.json').write_text(json.dumps(report,indent=2)+'\n')
        reference.save(output/f'{pose}-Reference.png');guide.save(output/f'{pose}-Guides.png')
        view=Image.new('RGBA',SIZE,'#f3eee2');view.alpha_composite(reference);view.alpha_composite(guide);overview.paste(view.convert('RGB'),(10+column*530,95+offset));d.text((25+column*530,30+offset),f'{pose} / blank artwork template',font=font(23),fill='#253c49')
        # Magnified guide interface for precise drawing at the small mouth.
        close=view.crop((170,302,310,407)).resize((280,210),Image.Resampling.NEAREST);overview.paste(close,(145+column*530,650+offset))
        rows.append(dict(pose=pose,psd=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),referenceFrame=spec['referenceFrame'],referenceTime=spec['referenceFrame']/48,anchors=anchors,guideType='manually authored design proposals, not measured anatomy or approved motion',requiredArtworkStillBlank=True,blankImportRejected=True,referencePixelsReloadExact=True,registrationGuidePixelsReloadExact=True,paintPlaneCount=len(PLANES)))
    d.text((25,900*((len(POSES)+2)//3)-280),'Proposed interfaces over CURRENT flawed references. Lines are construction guides, not painted lips.',font=font(23),fill='#253c49')
    d.text((25,900*((len(POSES)+2)//3)-15),'All paint layers blank. Contact compression, lip roll and anatomy still require drawing and animator review.',font=font(23),fill='#253c49')
    overview.save(output/'Drawing-Guide-Review.png')
    metadata=dict(size=list(SIZE),planesBackToFront=list(PLANES),drawingEnvelopes=PLANES,poses=rows,source='existing opt-in MaxillaryCartoonHead; source art not changed',planSha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),templatesOnly=True,animationReady=False,runtimeLoaded=False,limits=['All ART layers deliberately blank; not a layered working rig','References are current flawed renderer, not the approved mouth design','Guide anchors proposed for coordinated drawing; artist can revise with metadata','Reference frames are discontinuous snapshots, not a performance or timing test','No phone boundary edits, no speech movie or independent listening this pass'])
    (output/'Template-Manifest.json').write_text(json.dumps(metadata,indent=2)+'\n');return metadata


if __name__=='__main__':
    cv2.setNumThreads(1);p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('output',type=Path);a=p.parse_args();r=build(a.plan,a.output);print(json.dumps(dict(poses=[p['pose'] for p in r['poses']],blankImportsRejected=True,animationReady=False)))
