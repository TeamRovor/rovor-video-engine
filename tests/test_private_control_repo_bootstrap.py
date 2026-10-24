"""All network and authentication are mocked; no repository creation from CI."""
import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import private_control_repo_bootstrap as b


class FakeGitHub:
    def __init__(self, existing=False, public=False, branch="main", owner_type="User",
                 authenticated_as="TeamRovor"):
        self.existing, self.public = existing, public
        self.branch, self.owner_type = branch, owner_type
        self.authenticated_as = authenticated_as
        self.issue = None
        self.files = {}
        self.calls = []

    def metadata(self):
        return {"full_name": b.REPO, "private": not self.public,
                "archived": False, "disabled": False, "default_branch": self.branch,
                "has_issues": True}

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, body))
        prefix = "/repos/" + b.REPO
        if method == "GET" and path == prefix:
            return (200, self.metadata()) if self.existing else (404, None)
        if method == "GET" and path == "/repos/" + b.PUBLIC:
            return 200, {"owner": {"type": self.owner_type}}
        if method == "GET" and path == "/user":
            return 200, {"login": self.authenticated_as}
        if method == "POST" and path in ("/user/repos", "/orgs/TeamRovor/repos"):
            self.existing = True
            self.public = not body["private"]
            return 201, self.metadata()
        if method == "GET" and path == prefix + "/issues?state=all&per_page=100":
            return 200, [] if self.issue is None else [self.issue]
        if method == "POST" and path == prefix + "/issues":
            self.issue = {"number": 7, "state": "open", "title": body["title"]}
            return 201, self.issue
        if path.startswith(prefix + "/contents/"):
            key = path.split("/contents/", 1)[1].split("?", 1)[0]
            if method == "GET":
                if key not in self.files:
                    return 404, None
                raw = json.dumps(self.files[key]).encode()
                return 200, {"type": "file", "encoding": "base64",
                             "content": base64.b64encode(raw).decode()}
            if method == "PUT":
                if key in self.files:
                    self.fail("Unexpected overwrite")
                self.files[key] = json.loads(base64.b64decode(body["content"]))
                return 201, {"content": {"sha": "test-sha"}}
        raise AssertionError("Unexpected request " + method + " " + path)


class PrivateBootstrapTests(unittest.TestCase):
    def test_preflight_no_private_repo_never_writes(self):
        api = FakeGitHub()
        result = b.bootstrap(api)
        self.assertFalse(result["private_repo_verified"])
        self.assertFalse(any(m != "GET" for m, _, _ in api.calls))
        self.assertFalse(result["mac_command_executed"])

    def test_apply_creates_private_repo_ping_issue_and_queue(self):
        api = FakeGitHub()
        out = b.bootstrap(api, apply=True)
        self.assertTrue(out["private_repo_verified"])
        self.assertEqual(out["private_receipt_issue_number"], 7)
        self.assertTrue(out["queue_ready"])
        self.assertFalse(out["supervisor_activated"])
        self.assertFalse(out["remote_terminal_control_verified"])
        self.assertEqual(api.files[b.JOB_PATH], b.PING)
        self.assertEqual(api.files[b.QUEUE_PATH], b.QUEUE)
        writes = [(m,p) for m,p,_ in api.calls if m in ("POST","PUT")]
        self.assertEqual(writes[0], ("POST", "/user/repos"))
        self.assertEqual(writes[1], ("POST", "/repos/" + b.REPO + "/issues"))
        self.assertLess(writes.index(("PUT", "/repos/" + b.REPO + "/contents/" + b.JOB_PATH)),
                        writes.index(("PUT", "/repos/" + b.REPO + "/contents/" + b.QUEUE_PATH)))

    def test_idempotent_rerun_no_extra_writes(self):
        api = FakeGitHub()
        b.bootstrap(api, apply=True)
        api.calls.clear()
        b.bootstrap(api, apply=True)
        self.assertTrue(all(method == "GET" for method,_,_ in api.calls))

    def test_public_repository_refused_without_writes(self):
        api = FakeGitHub(existing=True, public=True)
        with self.assertRaisesRegex(b.Refused, "private_repository_not_ready"):
            b.bootstrap(api, apply=True)
        self.assertTrue(all(m == "GET" for m,_,_ in api.calls))

    def test_wrong_authenticated_person_refused(self):
        api = FakeGitHub(authenticated_as="not-TeamRovor")
        with self.assertRaisesRegex(b.Refused, "authenticate_as_teamrovor_first"):
            b.bootstrap(api, apply=True)
        self.assertFalse(any(m != "GET" for m,_,_ in api.calls))

    def test_org_owner_uses_org_create(self):
        api = FakeGitHub(owner_type="Organization")
        b.bootstrap(api, apply=True)
        self.assertIn(("POST", "/orgs/TeamRovor/repos"),
                      [(m,p) for m,p,_ in api.calls])

    def test_existing_repo_on_different_default_branch_fails(self):
        api = FakeGitHub(existing=True, branch="master")
        with self.assertRaisesRegex(b.Refused, "private_repository_not_ready"):
            b.bootstrap(api, apply=True)

    def test_conflicting_existing_queue_refused_not_overwritten(self):
        api = FakeGitHub()
        b.bootstrap(api, apply=True)
        api.files[b.QUEUE_PATH] = {"schema": 1, "jobs": ["other-private-job"]}
        api.calls.clear()
        with self.assertRaisesRegex(b.Refused, "existing_control_file_conflict"):
            b.bootstrap(api, apply=True)
        self.assertFalse(any(m in ("PUT", "POST") for m,_,_ in api.calls))

    def test_closed_issue_refused_no_duplicate(self):
        api = FakeGitHub(existing=True)
        api.issue = {"title": b.ISSUE_TITLE, "number": 7, "state": "closed"}
        with self.assertRaisesRegex(b.Refused, "receipt_issue_closed_or_invalid"):
            b.bootstrap(api, apply=True)
        self.assertFalse(any(m != "GET" for m,_,_ in api.calls))

    def test_no_token_printed_on_gh_failure(self):
        class Result:
            returncode = 1
            stdout = "secret-token"
        with self.assertRaisesRegex(b.Refused, "github_cli_auth_unavailable"):
            b.load_local_gh_token(run=lambda *a,**kw: Result())

    def test_existing_files_preflight_no_writes(self):
        api = FakeGitHub()
        b.bootstrap(api, apply=True)
        api.calls.clear()
        out = b.bootstrap(api, apply=False)
        self.assertTrue(out["receipt_issue_ready"])
        self.assertTrue(out["ping_packet_ready"])
        self.assertTrue(out["queue_ready"])
        self.assertFalse(any(m != "GET" for m,_,_ in api.calls))


if __name__ == "__main__":
    unittest.main()
