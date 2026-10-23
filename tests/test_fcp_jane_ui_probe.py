"""Test read-only FCP GUI classification / default library timestamps without app."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import fcp_jane_ui_probe as ui
import fcp_jane_native_probe as native


class WindowProbeTests(unittest.TestCase):
    def test_title_categories_privacy_and_sheets(self):
        result=ui.classify_window_titles(
            'APP_RUNNING\nWINDOW_COUNT|2\n'
            'WINDOW|1|Choose Library\n'
            'WINDOW|0|Personal Client 938328\n')
        self.assertEqual(result['ui_status'],'read_only_window_inspection')
        self.assertEqual(result['sheets_observed'],1)
        self.assertTrue(result['window_title_category_flags']['library_picker'])
        self.assertFalse(result['window_title_category_flags']['error_dialog'])
        self.assertNotIn('938328',str(result))
        self.assertTrue(result['ui_buttons_clicked'] is False)

    def test_reject_incorrect_gui_output_without_leaking_names(self):
        cases=[
            'APP_NOT_RUNNING',
            'APP_RUNNING\nWINDOW_COUNT|101',
            'APP_RUNNING\nWINDOW|1|Invalid XML',
            'error',
            'APP_RUNNING\nWINDOW|n|Secret',
        ]
        expected=[
            'app_not_running',
            'window_count_outside_limit',
            'read_only_window_inspection',
            'unexpected_reply',
            'unexpected_reply',
        ]
        for c,e in zip(cases,expected):
            got=ui.classify_window_titles(c)
            self.assertEqual(got['ui_status'],e)

    def test_apple_event_never_opens_or_clicks(self):
        cmds=[]
        def safe_run(command, **kwargs):
            cmds.append(command)
            self.assertEqual(command[:2],
                             ['/usr/bin/osascript','-e'])
            self.assertIn('every window',command[2])
            self.assertNotIn('click ',command[2])
            self.assertNotIn('open POSIX file',command[2])
            self.assertNotIn('activate',command[2])
            return subprocess.CompletedProcess(command,0,
               stdout='APP_RUNNING\nWINDOW_COUNT|1\nWINDOW|1|Import XML\n',
               stderr='')
        result=ui.gui_status(run=safe_run)
        self.assertEqual(result['sheets_observed'],1)
        self.assertTrue(result['window_title_category_flags']['import_dialog'])
        self.assertEqual(len(cmds),1)

    def test_denied_access_does_not_fake_native_success(self):
        def denied(cmd, **kwargs):
            return subprocess.CompletedProcess(
                cmd,1,stdout='',stderr='osascript is not allowed assistive access')
        r=ui.gui_status(run=denied)
        self.assertEqual(r['ui_status'],'accessibility_or_automation_denied')
        self.assertFalse(r['native_timeline_verified'])

    def test_timeout_fails_closed(self):
        def timeout(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd,kwargs['timeout'])
        r=ui.gui_status(run=timeout)
        self.assertEqual(r['ui_status'],'ui_query_timed_out')

    def test_status_avoids_library_package_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            root=home/'Documents'/'Rovor'
            root.mkdir(parents=True)
            job=root/'fcp-jane-auto-20261022-183007'
            job.mkdir()
            target=job/'ROVOR-Jane-Test.fcpbundle'
            (job/native.RECEIPT_NAME).write_text(json.dumps({
                'status':'native_library_not_observed',
                'target_library':str(target),
                'apple_event_sent':True,
                'last_dispatched':'landscape'
            }))
            (home/'Movies').mkdir()
            untitled=home/'Movies'/'Untitled.fcpbundle'
            untitled.mkdir()
            (untitled/'SECRET-PERSONAL-CLIENT-FILE').write_text('untouched')
            for label in ('landscape','portrait'):
                xml=ET.Element('fcpxml',version='1.13')
                io=ET.SubElement(xml,'import-options')
                ET.SubElement(io,'option',key='library location',
                              value=target.as_uri())
                res=ET.SubElement(xml,'resources')
                ET.SubElement(res,'format',frameDuration='1/60s')
                lib=ET.SubElement(xml,'library')
                event=ET.SubElement(lib,'event')
                proj=ET.SubElement(event,'project')
                ET.SubElement(proj,'sequence',duration='30s')
                ET.ElementTree(xml).write(job/(label+'-auto.fcpxml'))
            def fake_ps(cmd, **kw):
                self.assertEqual(cmd,['/bin/ps','-axo','comm='])
                return subprocess.CompletedProcess(cmd,0,stdout=
                    '/Applications/Final Cut Pro.app/Contents/MacOS/Final Cut Pro\n',stderr='')
            r=ui.analyze(root,job,home=home,run=fake_ps,with_ui=False)
            md=r['default_untitled_library_metadata']
            self.assertTrue(md['exists'])
            self.assertFalse(md['attributed_to_jane'])
            self.assertFalse(md['library_package_contents_examined'])
            self.assertFalse(r['native_timeline_verified'])
            self.assertFalse(r['portrait_dispatched'])
            self.assertNotIn('SECRET-PERSONAL',str(r))
            self.assertEqual(r['ui']['ui_status'],'skipped')


if __name__=='__main__':
    unittest.main()
