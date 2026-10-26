"""Blender MCP local configuration checks; offline and side-effect-free."""
from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from tools import blender_mcp_preflight as p


class BlenderMCPConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in (".codex/config.toml", "integrations/blender-mcp/mcp.json.example"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p.ROOT / relative, target)

    def test_real_repository_codex_and_mcp_json_validate(self):
        self.assertTrue(p.validate(p.ROOT)["validated"])

    def test_fixture_json_and_toml_match(self):
        self.assertTrue(p.validate(self.root)["safe_mode_configured"])

    def test_rejects_missing_safe_mode(self):
        file = self.root / "integrations/blender-mcp/mcp.json.example"
        obj = json.loads(file.read_text())
        obj["mcpServers"]["blender"]["env"]["BLENDER_MCP_SAFE_MODE"] = "0"
        file.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "safe mode"):
            p.validate(self.root)

    def test_rejects_non_local_host(self):
        file = self.root / ".codex/config.toml"
        file.write_text(file.read_text().replace('BLENDER_HOST = "127.0.0.1"',
                                                   'BLENDER_HOST = "0.0.0.0"'))
        with self.assertRaisesRegex(ValueError, "localhost"):
            p.validate(self.root)

    def test_rejects_unpinned_package_and_python(self):
        file = self.root / "integrations/blender-mcp/mcp.json.example"
        obj = json.loads(file.read_text())
        obj["mcpServers"]["blender"]["args"] = ["blender-mcp"]
        file.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "maintained"):
            p.validate(self.root)

    def test_rejects_unapproved_command_or_additional_args(self):
        file = self.root / "integrations/blender-mcp/mcp.json.example"
        obj = json.loads(file.read_text())
        obj["mcpServers"]["blender"]["command"] = "bash"
        file.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "launch uvx"):
            p.validate(self.root)
        obj["mcpServers"]["blender"]["command"] = "uvx"
        obj["mcpServers"]["blender"]["shell"] = True
        file.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "unexpected"):
            p.validate(self.root)

    def test_rejects_missing_file(self):
        (self.root / ".codex/config.toml").unlink()
        with self.assertRaises(FileNotFoundError):
            p.validate(self.root)

    def test_local_tcp_probe_no_blender_handshake_claim(self):
        class Dummy:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        with mock.patch.object(p.socket, "create_connection", return_value=Dummy()) as conn:
            result = p.probe_loopback()
        self.assertTrue(result["tcp_listener"])
        self.assertEqual(result["blender_mcp_handshake"], "unverified")
        conn.assert_called_once_with(("127.0.0.1", 9876), timeout=0.75)

    def test_no_tcp_listener_is_not_misreported_as_blender_failure(self):
        with mock.patch.object(p.socket, "create_connection", side_effect=ConnectionRefusedError):
            result = p.probe_loopback()
        self.assertFalse(result["tcp_listener"])
        self.assertEqual(result["reason"], "ConnectionRefusedError")
        self.assertEqual(result["blender_mcp_handshake"], "unverified")

    def test_port_validation(self):
        for bad in (-1, 0, 65536, True, "9876"):
            with self.subTest(port=bad), self.assertRaises(ValueError):
                p.probe_loopback(bad)

    def test_no_socket_access_during_plain_config_validation(self):
        with mock.patch.object(p.socket, "create_connection", side_effect=AssertionError("network called")):
            self.assertTrue(p.validate(self.root)["validated"])
            self.assertEqual(p.main(["--root", str(self.root)]), 0)

    def test_cli_reports_error_without_starting_server(self):
        path = self.root / ".codex/config.toml"
        path.write_text("[mcp_servers.blender]\ncommand='python'\n")
        self.assertEqual(p.main(["--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
