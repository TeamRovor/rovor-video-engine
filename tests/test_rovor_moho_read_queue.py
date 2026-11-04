"""Offline request parsing only; never start the bridge or send an issue comment."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'rovor_moho_read_queue', ROOT / '.github/scripts/rovor_moho_read_queue.py')
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


class ReadQueueBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        old = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, old)
        self.path = Path('rovor-production/moho-queue/read-offline.json')
        self.path.parent.mkdir(parents=True)
        env = mock.patch.dict(os.environ, {'ROVOR_REQUEST_PATH': str(self.path)})
        env.start()
        self.addCleanup(env.stop)
        self.plan = {'task_id': 'offline-read', 'commands': [
            {'name': 'document_getInfo', 'arguments': {}}]}

    def write_plan(self):
        self.path.write_text(json.dumps(self.plan), encoding='utf-8')

    def test_valid_one_and_two_read_commands_still_parse(self):
        for count in (1, 2):
            with self.subTest(count=count):
                self.plan['commands'] = [
                    {'name': name, 'arguments': {}}
                    for name in ('document_getInfo', 'document_getLayers')[:count]]
                self.write_plan()
                with mock.patch.object(client.subprocess, 'Popen') as process:
                    with mock.patch.object(client.urllib.request, 'urlopen') as network:
                        self.assertEqual(client.load_plan(), self.plan)
                process.assert_not_called()
                network.assert_not_called()

    def test_exact_byte_limit_is_accepted(self):
        raw = json.dumps(self.plan).encode('utf-8')
        self.path.write_bytes(b' ' * (client.MAX_REQUEST_BYTES - len(raw)) + raw)
        self.assertEqual(client.load_plan(), self.plan)

    def test_one_byte_over_limit_is_rejected_before_json_parse(self):
        raw = json.dumps(self.plan).encode('utf-8')
        self.path.write_bytes(b' ' * (client.MAX_REQUEST_BYTES + 1 - len(raw)) + raw)
        with mock.patch.object(client.json, 'loads', side_effect=AssertionError('Must reject before parsing')):
            with self.assertRaisesRegex(RuntimeError, 'exceeds byte limit'):
                client.load_plan()

    def test_budget_counts_bytes_before_unicode_decode(self):
        self.path.write_bytes(('é' * client.MAX_REQUEST_BYTES).encode('utf-8'))
        with self.assertRaisesRegex(RuntimeError, 'exceeds byte limit'):
            client.load_plan()

    def test_non_read_commands_and_arguments_remain_rejected(self):
        for command in ({'name': 'document_save', 'arguments': {}},
                        {'name': 'document_getInfo', 'arguments': {'path': 'other'}}):
            with self.subTest(command=command):
                self.plan['commands'] = [command]
                self.write_plan()
                with self.assertRaisesRegex(RuntimeError, 'Non-read command'):
                    client.load_plan()

    def test_unapproved_path_remains_rejected(self):
        self.write_plan()
        with mock.patch.dict(os.environ, {'ROVOR_REQUEST_PATH': '../read-other.json'}):
            with self.assertRaisesRegex(RuntimeError, 'unapproved'):
                client.load_plan()


if __name__ == '__main__':
    unittest.main()
