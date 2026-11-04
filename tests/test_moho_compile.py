import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import moho_compile as m

def fixture():
    channel = {'type':'Val','ref':False,'mute':False,'when':[0,10], 'val':[1.5,2.0], 'interp':[{'im':1},{'im':1}]}
    switch = dict(copy.deepcopy(channel),type='String',val=['Rest','AI'])
    return {'mime_type':'application/x-vnd.lm_mohodoc','version':1038,
            'project_data':{'fps':60,'start_frame':1,'end_frame':60},
            'artwork':{'untouched':[1,2,3]},
            'layers':[{'uuid':'rig','name':'Rig','type':'BoneLayer','skeleton':{'bones':[{'name':'jaw','anim_angle':channel}]},'layers':[
              {'uuid':'mouth','name':'Mouth','type':'SwitchLayer','switch_interpolation':False,'switch_keys':switch,
               'layers':[{'uuid':'rest','name':'Rest'},{'uuid':'ai','name':'AI'}]}]}]}

def plan():
    return {'fps':60,'sourceSha256':'placeholder','replaceTargetAnimation':True,
            'patches':[{'layerUuid':'rig','bone':'jaw','channel':'anim_angle','keys':[{'frame':1,'value':1.5},{'frame':60,'value':1.7}]}]}

class Compiler(unittest.TestCase):
    def test_observed_schema_versions_share_target_channel_contract(self):
        for version in (1038, 1045):
            source=fixture();source['version']=version
            result=m.compile_doc(source,plan())
            self.assertEqual(result['version'],version)
        source=fixture();source['version']=1046
        with self.assertRaises(ValueError):m.compile_doc(source,plan())

    def test_only_target_changes_and_zero_preserved(self):
        source=fixture(); result=m.compile_doc(source,plan())
        expected=copy.deepcopy(source)
        c=expected['layers'][0]['skeleton']['bones'][0]['anim_angle']
        c.update(when=[0,1,60],val=[1.5,1.5,1.7],interp=[{'im':1}]*3)
        self.assertEqual(result,expected); self.assertEqual(source,fixture())
    def test_frame_sampling(self):
        self.assertEqual(m.frame('0'),1)
        self.assertEqual(m.frame('0.5'),31)
        self.assertEqual(m.frame('0.50001'),32)
        self.assertEqual(m.frame('0.016666666666666666'),2)
    def test_reject_non60_source(self):
        d=fixture();d['project_data']['fps']=24
        with self.assertRaises(ValueError):m.compile_doc(d,plan())
    def test_reject_setup_write_duplicate_and_nonfinite(self):
        for keys in ([{'frame':0,'value':2}], [{'frame':1,'value':2}]*2, [{'frame':1,'value':float('nan')}], [{'frame':61,'value':2}]):
            p=plan();p['patches'][0]['keys']=keys
            with self.assertRaises(ValueError):m.compile_doc(fixture(),p)
    def test_reject_unknown_and_ambiguous_bones(self):
        d=fixture();d['layers'][0]['skeleton']['bones']*=2
        with self.assertRaises(ValueError):m.compile_doc(d,plan())
        p=plan();p['patches'][0]['bone']='invented'
        with self.assertRaises(ValueError):m.compile_doc(fixture(),p)
    def test_switch_must_exist(self):
        p=plan();p['patches']=[{'layerUuid':'mouth','channel':'switch_keys','keys':[{'frame':1,'value':'AI'}]}]
        result=m.compile_doc(fixture(),p)
        self.assertEqual(result['layers'][0]['layers'][0]['switch_keys']['val'],['Rest','AI'])
        p['patches'][0]['keys'][0]['value']='missing'
        with self.assertRaises(ValueError):m.compile_doc(fixture(),p)
    def test_archive_preserves_source_other_members_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source.moho';dst=Path(t)/'new.moho'
            with zipfile.ZipFile(src,'w') as z:
                z.writestr(m.PAYLOAD,json.dumps(fixture()));z.writestr('artwork.bin',b'original-art');z.comment=b'preserve'
            original=src.read_bytes();p=plan();p['sourceSha256']=m.sha(original)
            m.compile_archive(src,dst,p)
            self.assertEqual(src.read_bytes(),original)
            with zipfile.ZipFile(dst) as z:self.assertEqual(z.read('artwork.bin'),b'original-art');self.assertEqual(z.comment,b'preserve')
            with self.assertRaises(FileExistsError):m.compile_archive(src,dst,p)
            p['sourceSha256']='wrong'
            with self.assertRaises(ValueError):m.compile_archive(src,Path(t)/'wrong.moho',p)
    def test_json_duplicate_and_nan_rejected(self):
        for payload in ['{"x":1,"x":2}','{"x":NaN}']:
            with self.assertRaises(ValueError):m.decode(payload)
    def test_speech_requires_acoustic_alignment(self):
        with self.assertRaises(ValueError):m.speech_keys({},1,{'M':'AI'},'Rest')
    def test_acoustic_frames_and_rest(self):
        speech={'alignment':{'status':'acoustic','wordCoverage':1.0},'script':'me',
            'words':[{'word':'me','scriptIndex':0,'start':0.1,'end':0.5}],
            'phonemes':[{'phone':'M','value':'A','word':'me','scriptIndex':0,'start':0.1,'end':0.2},
                        {'phone':'IY','value':'B','word':'me','scriptIndex':0,'start':0.2,'end':0.5}]}
        self.assertEqual(m.speech_keys(speech,1,{'M':'Closed','IY':'E'},'Rest'),[
            {'frame':1,'value':'Rest'},{'frame':7,'value':'Closed'},{'frame':13,'value':'E'},{'frame':31,'value':'Rest'}])

if __name__=='__main__':unittest.main()
