"""Reference-only acoustic/lip trace; never retimes the disputed tiny/little words."""
from pathlib import Path
import hashlib,json,sys,shutil,subprocess,wave
import cv2,numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from speech_alignment_audit import read_audio,spectrum
from audit_separated_geometry import GeometryCapture,capture
from cartoon_upper_face import CartoonUpperFace

cv2.setNumThreads(1)
r=Path(__file__).resolve().parents[4];repo=r/'work/engine';o=r/'outputs/evan-cartoon-tiny-little-trace';o.mkdir(exist_ok=True)
planpath=r/'outputs/evan-speech-alignment/Aligned-Speech-Plan.json';plan=json.loads(planpath.read_text());voice=r.parent/'referenced-chatgpt-conversation-this-is-an/work/evan-narration.wav';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(planpath)=='af01ebd2e5f3bfeb5a46db2912321eab81d44c984b0999e3d36d11f1a77fcf7e'
assert sha(voice)=='28487eb9c730c3d6a9613a4d419d8d590aa3a72c7816de7fb9183d9a7e552f96'
x,rate=read_audio(voice);assert rate==16000
with wave.open(str(voice))as f:assert (f.getnchannels(),f.getsampwidth())==(1,2);original=f.readframes(f.getnframes())
full=r/'outputs/evan-cartoon-forehead-continuous'
with wave.open(str(full/'Original-Narration-With-Postroll.wav'))as f:full_pcm=f.readframes(f.getnframes())
assert full_pcm[:len(original)]==original
words={w['scriptIndex']:w for w in plan['words']};assert [words[i]['word']for i in [8,9]]==['tiny','little']
reviewpath=repo/'evan-engine/reviews/evan-reference-timing-v1.json';review=json.loads(reviewpath.read_text());flags=[w for w in review['words']if w['scriptIndex']in [8,9]];assert len(review['words'])==18 and len(flags)==2
start,end=2.28,2.82;a,b=round(start*rate),round(end*rate);y=x[a:b];db,st,frequency=spectrum(y,rate,a);assert len(st)>20 and abs(st[0]-(a+(400-1)/2)/rate)<1e-12
power=10**(db[frequency<=5000]/10);norm=power/np.maximum(np.linalg.norm(power,axis=0),1e-12);delta=1-np.sum(norm[:,1:]*norm[:,:-1],axis=0);assert np.isfinite(delta).all()
sys.path.insert(0,str(r/'work/payoff-lean-review'));import pilot
rig=pilot.head.rig;original_head=rig.head;upper=CartoonUpperFace(folder_name='eye-underlay-v4');baseline_upper=CartoonUpperFace();fixtures={}
for n in [56,63,64,67]:
 im=pilot.head.at(n/24,plan);oral=rig.head.current_oral.copy();jaw=rig.last_target.copy();audit=pilot.head.last_audit.copy();expression=rig.head.expression_control(n/24,plan);face=upper.render(im,expression,0)
 before=baseline_upper.render(im,expression,0);assert np.array_equal(np.array(before)[240:],np.array(face)[240:]);assert np.array_equal(np.array(im)[310:],np.array(face)[310:]);assert np.array_equal(oral,rig.head.current_oral)and np.array_equal(jaw,rig.last_target)and audit==pilot.head.last_audit
 face.save(o/f'Native-{n:03}.png');fixtures[n]=oral
class Trace(GeometryCapture):
 def oral_target(self,target,aperture):
  self.input_aperture=float(aperture)
  return super().oral_target(target,aperture)
traced=Trace();traced.expression_control=original_head.expression_control;rig.head=traced
try:
 for n,oral in fixtures.items():capture(rig,n/24,plan);np.testing.assert_allclose(traced.current_oral,oral,rtol=0,atol=1e-9)
 rows=[]
 for k in range(int(np.ceil(start*480)),int(np.floor(end*480))+1):
  row=capture(rig,k/480,plan);oral=traced.current_oral;row.update(inputAperture=traced.input_aperture,innerGap=float(oral[20,1]-oral[28,1]),upperY=float(oral[28,1]));rows.append(row)
finally:rig.head=original_head
assert rows[0]['time']>=start and rows[-1]['time']<=end
phones=[p for p in plan['phonemes']if p['end']>start and p['start']<end];ts=np.array([z['time']for z in rows]);fig,axes=plt.subplots(5,1,figsize=(14,11),sharex=True,gridspec_kw={'height_ratios':[1,2,1,1,1]})
axes[0].plot((a+np.arange(len(y)))/rate,y,lw=.5);axes[0].set_ylabel('Original PCM')
for p in phones:axes[0].text((max(start,p['start'])+min(end,p['end']))/2,1.03,p['phone'],transform=axes[0].get_xaxis_transform(),ha='center',fontsize=9)
axes[1].pcolormesh(st,frequency,db,shading='nearest',cmap='magma',vmin=-55,vmax=5);axes[1].set_ylim(0,5000);axes[1].set_ylabel('Hz / 25ms FFT')
axes[2].plot(st[1:],delta,color='#ad6634');axes[2].set_ylabel('Adjacent spectral\ncosine distance');axes[2].set_ylim(bottom=0)
axes[3].plot(ts,[z['inputAperture']for z in rows],label='Aperture entering actual oral construction');axes[3].plot(ts,[z['innerGap']for z in rows],label='Actual inner-lip gap');axes[3].set_ylabel('Native pixels');axes[3].legend(fontsize=8)
axes[4].plot(ts,[z['upperY']for z in rows],label='Upper inner lip Y');axes[4].plot(ts,[z['lowerY']for z in rows],label='Lower inner lip Y');axes[4].set_ylabel('Native lip Y');axes[4].legend(fontsize=8);axes[4].set_xlabel('Original recording seconds')
for ax in axes:
 ax.set_xlim(start,end);ax.axvline(2.36,color='#b56337',ls='--',label='Older tiny/little anchor2.36');ax.axvline(2.65,color='#248b9d',ls='--',label='Acoustic tiny/little estimate2.65')
 for p in phones:ax.axvline(p['start'],color='#777777',alpha=.25,lw=.5)
axes[0].legend(fontsize=8);fig.suptitle('Tiny → little: original recording beside actual continuous lip targets\nWord/phone labels remain estimates; spectral changes are not automatic boundaries')
fig.text(.02,.01,'25ms windows / 5ms hop; windows mix neighboring sounds. No timing/pose changes. Geometry traces are authored controls, not measured human motion.',fontsize=9);fig.tight_layout(rect=[0,.03,1,.94]);fig.savefig(o/'Acoustic-Lip-Trace.png',dpi=120);plt.close(fig)
im=Image.open(o/'Acoustic-Lip-Trace.png');im.crop((0,0,im.width,im.height//2)).save(o/'Trace-Top.png');im.crop((0,im.height//2,im.width,im.height)).save(o/'Trace-Bottom.png')
(o/'Frames').mkdir(exist_ok=True);hashes=json.loads((full/'Frame-Hashes.json').read_text())
for n in range(48,78):
 p=full/'Frames'/f'{n:06}.png';assert sha(p)==hashes[p.name];dst=o/'Frames'/f'{n-48:06}.png';shutil.copyfile(p,dst);assert sha(dst)==sha(p)
context=original[32000*2:52000*2]
with wave.open(str(o/'Exact-Context.wav'),'wb')as f:f.setparams((1,2,rate,0,'NONE','not compressed'));f.writeframes(context)
with wave.open(str(o/'Exact-Context.wav'))as f:assert f.readframes(f.getnframes())==context and len(context)==40000
ff=r.parent/'referenced-chatgpt-conversation-this-is-an/work/media-tools/ffmpeg';run=lambda args:subprocess.run([str(ff),'-v','error','-nostdin',*map(str,args)],check=True,capture_output=True)
from narrated_export import mux_complete_audio
run(['-y','-framerate',24,'-i',o/'Frames/%06d.png','-frames:v',30,'-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',o/'Silent.mp4']);audio=mux_complete_audio(ff,o/'Silent.mp4',o/'Exact-Context.wav',o/'Normal.mp4');run(['-y','-framerate',6,'-i',o/'Frames/%06d.png','-frames:v',120,'-vf','fps=24','-an','-c:v','libx264','-preset','fast','-crf',16,'-pix_fmt','yuv420p',o/'Quarter-Speed.mp4']);films={}
for name,count,indices in [('Normal',30,[8,15,16,19]),('Quarter-Speed',120,[60,64])]:
 result=run(['-i',o/(name+'.mp4'),'-map','0:v:0','-f','framemd5','-']);assert sum(bool(s and not s.startswith('#'))for s in result.stdout.decode().splitlines())==count;films[name]=dict(decodedFrames=count,sha256=sha(o/(name+'.mp4')));select="select='"+'+'.join(f'eq(n,{i})'for i in indices)+"'";run(['-y','-i',o/(name+'.mp4'),'-vf',select,'-fps_mode','passthrough',o/('Encoded-'+name+'-%02d.png')])
report=dict(sourceAudioSha256=sha(voice),planSha256=sha(planpath),referenceReviewSha256=sha(reviewpath),traceRange=[start,end],traceSourceSamples=[a,b],fftWindowSamples=400,fftHopSamples=80,spectrumTimes=st.tolist(),spectralCosineDistance=delta.tolist(),phoneLabels=phones,wordHypotheses=flags,rows=rows,actualRasterGeometryChecks=[56,63,64,67],geometryMatchesActualRasterOralTo1eMinus9=True,contextPcmRange=[32000,52000],contextPcmCount=20000,contextPcmByteExact=True,stageSourceFrames=[48,78],stageFramesByteExact=30,films=films,audio=audio,timingChanged=False,flagsCleared=0,flagsUnresolved=18,listeningVerified=False,exactBoundariesVerified=False,animationAccepted=False,polishedMilestoneReady=False)
(o/'Trace.json').write_text(json.dumps(report,indent=2)+'\n');(o/'Frame-Hashes.json').write_text(json.dumps({str(p.relative_to(o)):sha(p)for p in sorted(o.rglob('*.png'))},indent=2)+'\n');print('Trace complete:',len(rows),'samples;4actual raster geometry matches;30/120decoded;20000exactPCM; no timing changed')
