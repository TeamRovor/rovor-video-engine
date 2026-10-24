#!/usr/bin/env python3
"""Opt-in, resumable PRIVATE ROVOR Mac command-repo bootstrap.

One-time operator action, not a daemon or Mac remote-command executor.
Requires a locally authenticated GitHub CLI account. Never prints tokens.
"""
import argparse
import base64
import json
import subprocess
import sys
import urllib.error
import urllib.request

OWNER = "TeamRovor"
REPO = "TeamRovor/rovor-mac-control"
PUBLIC = "TeamRovor/rovor-video-engine"
ISSUE_TITLE = "ROVOR private Mac control receipts"
JOB_ID = "mac-link-private-001"
JOB_PATH = "control/jobs/" + JOB_ID + ".json"
QUEUE_PATH = "control/queue.json"
PING = {"schema": 1, "id": JOB_ID, "kind": "system.ping", "payload": {}}
QUEUE = {"schema": 1, "jobs": [JOB_ID]}
MAX_RESPONSE = 1_000_000


class Refused(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_local_gh_token(run=subprocess.run):
    """Read local gh authentication in process memory only, never stdout."""
    try:
        result = run(["gh", "auth", "token"], capture_output=True,
                     text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise Refused("github_cli_auth_unavailable") from None
    token = result.stdout.strip() if result.returncode == 0 else ""
    if not token or len(token) > 512 or any(x in token for x in ("\r", "\n", " ", "\x00")):
        raise Refused("github_cli_auth_unavailable")
    return token


def github_api(token):
    if not isinstance(token, str) or not token:
        raise Refused("github_cli_auth_unavailable")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    def request(method, path, body=None):
        if not path.startswith("/repos/") and path not in ("/user", "/user/repos") and not path.startswith("/orgs/"):
            raise Refused("unsupported_github_endpoint")
        if any(c in path for c in ("\r", "\n", "\x00")):
            raise Refused("unsupported_github_endpoint")
        if method not in ("GET", "POST", "PUT"):
            raise Refused("unsupported_github_method")
        data = None
        if body is not None:
            if method == "GET":
                raise Refused("invalid_github_request")
            data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        req = urllib.request.Request("https://api.github.com" + path,
                                     data=data, method=method,
                                     headers={"Authorization": "Bearer " + token,
                                              "Accept": "application/vnd.github+json",
                                              "X-GitHub-Api-Version": "2022-11-28",
                                              "Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=20) as response:
                raw = response.read(MAX_RESPONSE + 1)
                status = response.status
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return 404, None
            raise Refused("github_http_" + str(err.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Refused("github_request_unavailable") from None
        if len(raw) > MAX_RESPONSE:
            raise Refused("github_response_too_large")
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            raise Refused("github_invalid_json") from None
        return status, value
    return request


def require_repo_metadata(metadata):
    if (not isinstance(metadata, dict)
            or metadata.get("full_name") != REPO
            or metadata.get("private") is not True
            or metadata.get("archived") is True
            or metadata.get("disabled") is True
            or metadata.get("default_branch") != "main"
            or metadata.get("has_issues") is not True):
        raise Refused("private_repository_not_ready")


def prepare_repo(api, apply):
    code, info = api("GET", "/repos/" + REPO)
    if code == 404:
        if not apply:
            return False
        c, source = api("GET", "/repos/" + PUBLIC)
        if c != 200 or not isinstance(source, dict) or not isinstance(source.get("owner"), dict):
            raise Refused("owner_identity_unavailable")
        kind = source["owner"].get("type")
        if kind == "User":
            ucode, user = api("GET", "/user")
            if ucode != 200 or not isinstance(user, dict) or user.get("login", "").casefold() != OWNER.casefold():
                raise Refused("authenticate_as_teamrovor_first")
            endpoint = "/user/repos"
        elif kind == "Organization":
            endpoint = "/orgs/" + OWNER + "/repos"
        else:
            raise Refused("owner_type_unrecognized")
        code, info = api("POST", endpoint,
                         {"name": "rovor-mac-control", "private": True,
                          "has_issues": True, "auto_init": True,
                          "description": "Private, allowlisted Mac control and receipts for ROVOR"})
        if code != 201:
            raise Refused("private_repo_create_not_confirmed")
    elif code != 200:
        raise Refused("private_repo_metadata_not_confirmed")
    require_repo_metadata(info)
    return True


def issue_number(api, apply):
    code, issues = api("GET", "/repos/" + REPO + "/issues?state=all&per_page=100")
    if code != 200 or not isinstance(issues, list) or len(issues) >= 100:
        raise Refused("private_issue_list_incomplete")
    matches = [x for x in issues if isinstance(x, dict)
               and x.get("title") == ISSUE_TITLE and "pull_request" not in x]
    if len(matches) > 1:
        raise Refused("duplicate_receipt_issues")
    if matches:
        item = matches[0]
        if item.get("state") != "open" or type(item.get("number")) is not int:
            raise Refused("receipt_issue_closed_or_invalid")
        return item["number"], False
    if not apply:
        return None, False
    c, created = api("POST", "/repos/" + REPO + "/issues",
                     {"title": ISSUE_TITLE,
                      "body": "Private, sanitized execution receipts from the allowlisted ROVOR Mac worker. Never post secrets or raw local paths."})
    if c != 201 or not isinstance(created, dict) or type(created.get("number")) is not int:
        raise Refused("private_issue_not_confirmed")
    return created["number"], True


def ensure_file(api, path, expected, apply):
    endpoint = "/repos/" + REPO + "/contents/" + path
    code, meta = api("GET", endpoint + "?ref=main")
    if code == 200:
        if (not isinstance(meta, dict) or meta.get("type") != "file"
                or meta.get("encoding") != "base64" or not isinstance(meta.get("content"), str)):
            raise Refused("existing_control_file_unreadable")
        try:
            data = base64.b64decode(meta["content"].replace("\n", ""), validate=True)
            got = json.loads(data)
        except (ValueError, UnicodeError, TypeError, base64.binascii.Error):
            raise Refused("existing_control_file_unreadable") from None
        if got != expected:
            raise Refused("existing_control_file_conflict")
        return False
    if code != 404:
        raise Refused("control_file_check_unavailable")
    if not apply:
        return None
    raw = (json.dumps(expected, sort_keys=True, indent=2) + "\n").encode("utf-8")
    c, obj = api("PUT", endpoint,
                 {"message": "Initialize private ROVOR allowlisted ping channel",
                  "branch": "main", "content": base64.b64encode(raw).decode("ascii")})
    if c != 201 or not isinstance(obj, dict) or not isinstance(obj.get("content"), dict):
        raise Refused("control_file_create_not_confirmed")
    # Independently read back; never declare a successful write from HTTP alone.
    code, _info = api("GET", endpoint + "?ref=main")
    if code != 200:
        raise Refused("control_file_readback_missing")
    return True


def bootstrap(api, apply=False):
    """No destructive updates. An incomplete run is resumable with --apply."""
    if type(apply) is not bool:
        raise Refused("invalid_operator_approval")
    exists = prepare_repo(api, apply)
    report = {"status": "private_control_prepared" if apply else "read_only_preflight",
              "private_repo_verified": exists,
              "receipt_issue_ready": False,
              "queue_ready": False,
              "ping_packet_ready": False,
              "private_receipt_issue_number": None,
              "supervisor_activated": False,
              "mac_command_executed": False,
              "remote_terminal_control_verified": False}
    if not exists:
        return report
    issue, _created = issue_number(api, apply)
    report["private_receipt_issue_number"] = issue
    report["receipt_issue_ready"] = issue is not None
    # Publish job first, queue last: never make a queue point at an absent job.
    job_done = ensure_file(api, JOB_PATH, PING, apply)
    queue_done = ensure_file(api, QUEUE_PATH, QUEUE, apply)
    report["ping_packet_ready"] = job_done is not None
    report["queue_ready"] = queue_done is not None
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly create the private GitHub repo/receipt issue/fixed ping files")
    args = parser.parse_args(argv)
    try:
        token = load_local_gh_token()
        result = bootstrap(github_api(token), apply=args.apply)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["private_repo_verified"] else 1
    except Refused as err:
        # All error classes are fixed strings; never emit auth details or API response bodies.
        print(json.dumps({"status": "blocked", "reason": str(err),
                          "mac_command_executed": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
