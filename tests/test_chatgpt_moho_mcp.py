import base64
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import chatgpt_moho_mcp as bridge
import render_jobs


def file_param(url="https://files.oaiusercontent.com/audio?id=one", **extra):
    return {"download_url": url, "file_id": "file_abcdefgh12345678", "file_name": "narration.mp3", "mime_type": "audio/mpeg", **extra}


class ChatGPTMohoBridge(unittest.TestCase):
    def test_chatgpt_file_schema_matches_file_params_contract(self):
        schema = next(tool for tool in bridge._tool_specs() if tool["name"] == "render_from_mp3")
        self.assertEqual(schema["_meta"]["openai/fileParams"], ["file"])
        ref = schema["inputSchema"]["$defs"]["ChatGPTFile"]
        self.assertEqual(ref["required"], ["download_url", "file_id"])
        self.assertEqual(set(ref["properties"]), {"download_url", "file_id", "mime_type", "file_name"})

    def test_rejects_unapproved_url_hosts_before_network(self):
        with self.assertRaisesRegex(ValueError, "approved ChatGPT file hosts"):
            bridge._check_url("https://127.0.0.1/private.mp3")
        with patch.object(bridge.socket, "getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
            with self.assertRaisesRegex(ValueError, "public IP"):
                bridge._check_url("https://files.oaiusercontent.com/a.mp3")

    def test_rejects_path_names_and_non_audio_mime(self):
        with patch.object(bridge, "_check_url", return_value="https://files.oaiusercontent.com/a"):
            for value in (file_param(file_name="../escape.mp3"), file_param(mime_type="image/png")):
                with self.assertRaises(ValueError):
                    bridge.validate_file_arg(value)

    def test_mp3_is_staged_private_and_worker_command_is_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "jobs"
            adapter = Path(tmp) / "missing-adapter.json"
            def downloader(url, destination):
                destination.write_bytes(b"fake-mp3")
            probe = {"format": {"duration": "4.0"}, "streams": [{"codec_name": "mp3", "codec_type": "audio"}]}
            with patch.object(bridge, "_check_url", return_value="https://files.oaiusercontent.com/a"), \
                 patch.object(bridge, "inspect_setup", return_value={"state": "ready_to_test", "mediaProbeAvailable": True, "mohoCliAvailable": True, "adapterConfigValid": True, "productionBridgeVerified": False, "blockers": []}), \
                 patch.object(render_jobs, "probe", return_value=probe), \
                 patch.object(bridge.subprocess, "Popen") as popen:
                result = bridge.start_render(file_param(), root, adapter, downloader)
            self.assertEqual(result["state"], "queued")
            self.assertEqual(result["durationSeconds"], 4.0)
            job = render_jobs.job(root, result["jobId"])
            self.assertEqual((job / "source.mp3").read_bytes(), b"fake-mp3")
            self.assertEqual((job / "source.mp3").stat().st_mode & 0o777, 0o600)
            self.assertEqual(list((root / ".incoming").glob("upload-*.mp3")), [])
            argv = popen.call_args.args[0]
            self.assertEqual(argv[-2:], ["run", result["jobId"]])
            self.assertNotIn("shell", popen.call_args.kwargs)

    def test_prerequisite_failure_does_not_download_or_retain_mp3(self):
        with tempfile.TemporaryDirectory() as tmp:
            called = []
            blockers = ["media probe unavailable"]
            with patch.object(bridge, "inspect_setup", return_value={"state": "blocked", "blockers": blockers}):
                result = bridge.start_render(file_param(), Path(tmp) / "jobs", Path(tmp) / "adapter.json",
                                             lambda url, destination: called.append(destination))
            self.assertEqual(result["state"], "blocked")
            self.assertEqual(result["jobId"], "")
            self.assertEqual(called, [])
            self.assertFalse((Path(tmp) / "jobs").exists())

    def test_setup_reports_missing_native_frame_checker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            moho = root / "Moho"
            adapter = root / "adapter.json"
            moho.write_text("test executable")
            moho.chmod(0o700)
            adapter.write_text(json.dumps([str(moho)]))
            adapter.chmod(0o600)
            def which(command):
                return "/usr/bin/ffprobe" if command == "ffprobe" else None
            with patch.dict(bridge.os.environ, {"MOHO_EXECUTABLE": str(moho)}), \
                 patch.object(bridge.shutil, "which", side_effect=which):
                result = bridge.inspect_setup(adapter)
            self.assertTrue(result["mediaProbeAvailable"])
            self.assertTrue(result["mohoCliAvailable"])
            self.assertTrue(result["adapterConfigValid"])
            self.assertIn("Black/frozen-frame checks", " ".join(result["blockers"]))

    def test_artifact_is_exposed_only_after_hash_checked_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "a" * 32
            job = root / job_id
            job.mkdir()
            data = b"not a real movie, resource contract fixture"
            media = job / "render.mp4"
            media.write_bytes(data)
            sha = hashlib.sha256(data).hexdigest()
            (job / "status.json").write_text(json.dumps({"state": "review_required", "artifact": {"sha256": sha}}))
            resource = bridge.artifact_resource(root, job_id)
            response = bridge.resource_bytes(root, resource["uri"])
            self.assertEqual(base64.b64decode(response["contents"][0]["blob"]), data)
            self.assertEqual(resource["mimeType"], "video/mp4")
            media.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "checksum"):
                bridge.artifact_resource(root, job_id)

    def test_artifact_tool_returns_resource_link_after_verification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "b" * 32
            job = root / job_id
            job.mkdir()
            media = job / "render.mp4"
            media.write_bytes(b"verified-mp4-resource")
            sha = hashlib.sha256(media.read_bytes()).hexdigest()
            (job / "status.json").write_text(json.dumps({"state": "review_required", "artifact": {"sha256": sha}}))
            reply = bridge.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                                   "params": {"name": "get_render_artifact", "arguments": {"jobId": job_id}}}, root)
            content = reply["result"]["content"]
            link = next(block for block in content if block["type"] == "resource_link")
            self.assertEqual(link["uri"], f"rovor-moho://jobs/{job_id}/render.mp4")
            self.assertEqual(link["mimeType"], "video/mp4")

    def test_stdio_initializes_and_advertises_upload_tool(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        result = subprocess.run([sys.executable, str(ROOT / "tools" / "chatgpt_moho_mcp.py")], input="\n".join(map(json.dumps, messages)) + "\n", capture_output=True, text=True, check=True)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([reply["id"] for reply in replies], [1, 2])
        tools = replies[1]["result"]["tools"]
        self.assertIn("render_from_mp3", [tool["name"] for tool in tools])


if __name__ == "__main__":
    unittest.main()
