"""Fresh material/geometry, geometric crown occlusion and source safety."""
import unittest,cv2,numpy as np
from separated_oral_review import SeparatedOralReview,inner_arch,rounded_oral_arch,original_jaw_skin

class SeparatedOralTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cv2.setNumThreads(1);cls.rig=SeparatedOralReview()
 def pose(self,fv):
  w=np.eye(9)[3]*(1-fv)+np.eye(9)[7]*fv;baseline=self.rig.head.weights(w);return self.rig.assemble(baseline)
 def test_assembly_rejects_folded_oral_mesh_before_returning_pixels(self):
  self.pose(.4);oral=self.rig.head.current_oral.copy()
  try:
   self.rig.head.current_oral[[17,18]]=oral[[18,17]]
   with self.assertRaisesRegex(ValueError,'Oral mesh triangle foldover'):self.rig.assemble(self.rig.baseline)
  finally:self.rig.head.current_oral=oral
 def test_closed_bilabial_hides_all_interior_paint_and_fv_retains_teeth(self):
  from separated_oral_review import inner_oral_coverage
  from cartoon_head import POINTS
  for name,index in [('closed',1),('fv',7),('open',3)]:
   image,row=self.rig.assemble(self.rig.head.weights(np.eye(9)[index]))
   parts=self.rig.last_parts
   if name=='closed':
    for plane in ['Rigid upper incisors','Front dental tongue tip','Narration tongue']:
     self.assertEqual(float(parts[plane][:,:,3].max()),0,name+' '+plane)
   else:self.assertGreater(float(parts['Rigid upper incisors'][:,:,3].sum()),0,name)
  invalid=POINTS['C'].copy();invalid[[17,18]]=invalid[[18,17]]
  with self.assertRaises(ValueError):inner_oral_coverage(invalid)
 def test_carrier_guard_covers_cap_overshoot_without_covering_opening_or_jaw(self):
  from separated_oral_review import upper_lip_carrier_guard
  self.rig.assemble(self.rig.head.weights(np.eye(9)[5]));oral=self.rig.head.current_oral
  carrier=np.full((512,512,4),255,np.float32);face=carrier.copy();carrier[300,300]=[20,30,40,100];guard=upper_lip_carrier_guard(face,oral,carrier)
  x=round(float(oral[28,0]));top=float(oral[28,1])
  self.assertEqual(float(guard[int(top)-3,x,3]),255)
  self.assertEqual(float(guard[int(top)+3,x,3]),0)
  np.testing.assert_array_equal(guard[:310],carrier[:310])
  self.assertEqual(float(guard[370,181,3]),0)
  for index in [5,6]:
   self.rig.assemble(self.rig.head.weights(np.eye(9)[index]));oral=self.rig.head.current_oral
   from separated_oral_review import inner_arch
   upper=inner_arch(oral,True);xs=np.arange(np.ceil(upper[0,0])+2,np.floor(upper[-1,0])-1).astype(int)
   ys=np.floor(np.interp(xs,upper[:,0],upper[:,1])).astype(int)-2
   actual=self.rig.last_parts['Upper lip carrier guard'][ys,xs,3]
   expected=np.floor(self.rig.head.clean_face[ys,xs,3])
   np.testing.assert_array_equal(actual,expected)
  names=list(self.rig.last_parts)
  self.assertLess(names.index('Upper face and cheeks'),names.index('Drawn jaw skin'))
  self.assertGreater(names.index('Upper lip carrier guard'),names.index('Independent upper-lip cap'))
 def test_original_skin_extraction_preserves_color_chin_and_source(self):
  source=self.rig.head.layers['face-skin'];before=source.copy();jaw=original_jaw_skin(source)
  np.testing.assert_array_equal(source,before)
  self.assertEqual(float(jaw[:314,:,3].max()),0)
  self.assertEqual(float(jaw[448:,:,3].max()),0)
  self.assertEqual(float(jaw[:,330:,3].max()),0)
  expected=source.astype('float32').copy();expected[:,:,:3]*=expected[:,:,3:4]/255
  np.testing.assert_array_equal(jaw[335:390,210:250],expected[335:390,210:250])
  np.testing.assert_array_equal(jaw[390:397,215:240],expected[390:397,215:240])
  self.assertGreater(float(jaw[390:397,215:240,3].sum()),0)
 def test_inner_arch_preserves_actual_registered_xy_pairs(self):
  oral=np.arange(96,dtype=np.float32).reshape(48,2)
  np.testing.assert_array_equal(inner_arch(oral),oral[16:25][::-1])
  np.testing.assert_array_equal(inner_arch(oral,True),np.vstack([oral[24:32],oral[16]]))
 def test_rounded_arcs_preserve_corners_x_and_nonoral_controls(self):
  from maxillary_cartoon_head import maxillary_oral_target
  from cartoon_head import POINTS,TRIANGLES,area
  for aperture in [1,5,20,40]:
   oral=maxillary_oral_target(POINTS['C'],aperture)
   for strength in [0,.001,.5,1]:
    result=rounded_oral_arch(oral,aperture,strength)
    np.testing.assert_array_equal(result[:,0],oral[:,0]);np.testing.assert_array_equal(result[32:],oral[32:]);np.testing.assert_allclose(result[[0,8,16,24]],oral[[0,8,16,24]],atol=.00004)
    self.assertGreater(min(area(result,ids) for ids in TRIANGLES if max(ids)<32),0)
  for strength in [-1,1.1,float('nan')]:
   with self.assertRaises(ValueError):rounded_oral_arch(oral,20,strength)
 def test_contact_endpoint_is_fresh_and_continuous(self):
  source=self.rig.lower.source.copy()
  for pair in [(0,1e-7),(1-1e-7,1)]:
   images=[]
   for fv in pair:
    self.rig.head.last_painted_target=np.full((48,2),np.nan);im,row=self.pose(fv);images.append(np.array(im).astype(int));self.assertGreater(row['minimumTriangleArea2'],0);self.assertEqual(len(row['planes']),11);self.assertFalse(row['bakedMouthInUpperCarrier'])
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
  np.testing.assert_array_equal(source,self.rig.lower.source)
 def test_crown_is_clipped_geometrically_and_upper_identity_preserved(self):
  im,row=self.pose(.4);parts=self.rig.last_parts;mask=self.rig.head.review_interior[:,:,0]
  self.assertEqual(float(parts['Rigid upper incisors'][:,:,3][mask==0].max()),0)
  self.assertTrue(row['upper288Exact']);self.assertLessEqual(row['noseMaximumChange'],1)
  self.assertGreater(float(parts['Independent lower lip'][:,:,3].sum()),0)
  self.assertGreater(float(parts['Independent upper-lip cap'][:,:,3].sum()),0)
 def test_nonrounded_capture_does_not_change_original_head_output(self):
  from current_contact_exposure import CurrentContactHead
  original=CurrentContactHead();w=np.eye(9)[3]*.6+np.eye(9)[7]*.4
  np.testing.assert_array_equal(np.array(original.weights(w)),np.array(self.rig.head.weights(w)))
 def test_dental_tip_is_separate_and_crown_material_is_unchanged(self):
  w=np.eye(9)[8]*.7+np.eye(9)[3]*.3
  def pose():return self.rig.assemble(self.rig.head.weights(w))
  pose();crown=self.rig.head.review_teeth.copy();source=self.rig.head.dental_tip.copy()
  try:
   images=[]
   for fraction in [0,1e-7,1-1e-7,1]:
    self.rig.head.dental_fraction=fraction;im,row=pose();images.append(np.array(im).astype(int))
    np.testing.assert_array_equal(crown,self.rig.head.review_teeth)
    self.assertTrue(row['upper288Exact'])
   self.assertGreater(float(self.rig.last_parts['Front dental tongue tip'][:,:,3].sum()),0)
   self.assertLessEqual(int(abs(images[0]-images[1]).max()),2)
   self.assertLessEqual(int(abs(images[2]-images[3]).max()),2)
   np.testing.assert_array_equal(source,self.rig.head.dental_tip)
  finally:self.rig.head.dental_fraction=0

class CornerPhaseTests(unittest.TestCase):
 def setUp(self):
  from audit_separated_geometry import GeometryCapture
  from english_articulation import phone_gestures
  cv2.setNumThreads(1);self.rig=SeparatedOralReview();self.rig.head=GeometryCapture()
  phones=[dict(start=a,end=b,phone=p,value=v,word='test') for a,b,p,v in [(0,.1,'UW','F'),(.1,.3,'M','A'),(.3,.4,'S','B'),(.4,.6,'AO','E')]]
  self.plan=dict(alignment={'status':'acoustic'},words=phones,phonemes=phones,gestures=phone_gestures(phones),audio=dict(step=.01,energy=[.8]*100),fallbackCues=[],silences=[])
 def prior(self,t):
  from separated_oral_review import MaterialCapture
  from audit_separated_geometry import GeometryCaptured
  try:super(MaterialCapture,self.rig.head).at(t,self.plan)
  except GeometryCaptured:pass
  return self.rig.head.current_oral.copy(),self.rig.head.exposure_skin.copy()
 def test_native_corner_reference_and_held_seal(self):
  from audit_separated_geometry import capture
  for t in [.05,.15,.29,.35,.5]:
   oral,_=self.prior(t);np.testing.assert_array_equal(self.rig.head.baseline_corners(t,self.plan),oral[[8,0],0])
  for t in [.15,.2,.28]:
   row=capture(self.rig,t,self.plan);self.assertAlmostEqual(row['width'],69,places=4)
   oral=self.rig.head.current_oral;self.assertLessEqual(float(oral[20,1]-oral[28,1]),.151)
 def test_only_horizontal_oral_controls_change(self):
  from audit_separated_geometry import capture
  oral,skin=self.prior(.35);capture(self.rig,.35,self.plan);new=self.rig.head.current_oral
  self.assertGreater(float(abs(oral[:32,0]-new[:32,0]).max()),1)
  np.testing.assert_array_equal(oral[:,1],new[:,1]);np.testing.assert_array_equal(oral[32:],new[32:]);np.testing.assert_array_equal(skin,self.rig.head.exposure_skin)
 def test_cache_updates_for_in_place_plan_edit_and_cleans_exception_state(self):
  from audit_separated_geometry import capture
  capture(self.rig,.2,self.plan);keys=self.rig.head.corner_keys
  capture(self.rig,.21,self.plan);self.assertIs(keys,self.rig.head.corner_keys)
  self.plan['audio']['energy'][5]=.1;capture(self.rig,.2,self.plan);self.assertIsNot(keys,self.rig.head.corner_keys)
  self.plan['phonemes'][0]['end']=0
  with self.assertRaises(ValueError):capture(self.rig,.2,self.plan)
  self.assertIsNone(self.rig.head.corner_time)
 def test_diphthong_phases_and_rounded_w_have_corner_targets(self):
  from separated_oral_review import phonetic_corner_keys
  p=dict(self.plan,phonemes=[dict(start=0,end=.4,phone='OW',value='E'),dict(start=.4,end=.6,phone='W',value='F')])
  keys=phonetic_corner_keys(p,lambda t:(190,270));np.testing.assert_allclose([t for t,_ in keys[0]],[.1,.3,.5])

if __name__=='__main__':unittest.main()
