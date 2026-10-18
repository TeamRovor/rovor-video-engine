import unittest
from contact_audit import P,Pose,audit_contact_track,ContactError
class ContactTests(unittest.TestCase):
 def original(self):
  return [Pose(i,P(220,468),P(255,565),P(169,627),P(169,635),P(169,636)) for i in (8688,8698,8708)]
 def test_valid_shared_anchors(self):self.assertTrue(audit_contact_track(self.original())['structural_contact_valid'])
 def test_artist_approval_not_inferred(self):self.assertIs(audit_contact_track(self.original())['artist_approved'],False)
 def test_reject_detached_hand(self):
  a=self.original();a[1]=Pose(8698,P(220,468),P(255,565),P(169,627),P(250,650),P(250,650))
  with self.assertRaisesRegex(ContactError,'detached hand'):audit_contact_track(a)
 def test_reject_floating_tool(self):
  a=self.original();a[1]=Pose(8698,P(220,468),P(255,565),P(169,627),P(169,635),P(300,300))
  with self.assertRaisesRegex(ContactError,'tool floats'):audit_contact_track(a)
 def test_reject_stretched_elbow(self):
  a=self.original();a[1]=Pose(8698,P(220,468),P(455,265),P(169,627),P(169,635))
  with self.assertRaises(ContactError):audit_contact_track(a)
 def test_reject_missing_frames(self):
  a=self.original();a[1]=Pose(9000,P(220,468),P(255,565),P(169,627),P(169,635))
  with self.assertRaises(ContactError):audit_contact_track(a)
 def test_reject_duplicate_frame(self):
  a=self.original();a[1]=a[0]
  with self.assertRaises(ContactError):audit_contact_track(a)
 def test_reject_nonfinite_joint(self):
  with self.assertRaises(ContactError):P(float('nan'),0)
 def test_reject_missing_pose(self):
  with self.assertRaises(ContactError):audit_contact_track([])
 def test_reject_invented_strings(self):
  with self.assertRaises(ContactError):audit_contact_track(['looks physically attached'])
if __name__=='__main__':unittest.main(verbosity=2)