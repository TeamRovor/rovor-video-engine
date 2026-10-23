"""Ten actual mouth/face planes driven by the unchanged narration planner.

Review construction only: pressure is a thickness proxy, cap coordinates are
authored, and the existing jaw/cap artwork remains unapproved. No defaults.
"""
import cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from labiodental_construction import FaceCapture,load
from lower_lip_plane import LowerLipPlane,arch_surface
from guided_jaw_exposure import contour_target_mesh
from jaw_overlap_exposure import INTERFACE,mapped_interface
from lip_surface_correspondence import source_mesh,corresponding_fields
from layered_cartoon_head import over,straight
from lingual_cartoon_head import tongue_lift
from painted_timing import ease

class MaterialCapture(FaceCapture):
 def composite_oral(self,face,cavity,teeth,tongue,contact,closed,aperture,w):
  # Use the same rigid incisor parent at pure/mixed F/V; no material switch.
  self.review_interior=self.current_backing[:,:,3:4]/255
  crown,tip=self.rigid_teeth_parts(w,self.current_oral)
  self.review_teeth=crown*self.review_interior
  self.review_dental_tip=tip*self.review_interior
  visibility=max(float(ease((aperture-8)/12)),tongue_lift(w)*float(ease((aperture-1.2)/4)))
  self.review_tongue=tongue.copy()*visibility
  return super().composite_oral(face,cavity,teeth,tongue,contact,closed,aperture,w)

def inner_arch(oral,upper=False):
 outer=np.vstack([oral[8:16],oral[0]]) if upper else oral[:9][::-1]
 inner=np.vstack([oral[24:32],oral[16]]) if upper else oral[16:25][::-1]
 arch=outer.copy();arch[:,1]=np.interp(arch[:,0],inner[:,0],inner[:,1]);return arch

def face_ownership(target,upper):
 boundary=mapped_interface(target)
 for i,(x,_) in enumerate(INTERFACE):
  if 194<=x<=263:boundary[i,1]=np.interp(boundary[i,0],upper[:,0],upper[:,1])
 polygon=np.vstack([[[0,0],[511,0],[511,288]],boundary[::-1],[[0,288]]]).astype('float32');mask=np.zeros((1536,1536),np.uint8)
 cv2.fillPoly(mask,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8)
 return cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255

class SeparatedOralReview:
 def __init__(self):
  self.head=MaterialCapture();self.jaw=load(ROOT/'jaw-simplification-v1/Jaw-Candidate.png');self.source_points,_=source_mesh(self.jaw);self.lower=LowerLipPlane();self.cap=load(ROOT/'labiodental-guide-v1/Upper-Lip-Candidate-v2.png');self.neck=load(ROOT/'jaw-overlap-v1/Neck.png')
  x=np.linspace(198,274,9);self.cap_edge=np.column_stack([x,321-(x-198)*.5/76-1.75*np.sin(np.linspace(0,np.pi,9))]).astype('float32')
 def at(self,t,plan):
  baseline=self.head.at(t,plan);return self.assemble(baseline)
 def assemble(self,baseline):
  oral=self.head.current_oral;upper=inner_arch(oral,True);lower=inner_arch(oral)
  jaw_oral=oral.copy();jaw_oral[:9,1]=self.lower.jaw_arch(lower,self.head.current_fv)[::-1,1]
  target,minimum=contour_target_mesh(jaw_oral,self.head.exposure_skin)
  if upper[:,1].min()<310:raise ValueError('Mouth crossed protected upper-face guard')
  jaw=cv2.resize(cv2.remap(self.jaw,*corresponding_fields(self.source_points,target),cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT),(512,512),interpolation=cv2.INTER_AREA)
  # Match the upstream native8-bit face stage before restoring brow acting.
  face=straight(self.head.clean_face)
  # Preserve the original non-oral blend, without importing its resting mouth.
  blended=self.head.images['X'].astype('float32')*(1-self.head.weight)+face*self.head.weight;face[:310]=blended[:310]
  face=face.astype('uint8').astype('float32');face[:,:,:3]*=face[:,:,3:4]/255
  finished=np.array(baseline).astype('float32');finished[:,:,:3]*=finished[:,:,3:4]/255
  # Brow repair/acting is applied after the head's oral composite upstream.
  expression=self.head.repair|(self.head.forehead>0);face[expression]=finished[expression]
  underpaint=np.zeros_like(self.head.clean_face);underpaint[305:365,190:285]=self.head.clean_face[305:365,190:285]
  parts={'Neck backing':self.neck.copy(),'Drawn skin underlap':underpaint,'Painted cavity':self.head.current_backing.copy(),'Narration tongue':self.head.review_tongue.copy(),'Rigid upper incisors':self.head.review_teeth.copy(),'Front dental tongue tip':self.head.review_dental_tip.copy(),'Drawn jaw skin':jaw,'Independent lower lip':self.lower.pose(lower,self.head.current_fv),'Independent upper-lip cap':arch_surface(self.cap,self.cap_edge,upper),'Upper face and cheeks':face*face_ownership(target,upper)[:,:,None]}
  result=np.zeros_like(jaw)
  for part in parts.values():result=over(result,part)
  image=Image.fromarray(np.rint(straight(result)).astype('uint8'));self.last_parts=parts;self.last_target=target;self.baseline=baseline
  before=np.array(baseline);after=np.array(image);nose=int(abs(before[288:310,190:280].astype(int)-after[288:310,190:280].astype(int)).max())
  if nose>1:raise ValueError(f'Protected nose changed: {nose}')
  return image,dict(minimumTriangleArea2=minimum,fv=float(self.head.current_fv),width=float(oral[0,0]-oral[8,0]),lowerY=float(oral[20,1]),noseMaximumChange=nose,upper288Exact=bool(np.array_equal(before[:288],after[:288])),planes=list(parts),bakedMouthInUpperCarrier=False,defaultChanged=False,anatomyAccepted=False)
