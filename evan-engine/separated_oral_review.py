"""Ten actual mouth/face planes driven by the shared narration planner.

Review construction only: pressure is a thickness proxy, corner/overlap guides
are authored, and jaw/cap artwork remains unapproved. No defaults.
"""
import json,cv2,numpy as np
from PIL import Image
from cartoon_body import ROOT
from labiodental_construction import FaceCapture,load
from lower_lip_plane import LowerLipPlane,arch_surface
from guided_jaw_exposure import contour_target_mesh,SOURCE,POLYGON
from cartoon_neck import jaw_cut
from jaw_overlap_exposure import INTERFACE,mapped_interface
from lip_surface_correspondence import corresponding_fields
from layered_cartoon_head import over,straight
from lingual_cartoon_head import tongue_lift
from painted_timing import ease,flowing_track
from speech_planner import VOWELS
from english_articulation import PHONE_CATALOG
from duration_cartoon_head import duration_jaw_weights
from rounded_cartoon_head import RoundedCartoonHead,rounding_identity
from cartoon_head import TRIANGLES,area

ORAL_TRIANGLES=[ids for ids in TRIANGLES if max(ids)<32]

def check_oral_mesh(oral):
 if not np.isfinite(oral).all():raise ValueError('Non-finite oral geometry')
 minimum=min(area(oral,ids) for ids in ORAL_TRIANGLES)
 if minimum<=0:raise ValueError(f'Oral mesh triangle foldover: {minimum}')
 return minimum

def corner_signature(plan):
 rows=lambda ps:tuple((p['start'],p['end'],p['phone'],p['value']) for p in ps)
 return (rows(plan['phonemes']),rows(plan.get('gestures',plan['phonemes'])),plan['audio']['step'],tuple(plan['audio']['energy']),tuple((s['start'],s['end']) for s in plan.get('silences',[])))

def phonetic_corner_keys(plan,pose):
 keys={}
 for p in plan['phonemes']:
  a,b=p['start'],p['end'];mid=(a+b)/2;base=p['phone'].rstrip('012')
  if not np.isfinite([a,b]).all() or b<=a:raise ValueError('Expected finite positive phone intervals')
  if base in {'P','B','M','F','V'}:times=[min(a+.015,mid),max(b-.010,mid)]
  elif base in VOWELS:
   phases=len(PHONE_CATALOG[base]['targets']);times=[a+(b-a)*(i+.5)/phases for i in range(phases)]
  elif base=='W':times=[mid]
  else:continue
  for t in times:keys[round(t,9)]=(t,*pose(t))
 for s in plan.get('silences',[]):
  if not np.isfinite([s['start'],s['end']]).all() or s['end']<s['start']:raise ValueError('Expected finite ordered silence intervals')
  if s['end']-s['start']>=.08:
   for t in [s['start']+.035,s['end']-.035]:keys[round(t,9)]=(t,*pose(t))
 ordered=sorted(keys.values())
 return [[(row[0],row[j]) for row in ordered] for j in [1,2]] if ordered else None

def rounded_oral_arch(oral,aperture,strength):
 if not np.isfinite(strength) or not 0<=strength<=1:raise ValueError('Rounding strength must be within0..1')
 if not strength:return oral.copy()
 # shortcut: ellipse split is authored; replace with artist-approved articulation curves.
 result=oral.copy();gap=max(.15,float(aperture)-1);upper=min(8.,.38*gap);lower=gap-upper
 for start,top,bottom in [(0,upper+1.1,lower+1.1),(16,upper,lower)]:
  points=oral[start:start+16];left,right=points[8],points[0];u=(points[:,0]-left[0])/(right[0]-left[0]);chord=left[1]+u*(right[1]-left[1])
  arc=np.sqrt(np.maximum(0,1-(2*u-1)**2));offset=np.where(np.arange(16)<=8,arc*bottom,-arc*top)
  result[start:start+16,1]=points[:,1]*(1-strength)+(chord+offset)*strength
 return result

class MaterialCapture(FaceCapture):
 def baseline_corners(self,t,plan):
  # RoundedDuration preserves these original X controls while scaling height.
  points=RoundedCartoonHead.target_points(self,duration_jaw_weights(t,plan),rounding_identity(t,plan))
  return float(points[8,0]),float(points[0,0])
 def at(self,t,plan):
  previous=getattr(self,'corner_time',None)
  try:
   if plan.get('alignment',{}).get('status')=='acoustic':
    signature=corner_signature(plan)
    if signature!=getattr(self,'corner_signature',None):
     keys=phonetic_corner_keys(plan,lambda time:self.baseline_corners(time,plan))
     self.corner_keys=keys;self.corner_signature=signature
    self.corner_time=t if self.corner_keys else None
   else:self.corner_time=None
   return super().at(t,plan)
  finally:self.corner_time=previous
 def weights(self,weights,expression=None,shape_weights=None,geometry_weights=None):
  previous=getattr(self,'review_rounding',0.)
  identity=np.asarray(weights if shape_weights is None else shape_weights,float);identity=identity/identity.sum()
  jaw=np.asarray(weights if geometry_weights is None else geometry_weights,float);jaw=jaw/jaw.sum()
  self.review_rounding=float(np.clip((identity[5]+identity[6])/max(float(identity[1:].sum()),1e-9)*(1-jaw[1]-jaw[7]),0,1))
  try:return super().weights(weights,expression,shape_weights=shape_weights,geometry_weights=geometry_weights)
  finally:self.review_rounding=previous
 def oral_target(self,target,aperture):
  oral=super().oral_target(target,aperture)
  oral=rounded_oral_arch(oral,aperture,self.review_rounding)
  if getattr(self,'corner_time',None) is not None:
   left,right=[flowing_track(self.corner_time,keys) for keys in self.corner_keys];a,b=oral[8,0],oral[0,0]
   if not np.isfinite([left,right,a,b]).all() or right<=left or b<=a:raise ValueError('Invalid lip-corner span')
   oral[:32,0]=left+(oral[:32,0]-a)*(right-left)/(b-a)
  self.current_oral=oral.copy();self.current_rounding=self.review_rounding;self.current_round_material=self.review_rounding*float(ease((aperture-3)/8));return oral
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
 # Keep inner contour X and Y together; mixing outer X with clamped inner Y
 # flattens the corner spans and turns narrow rounded mouths into wedges.
 return (np.vstack([oral[24:32],oral[16]]) if upper else oral[16:25][::-1]).copy()

def face_ownership(target,upper):
 boundary=mapped_interface(target)
 for i,(x,_) in enumerate(INTERFACE):
  if 194<=x<=263:boundary[i,1]=np.interp(boundary[i,0],upper[:,0],upper[:,1])
 polygon=np.vstack([[[0,0],[511,0],[511,288]],boundary[::-1],[[0,288]]]).astype('float32');mask=np.zeros((1536,1536),np.uint8)
 cv2.fillPoly(mask,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8)
 return cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255

def original_jaw_skin(source):
 # Keep the chin through the neck split; the ear belongs to the upper face.
 polygon=np.vstack([POLYGON[:9],[[329,448],[128,448],[128,315]]])
 mask=np.zeros((1536,1536),np.uint8)
 cv2.fillPoly(mask,[np.rint(polygon*3*256).astype('int32')],255,lineType=cv2.LINE_AA,shift=8)
 mask=cv2.resize(mask,(512,512),interpolation=cv2.INTER_AREA).astype('float32')/255
 yy,xx=np.mgrid[:512,:512];mask*=np.clip((jaw_cut(xx)+5-yy)/3,0,1)
 jaw=source.astype('float32').copy();jaw[:,:,:3]*=jaw[:,:,3:4]/255
 return jaw*mask[:,:,None]

class SeparatedOralReview:
 def __init__(self):
  self.head=MaterialCapture();self.jaw=original_jaw_skin(self.head.layers['face-skin']);self.source_points=SOURCE.copy();self.lower=LowerLipPlane();self.cap=load(ROOT/'labiodental-guide-v1/Upper-Lip-Candidate-v2.png');self.neck=load(ROOT/'jaw-overlap-v1/Neck.png')
  folder=ROOT/'rounded-upper-rim-v1';self.round_cap=load(folder/'Upper-Rim-Candidate.png');self.round_edge=np.asarray(json.loads((folder/'Registration.json').read_text())['sourceEdge'],np.float32)
  x=np.linspace(198,274,9);self.cap_edge=np.column_stack([x,321-(x-198)*.5/76-1.75*np.sin(np.linspace(0,np.pi,9))]).astype('float32')
 def at(self,t,plan):
  baseline=self.head.at(t,plan);return self.assemble(baseline)
 def jaw_target(self):
  oral=self.head.current_oral;lower=inner_arch(oral)
  edge=self.lower.jaw_arch(lower,self.head.current_fv)
  jaw_oral=oral.copy();jaw_oral[:9,1]=np.interp(oral[:9,0],edge[:,0],edge[:,1])
  return contour_target_mesh(jaw_oral,self.head.exposure_skin)
 def assemble(self,baseline):
  oral=self.head.current_oral;oral_minimum=check_oral_mesh(oral);upper=inner_arch(oral,True);lower=inner_arch(oral)
  target,minimum=self.jaw_target()
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
  rounding=self.head.current_round_material;cap=arch_surface(self.cap,self.cap_edge,upper)*(1-rounding)+arch_surface(self.round_cap,self.round_edge,upper)*rounding
  parts={'Neck backing':self.neck.copy(),'Drawn skin underlap':underpaint,'Painted cavity':self.head.current_backing.copy(),'Narration tongue':self.head.review_tongue.copy(),'Rigid upper incisors':self.head.review_teeth.copy(),'Front dental tongue tip':self.head.review_dental_tip.copy(),'Drawn jaw skin':jaw,'Independent lower lip':self.lower.pose(lower,self.head.current_fv),'Independent upper-lip cap':cap,'Upper face and cheeks':face*face_ownership(target,upper)[:,:,None]}
  result=np.zeros_like(jaw)
  for part in parts.values():result=over(result,part)
  image=Image.fromarray(np.rint(straight(result)).astype('uint8'));self.last_parts=parts;self.last_target=target;self.baseline=baseline
  before=np.array(baseline);after=np.array(image);nose=int(abs(before[288:310,190:280].astype(int)-after[288:310,190:280].astype(int)).max())
  if nose>1:raise ValueError(f'Protected nose changed: {nose}')
  return image,dict(roundingStrength=rounding,minimumTriangleArea2=minimum,minimumOralTriangleArea2=oral_minimum,fv=float(self.head.current_fv),width=float(oral[0,0]-oral[8,0]),lowerY=float(oral[20,1]),noseMaximumChange=nose,upper288Exact=bool(np.array_equal(before[:288],after[:288])),planes=list(parts),bakedMouthInUpperCarrier=False,defaultChanged=False,anatomyAccepted=False)
