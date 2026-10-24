# ROVOR private command-channel bootstrap

**Why this exists:** the Mac's already-tested five-minute ghost worker is not the same as remote ChatGPT-to-Mac execution. The private bridge source in PR #41 needs a *separate, private* TeamRovor control repo, a fixed receipt issue and a verified Mac-local scoped credential. As of the 2026-10-23 GitHub connection check, only the public TeamRovor/rovor-video-engine repository was accessible.

This is one small, **optional one-time operator program** to prepare the missing PRIVATE repository without duplicating the Mac worker/scheduler. It is read-only by default, creates resources only with `--apply`, and can be rerun safely after a partial failure. It uses the already locally authenticated GitHub CLI (`gh auth token` internally); no token is printed or saved. GitHub API requests go exclusively to api.github.com with redirect and proxy disabled. It **never** installs software, stores a credential in Keychain, launches a Mac command or turns on a LaunchAgent.

## Operator prerequisites

- A locally authenticated GitHub CLI account authorized to create repositories for TeamRovor (if TeamRovor is a personal account, the current `gh auth` login must be TeamRovor).
- Run from a reviewed clean checkout, in the user's interactive Mac session; no public-repository self-hosted runner.
- An existing public `TeamRovor/rovor-video-engine` readable only for owner-type detection.
- The new private repo must default to branch `main` and have Issues enabled. An existing public or conflicting repo is **always refused**, never converted or overwritten.

## Default no-write check

```sh
python3 tools/private_control_repo_bootstrap.py
```

This checks for the exact private repository `TeamRovor/rovor-mac-control`; returns `private_repo_verified=false` if absent, without creating anything. If it is present, checks the exact receipt issue and fixed ping/queue files without modifying them.

## Explicit initial creation (one time; GH authentication required)

```sh
python3 tools/private_control_repo_bootstrap.py --apply
```

Creates the private repository if absent, a private issue titled `ROVOR private Mac control receipts`, an allowlisted `system.ping` packet with ID `mac-link-private-001`, and `control/queue.json` containing that ID. It creates the job **before** exposing the queue, verifies privacy and readback, and refuses conflicting files or closed/duplicate issues. It does not issue commands or create an executor. The output only contains confirmation booleans and the private receipt issue number.

## Finish the actual remote execution connection

1. Grant the GitHub connection used by ChatGPT access **only** to the new private control repo, and confirm it is visible.
2. Separately create a **fine-grained, repository-scoped** token for the Mac runtime: Metadata read, Contents read, Issues write. Store through the Mac owner's Keychain UI as service `rovordigital.private-control.github-token`. Never paste tokens in chat or a public issue. Do not use the broader owner-bootstrap credential for unattended runtime.
3. Use the **already authored**, opt-in `tools/rovor_private_supervisor.py` from a verified PR #41 checkout: inspect `--status`; stage with `--stage --approve-stage --repo TeamRovor/rovor-mac-control --receipt-issue N` using the actual returned private issue N; run `--preflight`; then explicitly `--activate --approve-activate` only if preflight succeeds. Do not create a second worker/scheduler.
4. Verify private issue receives a sanitized receipt from **the actual Mac**, from an independently picked up `system.ping`; record actual timestamp, attempt count and STOP behavior. Until then, **no direct terminal control is established**. This v1 bridge does not accept arbitrary commands; terminal capabilities must be separately allowlisted, risk-scoped and verified before use by research roles.

## Tests and limits

The hosted Python 3.9/3.11 tests mock all GitHub requests and never create a repository or run on Mac. The tool cannot create an OAuth app installation, provision a least-privilege Keychain token, bypass account/org approval, or guarantee an always-awake Mac. The existing five-claims-per-24h OmniRoute quota and failed scheduled AI inference remain independent blockers. Avoid treating a private repo or passing preflight as a successful unattended AI employee.
