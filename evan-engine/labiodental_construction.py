"""Opt-in six-plane contact/release construction; not a speech profile.

Coordinates are the artist-guide proposal. Real painted components are sampled;
no source pixels/alpha are cleaned and no default head renderer is changed.
"""
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from current_contact_exposure import CurrentContactHead
from guided_jaw_exposure import target_mesh
from jaw_overlap_exposure import INTERFACE,mapped_interface
from lip_surface_correspondence import source_mesh,corresponding_fields
from painted_contour_cartoon_head import oral_fields
from layered_cartoon_head import over,straight
from face_art_contract import POSES

class FaceCapture(CurrentContactHead):
 def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
  self.clean_face=face.copy()
  return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)

def load(path):
 raw=np.array(Image.open(path).convert('RGBA')).astype('float32');raw[:,:,:3]*=raw[:,:,3:4]/255
 return raw

def upper_carrier_mask(target):
 boundary=mapped_interface(target)
 # Keep the cheek wings; central upper-face skin stops at the UPPER lip.
 # The separate crown and jaw/lower lip now own the opening below this edge.
 for i,(x,_) in enumerate(INTERFACE):
  if 194<=x<=263:
   nx=boundary[i,0];boundary[i,1]=319+abs(nx-236)/38*2
 polygon=np.vstack([[[0,0],[511,0],[511,288]],boundary[::-1],[[0,288]]]).astype('float32')
 raw=np.zeros((1536,1536),np.uint8);cv2.fillPoly(raw,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8)
 return cv2.resize(raw,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255

class LabiodentalConstruction:
 def __init__(self):
  self.head=FaceCapture();self.reference=self.head.weights(np.eye(9)[7]);self.face=self.head.clean_face.copy()
  self.jaw=load(ROOT/'fv-redraw-v1/Contact-Jaw-Candidate.png');self.source_points,self.correspondence=source_mesh(self.jaw)
  self.neck=load(ROOT/'jaw-overlap-v1/Neck.png');self.cap=load(ROOT/'labiodental-guide-v1/Upper-Lip-Candidate-v2.png');self.teeth=load(ROOT/'fv-rig-v3/upper-teeth.png')
  self.cavity=load(ROOT/'painted-oral-parts-v1/Cavity.png')
 def pose(self,release):
  if not 0<=release<=1:raise ValueError('Release must be within0..1')
  contact=POSES['Labiodental'];opened=POSES['LabiodentalRelease'];lower=contact['lower'][1]*(1-release)+opened['lower'][1]*release
  oral=self.head.current_oral.copy();angles=np.arange(16)*np.pi/8
  for start,radius,top,bottom in [(0,38,317.9,lower+1.1),(16,34,319,lower)]:
   x=236+radius*np.cos(angles);line=321-(x-198)*.5/76;s=np.sin(angles)
   oral[start:start+16,0]=x;oral[start:start+16,1]=line+np.where(s>=0,(bottom-320.75)*s,(320.75-top)*s)
  skin=self.head.exposure_skin.copy();skin[46,1]=393+release;target,minimum=target_mesh(oral,skin)
  jaw=cv2.resize(cv2.remap(self.jaw,*corresponding_fields(self.source_points,target),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  cavity=cv2.resize(cv2.remap(self.cavity,*oral_fields(self.head.painted_points,oral),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  parts={'Neck backing':self.neck.copy(),'Painted cavity':cavity,'Fixed upper incisors':self.teeth.copy(),'Drawn jaw and lower lip':jaw,'Drawn upper-lip cap':self.cap.copy(),'Upper face and cheek wings':self.face*upper_carrier_mask(target)[:,:,None]}
  result=np.zeros_like(jaw)
  for part in parts.values():result=over(result,part)
  self.last_parts=parts;self.last_oral=oral.copy()
  return Image.fromarray(np.rint(straight(result)).astype('uint8')),dict(release=float(release),lowerLipY=float(lower),upperLipY=319,incisorTipsY=325,minimumTriangleArea2=minimum,planes=list(parts),sourceArtworkChanged=False,speechProfile=False,anatomyAccepted=False)
