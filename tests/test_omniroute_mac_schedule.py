"""Offline checks: mutate only the existing service, fail back to STOP."""
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import omniroute_mac_schedule as schedule
from omniroute_mac_once import ensure_stop


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name).resolve();self.path=self.base/'existing.plist'
        self.original={'Label':schedule.LABEL,'ProgramArguments':['old','--approve-model-use'],
                       'EnvironmentVariables':{'PATH':'fixture'},'StartInterval':300}
        self.path.write_bytes(plistlib.dumps(self.original));self.stop=self.base/'STOP'
        self.config=schedule.build_config(self.original,self.base/'python',self.base/'runtime',self.base/'state',self.base/'workspace')

    def test_config_removes_old_model_and_native_flags_preserving_environment(self):
        args=self.config['ProgramArguments']
        self.assertIn('--approve-omniroute-model-use',args)
        for flag in ('--approve-model-use','--allow-native-import','--approve-jane-library-create'):
            self.assertNotIn(flag,args)
        self.assertEqual(self.config['Label'],schedule.LABEL)
        self.assertEqual(self.config['EnvironmentVariables'],self.original['EnvironmentVariables'])
        self.assertEqual(args[args.index('--max-jobs')+1],'1')
        self.assertEqual(self.config['StartInterval'],300)

    def test_failed_bootstrap_or_observation_restores_stop_and_original(self):
        for codes in ([1,0],[0,1,0]):
            with self.subTest(codes=codes):
                run=mock.Mock(side_effect=[subprocess.CompletedProcess([],x) for x in codes])
                with self.assertRaises(ValueError):schedule.activate(self.path,self.config,self.stop,ensure_stop=ensure_stop,run=run)
                self.assertTrue(self.stop.is_file())
                self.assertEqual(plistlib.loads(self.path.read_bytes()),self.original)

    def test_stop_is_present_until_service_is_verified_then_removed(self):
        def run(cmd,**kwargs):
            self.assertTrue(self.stop.is_file())
            return subprocess.CompletedProcess(cmd,0)
        schedule.activate(self.path,self.config,self.stop,ensure_stop=ensure_stop,run=run)
        self.assertFalse(self.stop.exists())
        self.assertEqual(plistlib.loads(self.path.read_bytes()),self.config)
        self.assertEqual(plistlib.loads(self.path.with_name(self.path.name+'.before-omniroute').read_bytes()),self.original)

    def test_refuses_backup_symlink_without_changing_original(self):
        self.path.with_name(self.path.name+'.before-omniroute').symlink_to(self.base/'elsewhere')
        run=mock.Mock()
        with self.assertRaises(ValueError):schedule.activate(self.path,self.config,self.stop,ensure_stop=ensure_stop,run=run)
        run.assert_not_called();self.assertTrue(self.stop.is_file())
        self.assertEqual(plistlib.loads(self.path.read_bytes()),self.original)

    def test_default_never_activates_or_imports_worker(self):
        with mock.patch.object(schedule,'activate') as activate:
            self.assertEqual(schedule.main([]),0)
            activate.assert_not_called()

    def test_pause_requires_positive_service_observation_and_successful_bootout(self):
        for codes in ([113],[0,1]):
            run=mock.Mock(side_effect=[subprocess.CompletedProcess([],x) for x in codes])
            with self.assertRaises(ValueError):schedule.pause_existing_service(run)
        run=mock.Mock(side_effect=[subprocess.CompletedProcess([],0),subprocess.CompletedProcess([],0)])
        schedule.pause_existing_service(run)
        self.assertEqual(run.call_args.args[0],['launchctl','bootout',f'gui/{__import__("os").getuid()}/{schedule.LABEL}'])


if __name__=='__main__':unittest.main()
