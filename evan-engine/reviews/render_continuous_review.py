"""Continuous24fps narration review, current layered speech plus verified ending."""
from pathlib import Path
import json,hashlib,shutil,subprocess,wave,time
import cv2,numpy as np
from PIL import Image
from finished_cartoon_scene import FinishedCartoonSceneBody,FinishedStage
from narrated_export import mux_complete_audio
cv2.setNumThreads(1)
root=Path(__file__).resolve().parents[4];repo=root/'work/engine';out=root/'outputs/evan-cartoon-continuous';frames=out/'Frames';frames.mkdir(exist_ok=True)
media=root.parent/'referenced-chatgpt-conversation-this-is-an/work';voice=media/'evan-narration.wav';ff=media/'media-tools/ffmpeg'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
planpath=root/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json';plan=json.loads(planpath.read_text())
assert sha(planpath)=='af01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e'
assert sha(voice)=='28487eb9c730c3d6a9613a4d419d8d590aa3a72c7816de7fb9183d9a7e552f96'
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip();assert not subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True)
source=root/'outputs/evan-cartoon-grin-band';audit=json.loads((source/'Verification.json').read_text());assert audit['cutFrame']==1063 and audit['nativeOutsideLumenExact']==48
body=FinishedCartoonSceneBody();body.enable_separated_face();stage=FinishedStage()
manifest=dict(commit=commit,planSha256=sha(planpath),audioSha256=sha(voice),tailVerificationSha256=sha(source/'Verification.json'),scriptSha256=sha(Path(__file__)),fps=24,frames=552,sourceAudioEnd=352758/16000,defaultChanged=False)
(out/'Source-Manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');shutil.copy2(Path(__file__),out/'Source/render.py.txt')
# The pure speech adapter must join the cached guarded ending without a source change.
for n in [456,504]:
 im=stage.draw(body.render(n/24,plan),n/24,plan)
 assert np.array_equal(np.array(im),np.array(Image.open(source/'After/Frames'/f'{2*n:06}.png'))),f'tail calibration {n}'
rows=[];started=time.monotonic();current=-1
try:
 for n in range(552):
  current=n;p=frames/f'{n:06}.png';t=n/24
  if n<456:
   im=stage.draw(body.render(t,plan),t,plan);im.save(p);face=body.head.last_audit.copy();origin='fresh-current-separated-face'
  else:
   q=source/'After/Frames'/f'{2*n:06}.png';shutil.copy2(q,p);assert sha(p)==sha(q);face=None;origin='verified-48fps-ending-even-sample'
  rows.append(dict(frame=n,time=t,sha256=sha(p),origin=origin,face=face))
  if n%24==0 or n==551:
   progress=dict(lastFrame=n,totalFrames=552,elapsedSeconds=time.monotonic()-started,commit=commit)
   (out/'Progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(progress,flush=True)
except Exception as e:
 (out/'Failure.json').write_text(json.dumps(dict(frame=current,error=str(e),commit=commit),indent=2)+'\n');raise
(out/'Render-Audit.json').write_text(json.dumps(dict(rows=rows,manifest=manifest,freshFrames=456,copiedEndingFrames=96,tailCalibrationFrames=[456,504]),indent=2)+'\n')
with wave.open(str(voice))as f:
 assert (f.getnchannels(),f.getsampwidth(),f.getframerate(),f.getnframes())==(1,2,16000,352758)
 pcm=f.readframes(352758)
padded=pcm+bytes((368000-352758)*2);wav=out/'Original-Narration-With-Postroll.wav'
with wave.open(str(wav),'wb')as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(padded)
with wave.open(str(wav))as f:assert f.getnframes()==368000 and f.readframes(368000)==padded
run=lambda a:subprocess.run([str(ff),'-v','error','-nostdin',*map(str,a)],check=True,capture_output=True)
silent=out/'Silent.mp4';normal=out/'Normal.mp4';slow=out/'Quarter-Speed.mp4'
run(['-y','-framerate',24,'-i',frames/'%06d.png','-frames:v',552,'-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',silent]);audio=mux_complete_audio(ff,silent,wav,normal)
run(['-y','-framerate',6,'-i',frames/'%06d.png','-frames:v',2208,'-vf','fps=24','-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',slow])
films={}
for p,expected in [(normal,552),(slow,2208)]:
 d=run(['-i',p,'-map','0:v:0','-f','framemd5','-']);count=sum(bool(s and not s.startswith('#'))for s in d.stdout.decode().splitlines());assert count==expected;films[p.name]=dict(decodedFrames=count,sha256=sha(p))
report=dict(manifest=manifest,freshFrames=456,verifiedCopiedEndingFrames=96,calibrations=[456,504],films=films,audio=audio,sourcePcmSamples=352758,zeroPadSamples=15242,wavPrefixByteExact=True,firstRaised24fpsFrame=532,firstRaisedTime=532/24,sourceCut48fps=1063/48,minimumJawArea2=min(r['face']['minimumTriangleArea2']for r in rows if r['face']),minimumOralArea2=min(r['face']['minimumOralTriangleArea2']for r in rows if r['face']),defaultChanged=False,independentListeningAccepted=False,realTimeActingAccepted=False,polishedMilestoneReady=False)
assert sha(planpath)==manifest['planSha256'] and sha(voice)==manifest['audioSha256']
(out/'Verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
