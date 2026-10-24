"""Complete recording/control geometry audit; no raster/artwork acceptance.

Stops the actual head pipeline immediately after its oral and skin targets.
Every48fps sample and every phone midpoint is checked, including brief phones
that fall between output frames. Failures stay explicit; no geometry fallback.
Oral triangle orientation uses the same gate as the final layered assembly.
"""
import argparse,hashlib,json,math,wave
from pathlib import Path
import numpy as np
from separated_oral_review import SeparatedOralReview,MaterialCapture,inner_arch,check_oral_mesh

class GeometryCaptured(Exception):pass

class GeometryCapture(MaterialCapture):
 def skin_target(self,weights,target):
  result=super().skin_target(weights,target)
  raise GeometryCaptured()

def capture(rig,t,plan):
 try:rig.head.at(t,plan)
 except GeometryCaptured:pass
 else:raise RuntimeError('Geometry capture did not reach skin target')
 target,minimum=rig.jaw_target();oral=rig.head.current_oral;upper=inner_arch(oral,True)
 oral_minimum=check_oral_mesh(oral)
 if upper[:,1].min()<310:raise ValueError('Mouth crossed protected upper-face guard')
 return dict(time=float(t),minimumTriangleArea2=minimum,minimumOralTriangleArea2=oral_minimum,width=float(oral[0,0]-oral[8,0]),lowerY=float(oral[20,1]),chinY=float(rig.head.exposure_skin[46,1]),fv=rig.head.current_fv,upperGuardMinimumY=float(upper[:,1].min()),targetFinite=bool(np.isfinite(target).all()))

def audit(plan,duration):
 if not np.isfinite(duration) or duration<=0:raise ValueError('Recording duration must be positive and finite')
 rig=SeparatedOralReview();rig.head=GeometryCapture();rows=[];failures=[]
 samples=[(i/48,dict(sourceFrame=i)) for i in range(math.ceil(duration*48))]
 samples += [((p['start']+p['end'])/2,dict(phoneIndex=i,phone=p['phone'],word=p['word'])) for i,p in enumerate(plan['phonemes'])]
 for t,identity in samples:
  try:rows.append(dict(capture(rig,t,plan),**identity))
  except ValueError as error:failures.append(dict(time=t,error=str(error),**identity))
 return dict(expectedFrames=math.ceil(duration*48),expectedPhoneMidpoints=len(plan['phonemes']),rows=rows,failures=failures,allRequestedSamplesPassed=not failures,geometryOnly=True,pixelOwnershipChecked=False,timingChanged=False,animationAccepted=False)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('audio',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 with wave.open(str(a.audio)) as f:
  if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(16000,1,2):raise ValueError('Expected original mono16k PCM16 voice')
  duration=f.getnframes()/f.getframerate()
 report=audit(json.loads(a.plan.read_text()),duration);report.update(planSha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),audioSha256=hashlib.sha256(a.audio.read_bytes()).hexdigest());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
 if report['failures']:raise SystemExit(1)
