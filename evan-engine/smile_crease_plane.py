"""One drawn smile-corner accent, opt-in construction review only."""
import hashlib,json,cv2,numpy as np
from cartoon_body import ROOT
from labiodental_construction import load
class SmileCreasePlane:
 def __init__(self):
  folder=ROOT/'smile-crease-v1';p=folder/'source.png';self.registration=json.loads((folder/'Registration.json').read_text())
  if hashlib.sha256(p.read_bytes()).hexdigest()!=self.registration['sourceSha256']:raise ValueError('Smile crease source/registration mismatch')
  self.source=load(p)
 def pose(self,upper,strength):
  arch=np.asarray(upper,np.float32)
  if arch.shape!=(9,2) or not np.isfinite(arch).all() or np.any(np.diff(arch[:,0])<=0):raise ValueError('Expected nine ordered upper lip points')
  if not np.isfinite(strength) or not 0<=strength<=1:raise ValueError('Crease strength must be within0..1')
  if strength==0:return np.zeros((512,512,4),np.float32)
  r=self.registration;v=arch[-1]-arch[0];v=v/np.linalg.norm(v);rotation=np.array([[v[0],-v[1]],[v[1],v[0]]],np.float32)
  scale=r['nativeWidth']/r['halfAlphaBBox'][2];linear=rotation*scale
  destination=arch[-1]+rotation@np.asarray(r['anchorOffset'],np.float32)
  # source alpha is preserved; strength is an authored expression control.
  yy,xx=np.mgrid[:1536,:1536];offset=np.stack([xx/3-destination[0],yy/3-destination[1]],axis=-1)
  source=offset@np.linalg.inv(linear).T+np.asarray(r['sourceAnchor'])
  image=cv2.remap(self.source,source[:,:,0].astype('float32'),source[:,:,1].astype('float32'),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
  return cv2.resize(image,(512,512),interpolation=cv2.INTER_AREA)*strength
