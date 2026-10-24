"""Register the review-only jaw drawing; preserve original paint and alpha."""
import hashlib,json
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from planar_fv_cartoon_head import contact_matrix
from layered_cartoon_head import straight
from lip_surface_correspondence import source_mesh

def register():
 cv2.setNumThreads(1);folder=ROOT/'jaw-simplification-v1'
 source=folder/'source/jaw-v2.png';raw=np.array(Image.open(source).convert('RGBA'))
 before=hashlib.sha256(source.read_bytes()).hexdigest()
 # Two manually reviewed attachment points; chin is held out from fitting.
 target=np.zeros((16,2),np.float32);target[8]=[164,313];target[0]=[336,317]
 matrix=contact_matrix(target,[[401,763],[827,774]])
 pm=raw.astype('float32');pm[:,:,:3]*=pm[:,:,3:4]/255
 native=cv2.resize(cv2.warpAffine(pm,matrix*3,(1536,1536),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
 image=Image.fromarray(np.rint(np.clip(straight(native),0,255)).astype('uint8'));image.save(folder/'Jaw-Candidate.png')
 _,correspondence=source_mesh(np.array(image).astype('float32'))
 chin=matrix@np.array([559,985,1]);error=float(np.linalg.norm(chin-[230,401]))
 assert np.isfinite(chin).all()
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 report=dict(source=source.name,sourceSha256=before,sourceSize=list(Image.open(source).size),sourceCorners=[[401,763],[827,774]],targetCorners=[[164,313],[336,317]],matrix=matrix.tolist(),registration='uniform two-corner parent; no chin fit or alpha cleanup',heldOutChin=dict(source=[559,985],target=[230,401],mapped=chin.tolist(),residualPixels=error,withinTwoPixels=error<2),correspondence=correspondence,sourceAlphaModified=False,placementAccepted=False,defaultProfileLoaded=False,animationReady=False)
 (folder/'Registration.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report['heldOutChin']))

if __name__=='__main__':register()
