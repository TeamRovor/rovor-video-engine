import json, tempfile, unittest, wave
from pathlib import Path
from moho_batch_handoff import validate_manifest,export_bundle,parse_moho_switch,proposed_commands

class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        with wave.open(str(self.root/'evan.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(bytes(32000))
        (self.root/'script.txt').write_text('The Rovor example.')
        self.man={'schemaVersion':1,'fps':24,'productionStatus':'engineering-awaiting-review',
                   'shots':[{'id':'intro','actor':'Evan','audio':'evan.wav','transcript':'script.txt',
                             'estimatedDurationSec':1.,'actions':[{'name':'Action_Point','timeSec':.35}]}]}
        (self.root/'manifest.json').write_text(json.dumps(self.man))
    def tearDown(self):self.tmp.cleanup()
    def test_dry_run_contains_correct_commands_and_no_moho_project(self):
        result=export_bundle(self.root/'manifest.json',self.root/'bundle')
        self.assertFalse(result['productionReady']);self.assertFalse(result['mohoProjectCreated'])
        self.assertEqual(result['batchStatus'],'dry-run-not-executed')
        cmds=json.loads((self.root/'bundle/rhubarb-jobs.json').read_text())
        self.assertEqual(cmds[0]['rhubarb'][1:5],['-f','dat','--datFrameRate','24'])
        self.assertEqual(result['shots'][0]['actions'][0]['frame'],9)
    def test_moho_dat_parses_and_rejects_bad_shape_or_frame_order(self):
        self.assertEqual(parse_moho_switch('MohoSwitch1\n1 X\n10 A\n20 D')[2]['shape'],'D')
        for raw in ('NoHeader\n1 X','MohoSwitch1\n0 X','MohoSwitch1\n1 X\n1 D',
                    'MohoSwitch1\n1 BLERP','MohoSwitch1\n-1 X','MohoSwitch1'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):parse_moho_switch(raw)
    def test_dat_existing_checked_against_wav_duration(self):
        (self.root/'known.dat').write_text('MohoSwitch1\n1 X\n5 B\n24 X\n')
        self.man['shots'][0].update(switchData='known.dat')
        result=validate_manifest(self.man,self.root)
        self.assertEqual(result['shots'][0]['switchCount'],3)
        (self.root/'known.dat').write_text('MohoSwitch1\n1 X\n120 B\n')
        with self.assertRaises(ValueError):validate_manifest(self.man,self.root)
    def test_unknown_action_rejected(self):
        self.man['shots'][0]['actions'][0]['name']='Action_DeleteProject'
        with self.assertRaises(ValueError):validate_manifest(self.man,self.root)
    def test_symlink_escape_and_directory_traversal_rejected(self):
        self.man['shots'][0]['audio']='../outside.wav'
        with self.assertRaises(ValueError):validate_manifest(self.man,self.root)
        self.man['shots'][0]['audio']='evan.wav';self.man['shots'][0]['transcript']='/etc/passwd'
        with self.assertRaises(ValueError):validate_manifest(self.man,self.root)
    def test_repeated_ids_rejected(self):
        self.man['shots'].append(dict(self.man['shots'][0]))
        with self.assertRaises(ValueError):validate_manifest(self.man,self.root)

if __name__=='__main__': unittest.main()