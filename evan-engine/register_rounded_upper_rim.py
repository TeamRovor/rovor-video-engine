"""Uniform corner registration and measured source UVs; no alpha cleanup."""
import hashlib,json,cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from layered_cartoon_head import straight

def register():
 folder=ROOT/'rounded-upper-rim-v1';path=folder/'source/upper-rim-v1.png';raw=np.array(Image.open(path).convert('RGBA')).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
 source=np.array([[391,536],[1382,536]],np.float32);target=np.array([[198,321],[274,320.5]],np.float32);v=(target[1]-target[0])/(source[1,0]-source[0,0]);matrix=np.array([[v[0],-v[1],0],[v[1],v[0],0]],np.float32);matrix[:,2]=target[0]-matrix[:,:2]@source[0]
 np.testing.assert_allclose(cv2.transform(source[None],matrix)[0],target,atol=.001)
 mapped=cv2.warpAffine(raw,matrix,(512,512),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT);Image.fromarray(np.rint(straight(mapped)).astype('uint8')).save(folder/'Upper-Rim-Candidate.png')
 edge=[]
 for i,x in enumerate(np.linspace(198,274,9)):
  if i in (0,8):y=float(target[0 if i==0 else 1,1])
  else:
   alpha=cv2.remap(mapped[:,:,3],np.full((512,1),x,np.float32),np.arange(512,dtype=np.float32)[:,None],cv2.INTER_LINEAR)[:,0];rows=np.where(alpha>=127.5)[0]
   if not len(rows):raise ValueError('No bounded upper rim at source UV')
   last=int(rows[-1]);bottom=last+(alpha[last]-127.5)/max(float(alpha[last]-alpha[last+1]),1e-6);y=bottom-1.
  edge.append([float(x),float(y)])
 report=dict(sourceCorners=source.tolist(),authoredTargetCorners=target.tolist(),matrix=matrix.tolist(),sourceEdge=edge,edgeNote='Interior half-alpha bottom crossings minus authored1px ink underlap; endpoint corner guides. Measurement only.',sourceSha256=hashlib.sha256(path.read_bytes()).hexdigest(),sourceAlphaModified=False,placementAccepted=False,anatomyCalibrated=False)
 (folder/'Registration.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':print(json.dumps(register(),indent=2))
