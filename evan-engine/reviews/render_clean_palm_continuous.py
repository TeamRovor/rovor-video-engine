from pathlib import Path
from types import SimpleNamespace
import json,hashlib,wave,subprocess,sys
import cv2,numpy as np
from PIL import Image
from finished_cartoon_scene import FinishedCartoonSceneBody,FinishedStage
from relaxed_cartoon_scene import RelaxedWristArm
from dismissive_cartoon_review import dismissive_controls
from narrated_export import mux_complete_audio
cv2.setNumThreads(1);root=Path(__file__).resolve().parents[4];out=root/'outputs/evan-cartoon-clean-palm-continuous';source=root/'outputs/evan-cartoon-dismissive-acting';frames=out/'Frames';native=out/'Native';out.mkdir(parents=True,exist_ok=True);frames.mkdir(exist_ok=True);native.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();planpath=root/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json';plan=json.loads(planpath.read_text());body=FinishedCartoonSceneBody();body.head=SimpleNamespace(geometry=body.head.geometry,at=lambda t,p:Image.new('RGBA',(512,512)));stage=FinishedStage();oldarm=body.arms['right'];folder=root/'work/engine/evan-character/cartoon-v1/open-palm-clean-v1';arm=RelaxedWristArm(Image.open(folder/'right-skin.png').convert('RGBA'),oldarm.geometry,oldarm);roi=np.s_[300:650,365:665];rows=[]
def compose(layers,c):
 im=Image.new('RGBA',(1464,1536))
 for p in layers.values():im.alpha_composite(p)
 return im.rotate(c['body_roll'],Image.Resampling.BICUBIC,center=(732,950))
def render(n):
 t=n/24;c=dismissive_controls(t,plan);layers=body.layers(t,plan,c);baseline=np.array(stage.draw(compose(layers,c),t,plan));cached=np.array(Image.open(source/'Frames'/f'{n:06}.png'));assert np.array_equal(baseline[roi],cached[roi]),n
 oldlayer=layers['arm-right'];im,(x,y)=arm.render(c['right']);newlayer=Image.new('RGBA',(1464,1536));newlayer.alpha_composite(im,(x+220,y));layers['arm-right']=newlayer;fresh=np.array(stage.draw(compose(layers,c),t,plan));changed=np.any(fresh!=baseline,axis=2);outside=changed.copy();outside[roi]=False;assert not outside.any(),n
 actual=cached.copy();actual[roi]=fresh[roi];diff=np.any(actual!=cached,axis=2);outside=diff.copy();outside[roi]=False;assert not outside.any();assert np.array_equal(actual[:,685:],cached[:,685:])
 p=arm.posed_vertices(c['right'])[np.array(arm.triangles)];v=p[:,1:]-p[:,0,None];area=float((v[:,0,0]*v[:,1,1]-v[:,0,1]*v[:,1,0]).min());assert area>0
 return Image.fromarray(actual),Image.fromarray(cached),oldlayer,newlayer,dict(sourceFrame=n,time=t,angles=c['right'],minimumArmArea2=area,cachedHandRegionCalibrationExact=True,outsideRightHandRegionExact=True,faceLeftArmAndBrandExact=True,changedStagePixels=int(diff.sum()))
if '--pilot' in sys.argv:
 for n in [0,60,396,531]:
  after,before,oldlayer,newlayer,row=render(n)
  after.save(out/f'Pilot-Stage-{n}.png');newlayer.crop((900,550,1380,1050)).save(out/f'Pilot-Native-{n}.png');print(row,flush=True)
 sys.exit()
import shutil
from painted_character import arm_transforms,rotation
journal=(out/'Frame-Audit.jsonl').open('w')
for n in range(532):
 after,before,oldlayer,newlayer,row=render(n);after.save(frames/f'{n:06}.png')
 center=(arm_transforms(arm.geometry,row['angles'])[2]@np.r_[arm.geometry['wrist'],1])[:2]+[220,0];cx,cy=map(int,np.rint(center));box=(cx-180,cy-150,cx+190,cy+180);newlayer.crop(box).save(native/f'{n:06}.png');row['nativeCropBox']=box
 yy,xx=np.where(np.array(newlayer)[:,:,3]>127);corners=np.array([[xx.min(),yy.min(),1],[xx.max(),yy.min(),1],[xx.max(),yy.max(),1],[xx.min(),yy.max(),1]]);c=dismissive_controls(n/24,plan);points=(corners@rotation((732,950),-c['body_roll']).T)[:,:2]*[849/1464,891/1536]+[-120,30];assert points[:,0].min()>0 and points[:,0].max()<680 and points[:,1].min()>0 and points[:,1].max()<720,n
 row['halfAlphaStageBounds']=[float(points[:,0].min()),float(points[:,1].min()),float(points[:,0].max()),float(points[:,1].max())];rows.append(row);journal.write(json.dumps(row)+'\n');journal.flush()
 if n%24==0:print(n,flush=True)
journal.close()
for n in range(532,552):
 p=source/'Frames'/f'{n:06}.png';shutil.copy2(p,frames/p.name);assert sha(p)==sha(frames/p.name)
(out/'Render-Audit.json').write_text(json.dumps(dict(rows=rows,closingFramesByteExact=20,sourcePlanSha256=sha(planpath)),indent=2)+'\n')
(out/'Frame-Hashes.json').write_text(json.dumps({f'{n:06}.png':sha(frames/f'{n:06}.png')for n in range(552)},indent=2)+'\n')
ff=root.parent/'referenced-chatgpt-conversation-this-is-an/work/media-tools/ffmpeg';run=lambda a:subprocess.run([str(ff),'-v','error','-nostdin',*map(str,a)],check=True,capture_output=True);silent=out/'Silent.mp4';normal=out/'Normal.mp4';slow=out/'Quarter-Speed.mp4';wav=out/'Original-Narration-With-Postroll.wav';shutil.copy2(source/wav.name,wav);assert sha(wav)==sha(source/wav.name)
run(['-y','-framerate',24,'-i',frames/'%06d.png','-frames:v',552,'-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',silent]);audio=mux_complete_audio(ff,silent,wav,normal)
run(['-y','-framerate',6,'-i',frames/'%06d.png','-frames:v',2208,'-vf','fps=24','-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',slow]);films={}
for p,count in [(normal,552),(slow,2208)]:
 d=run(['-i',p,'-map','0:v:0','-f','framemd5','-']);actual=sum(bool(s and not s.startswith('#'))for s in d.stdout.decode().splitlines());assert actual==count;films[p.name]=dict(decodedFrames=actual,sha256=sha(p))
for name,digest in json.loads((out/'Frame-Hashes.json').read_text()).items():assert sha(frames/name)==digest
report=dict(frames=552,updatedHandFrames=532,closingFramesByteExact=20,cachedRightHandRegionCalibrationExactFrames=532,outsideRightHandRegionExactFrames=532,faceLeftArmAndBrandExact=True,halfAlphaRightArmStageBoundsClearFrames=532,minimumArmArea2=min(r['minimumArmArea2']for r in rows),films=films,audio=audio,sourceWavByteExact=True,sourcePlanSha256=sha(planpath),sourceSha256=sha(folder/'source-v2.png'),registeredSkinSha256=sha(folder/'right-skin.png'),fullFilmUpdated=True,defaultChanged=False,sourceAlphaModified=False,fingerArticulated=False,independentListeningAccepted=False,realTimeActingAccepted=False,polishedMilestoneReady=False)
(out/'Verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
