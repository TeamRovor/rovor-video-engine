"""Offline, no-Mac/launchctl/Keychain tests for opt-in user LaunchAgent."""
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import rovor_private_supervisor as sup


class PrivateSupervisorTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        (self.home/'Documents'/'Rovor').mkdir(parents=True)
        (self.home/'Library'/'Application Support').mkdir(parents=True)
        (self.home/'Library'/'LaunchAgents').mkdir()
        source=self.home/'reviewed-source'
        source.mkdir()
        for name in sup.RUNTIME_FILES:
            (source/name).write_text('## synthetic trusted fixture: '+name+'\n')
        self.script=source/'rovor_private_supervisor.py'
        self.python=self.home/'safe-python'
        self.python.write_text('#!dummy executable fixture\n')
        self.repo='TeamRovor/rovors-private-control'
        self.issue=7

    def staged(self):
        with mock.patch.object(sup.sys,'platform','darwin'):
            return sup.stage(self.home,self.repo,self.issue,
                             script=self.script,python=self.python)

    def test_no_auto_install_when_module_imported_or_status_read(self):
        with mock.patch.object(sup.sys,'platform','linux'):
            out=sup.status(self.home)
        self.assertFalse(out['staged'])
        self.assertFalse(out['launchd_loaded'])
        self.assertFalse(out['token_inspected'])
        self.assertFalse((self.home/'Library'/'Application Support'/sup.APP_FOLDER).exists())

    def test_staging_creates_plist_with_exact_argv_no_secrets_and_does_not_load(self):
        with mock.patch.object(sup,'launchctl') as actuator:
            result=self.staged()
        actuator.assert_not_called()
        self.assertEqual(result['status'],'staged_not_running')
        service,plist,conf=sup._check_stage(self.home)
        obj=plistlib.loads(plist.read_bytes())
        self.assertEqual(obj['Label'],sup.LABEL)
        self.assertEqual(obj['ProgramArguments'],
                         [str(self.python),
                          str(service/sup.RUNTIME_DIR/sup.RUNTIME_FILES[0]),
                          '--tick'])
        self.assertEqual(conf['schema'],2)
        self.assertEqual(set(conf['runtime_sha256']),set(sup.RUNTIME_FILES))
        for name in sup.RUNTIME_FILES:
            frozen=service/sup.RUNTIME_DIR/name
            self.assertEqual(frozen.read_bytes(),(self.script.parent/name).read_bytes())
            self.assertEqual(frozen.stat().st_mode&0o777,0o600)
        self.assertTrue(obj['RunAtLoad'])
        self.assertEqual(obj['StartInterval'],300)
        self.assertNotIn('KeepAlive',obj)
        raw=plist.read_text()
        self.assertNotIn('token',raw.lower())
        self.assertNotIn('private_repo',raw)
        self.assertNotIn(self.repo,raw)
        self.assertEqual(service.stat().st_mode&0o777,0o700)
        self.assertEqual((service/sup.CONFIG_FILE).stat().st_mode&0o777,0o600)
        self.assertEqual(plist.stat().st_mode&0o777,0o600)

    def test_staging_never_overwrites_an_existing_agent_or_configuration(self):
        self.staged()
        with mock.patch.object(sup.sys,'platform','darwin'):
            with self.assertRaisesRegex(sup.Refused,'Existing LaunchAgent'):
                sup.stage(self.home,self.repo,self.issue,
                          script=self.script,python=self.python)
        self.assertEqual(sup._check_stage(self.home)[2]['receipt_issue'],self.issue)

    def test_stage_does_not_allow_public_github_repo(self):
        with mock.patch.object(sup.sys,'platform','darwin'):
            with self.assertRaises(sup.Refused):
                sup.stage(self.home,'TeamRovor/rovor-video-engine',self.issue,
                          script=self.script,python=self.python)
        self.assertFalse((self.home/'Library'/'Application Support'/sup.APP_FOLDER).exists())

    def test_staging_refuses_non_mac_host(self):
        with mock.patch.object(sup.sys,'platform','linux'):
            with self.assertRaisesRegex(sup.Refused,'Mac user session'):
                sup.stage(self.home,self.repo,self.issue,
                          script=self.script,python=self.python)

    def test_staging_rejects_symlinked_launch_agents_folder(self):
        (self.home/'Library'/'LaunchAgents').rmdir()
        outside=self.home/'outside'
        outside.mkdir()
        (self.home/'Library'/'LaunchAgents').symlink_to(outside,target_is_directory=True)
        with mock.patch.object(sup.sys,'platform','darwin'):
            with self.assertRaisesRegex(sup.Refused,'Unsafe LaunchAgent parent'):
                sup.stage(self.home,self.repo,self.issue,
                          script=self.script,python=self.python)
        self.assertEqual(list(outside.iterdir()),[])

    def test_git_checkout_modification_does_not_change_frozen_runtime(self):
        self.staged()
        service, plist, config = sup._check_stage(self.home)
        original = (service/sup.RUNTIME_DIR/sup.RUNTIME_FILES[0]).read_bytes()
        self.script.write_text('## mutated Git checkout after stage\n')
        _service, _plist, verified = sup._check_stage(self.home)
        self.assertEqual((service/sup.RUNTIME_DIR/sup.RUNTIME_FILES[0]).read_bytes(),
                         original)
        self.assertEqual(verified['script_path'],
                         str(service/sup.RUNTIME_DIR/sup.RUNTIME_FILES[0]))
        self.assertNotEqual(original,self.script.read_bytes())

    def test_frozen_dependency_edit_blocks_native_service_tick(self):
        self.staged()
        service,plist,config=sup._check_stage(self.home)
        frozen=service/sup.RUNTIME_DIR/'ghost_private_control.py'
        frozen.write_bytes(b'# swapped after approval\n')
        with self.assertRaisesRegex(sup.Refused,
                                    'snapshot differs from reviewed code'):
            sup._check_stage(self.home)
        with mock.patch.object(sup.sys,'platform','darwin'):
            with mock.patch.object(sup.poller,'poll') as agent:
                with self.assertRaisesRegex(sup.Refused,
                                            'snapshot differs from reviewed code'):
                    sup.tick(self.home,key_lookup=lambda:'test-private-token')
            agent.assert_not_called()

    def test_snapshot_redirect_and_unknown_runtime_path_refused(self):
        self.staged()
        service,plist,config=sup._check_stage(self.home)
        frozen=service/sup.RUNTIME_DIR/'ghost_worker.py'
        copied=frozen.read_bytes()
        frozen.unlink()
        frozen.symlink_to(self.script)
        with self.assertRaises(sup.Refused):sup._check_stage(self.home)
        frozen.unlink()
        frozen.write_bytes(copied)
        frozen.chmod(0o600)
        cfg=service/sup.CONFIG_FILE
        data=json.loads(cfg.read_text())
        data['script_path']='/Users/someone/Downloads/untrusted.py'
        cfg.write_text(json.dumps(data))
        with self.assertRaisesRegex(sup.Refused,
                                    'Runtime script must be isolated'):
            sup._check_stage(self.home)

    def test_tampered_plist_stops_action(self):
        self.staged()
        _service,plist,_config=sup._check_stage(self.home)
        tampered=plistlib.loads(plist.read_bytes())
        tampered['ProgramArguments']=['/bin/sh','-c','arbitrary code']
        plist.write_bytes(plistlib.dumps(tampered))
        with self.assertRaisesRegex(sup.Refused,'differs'):
            sup._check_stage(self.home)

    def test_broad_file_permissions_refused_before_launch(self):
        self.staged()
        service,plist,conf=sup._check_stage(self.home)
        plist.chmod(0o644)
        with self.assertRaisesRegex(sup.Refused,'permissions too broad'):
            sup._check_stage(self.home)
        plist.chmod(0o600)
        (service/sup.CONFIG_FILE).chmod(0o644)
        with self.assertRaisesRegex(sup.Refused,'permissions too broad'):
            sup._check_stage(self.home)

    def test_fake_private_queue_tick_only_exact_safe_limits(self):
        self.staged()
        calls=[]
        def fake_poll(repo,token,home,issue,**kwargs):
            calls.append((repo,token,home,issue,kwargs))
            return {'queue_polls':1,'jobs_checked':1,
                    'jobs_succeeded':1,'stop_reason':'max_jobs'}
        with mock.patch.object(sup.sys,'platform','darwin'):
            result=sup.tick(self.home,poll=fake_poll,key_lookup=lambda:'secret-key')
        self.assertEqual(result['status'],'private_queue_tick_completed')
        self.assertEqual(result['jobs_checked'],1)
        self.assertTrue(result['native_gui_control_verified'] is False)
        self.assertFalse(result['ai_model_called'])
        self.assertEqual(calls[0][:4],(self.repo,'secret-key',self.home,self.issue))
        opts=calls[0][4]
        self.assertEqual(opts['max_jobs'],1)
        self.assertLessEqual(opts['max_seconds'],180)
        self.assertFalse(opts['allow_inventory'])
        self.assertNotIn('secret-key',json.dumps(result))

    def test_tick_refuses_missing_key_and_never_calls_queue(self):
        self.staged()
        with mock.patch.object(sup.sys,'platform','darwin'):
            with mock.patch.object(sup.poller,'poll') as actual:
                with self.assertRaisesRegex(sup.Refused,'credential missing'):
                    sup.tick(self.home,key_lookup=lambda:'')
        actual.assert_not_called()

    def test_keychain_retrieval_is_local_and_not_saved(self):
        def lookup(cmd,**kwargs):
            self.assertEqual(cmd[0],'/usr/bin/security')
            self.assertEqual(cmd[1:3],['find-generic-password','-s'])
            self.assertIn(sup.KEYCHAIN_SERVICE,cmd)
            return subprocess.CompletedProcess(cmd,0,stdout='example-private-token\n',stderr='')
        with mock.patch.object(sup.sys,'platform','darwin'):
            self.assertEqual(sup.keychain_token(run=lookup),'example-private-token')
        self.assertFalse((self.home/'Library'/'Application Support'/sup.APP_FOLDER).exists())

    def test_keychain_missing_credentials_fail_without_payload_leak(self):
        def bad(cmd,**kwargs):
            return subprocess.CompletedProcess(cmd,1,stdout='SECRET ON ERROR',stderr='')
        with mock.patch.object(sup.sys,'platform','darwin'):
            with self.assertRaisesRegex(sup.Refused,'No valid private control credential'):
                sup.keychain_token(run=bad)

    def test_exact_activation_argv_and_no_shell(self):
        self.staged()
        commands=[]
        def fake(cmd,**kwargs):
            commands.append(cmd)
            return subprocess.CompletedProcess(cmd,0,stdout='',stderr='')
        with mock.patch.object(sup.sys,'platform','darwin'):
            a=sup.launchctl(self.home,'activate',run=fake)
            d=sup.launchctl(self.home,'deactivate',run=fake)
        self.assertEqual(a['status'],'activation_dispatched_not_verified')
        self.assertEqual(d['status'],'deactivation_dispatched_not_verified')
        self.assertEqual(commands[0][:2],['/bin/launchctl','bootstrap'])
        self.assertEqual(commands[1][:2],['/bin/launchctl','bootout'])
        self.assertNotIn('/bin/sh',str(commands))

    def test_activation_requires_explicit_confirmation(self):
        with mock.patch.object(sup,'launchctl') as actuator:
            with redirect_stderr(io.StringIO()):
                out=sup.main(['--activate'])
        self.assertEqual(out,2)
        actuator.assert_not_called()

    def test_status_reads_launchd_boolean_never_raw_output(self):
        self.staged()
        def fake(cmd,**kwargs):
            return subprocess.CompletedProcess(cmd,0,stdout='PRIVATE DETAILS',stderr='')
        with mock.patch.object(sup.sys,'platform','darwin'):
            out=sup.status(self.home,run=fake)
        self.assertTrue(out['staged'])
        self.assertTrue(out['launchd_loaded'])
        self.assertNotIn('PRIVATE DETAILS',json.dumps(out))
        self.assertFalse(out['private_queue_job_ever_executed_verified'])

    def test_gui_service_not_loaded_when_status_command_fails(self):
        self.staged()
        def fail(cmd,**kwargs):
            return subprocess.CompletedProcess(cmd,1,stdout='',stderr='PRIVATE TOKEN')
        with mock.patch.object(sup.sys,'platform','darwin'):
            result=sup.status(self.home,run=fail)
        self.assertFalse(result['launchd_loaded'])

    def test_config_symlink_and_private_repo_identity_refused(self):
        self.staged()
        service,plist,config=sup._check_stage(self.home)
        cfg=service/sup.CONFIG_FILE
        text=cfg.read_text()
        cfg.unlink()
        cfg.symlink_to(self.home/'nope')
        with self.assertRaises(sup.Refused):
            sup._check_stage(self.home)
        cfg.unlink()
        cfg.write_text(text)
        cfg.chmod(0o600)
        changed=json.loads(text)
        changed['private_repo']='TeamRovor/rovor-video-engine'
        cfg.write_text(json.dumps(changed))
        with self.assertRaisesRegex(sup.Refused,'Unsafe private repository'):
            sup._check_stage(self.home)


if __name__=="__main__":
    unittest.main()
