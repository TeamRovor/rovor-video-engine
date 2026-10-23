"""Review-only two-corner registration of a genuinely separate lip drawing."""
import hashlib,json,cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from planar_fv_cartoon_head import contact_matrix
from layered_cartoon_head import straight

def register():
 cv2.setNumThreads(1);folder=ROOT/'lower-lip-pressure-v1';source=folder/'source/lip-v2.png';raw=np.array(Image.open(source).convert('RGBA'));before=hashlib.sha256(source.read_bytes()).hexdigest()
 target=np.zeros((16,2),np.float32);target[8]=[198,321];target[0]=[274,320.5];matrix=contact_matrix(target,[[418,789],[768,789]])
 pm=raw.astype('float32');pm[:,:,:3]*=pm[:,:,3:4]/255
 native=cv2.resize(cv2.warpAffine(pm,matrix*3,(1536,1536),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
 image=Image.fromarray(np.rint(np.clip(straight(native),0,255)).astype('uint8'));image.save(folder/'Lower-Lip-Candidate.png');alpha=np.array(image)[:,:,3].astype('float32');edge=[[198.,321.]]
 for x in [201,211,220,229,238,247,256,265,271]:
  values=alpha[:,x];ys=np.flatnonzero(values>=127.5)
  if not len(ys):raise ValueError(f'No half-alpha top edge at native x{x}')
  y=int(ys[0]);edge.append([float(x),float(y-1+(127.5-values[y-1])/(values[y]-values[y-1]))])
 edge.append([274.,320.5]);center=matrix@np.array([592,821,1]);assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 report=dict(source=source.name,sourceSha256=before,sourceSize=list(Image.open(source).size),sourceCorners=[[418,789],[768,789]],targetCorners=[[198,321],[274,320.5]],matrix=matrix.tolist(),sourceTopEdge=edge,topEdgeMeasurement='Half-alpha crossing for UV correspondence only; no source cleanup',neutralCenterMapped=center.tolist(),neutralCenterProposal=[236,328],neutralCenterResidualPixels=float(np.linalg.norm(center-[236,328])),sourceAlphaModified=False,artistCoordinatesMeasured=False,defaultProfileLoaded=False,anatomyAccepted=False,animationReady=False)
 (folder/'Registration.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['neutralCenterMapped']))

if __name__=='__main__':register()
