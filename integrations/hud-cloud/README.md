# Persistent private HUD reporting

Status: implemented and locally tested, **not deployed, not installed on Mac,
not connected as a ChatGPT tool**. No cloud account credentials were available
in this session. The current temporary tunnel is not converted merely by
merging this code.

The existing HUD is served unchanged behind a fixed HTTPS origin and private
device sign-in. A separately running outbound reporter uses the existing
OmniRoute model collector and employee SQLite reader, sending the 1h/24h/7d
aggregates to this cloud receiver. Closing the HUD does not stop reporting.
No tunnel URL, one-use pairing link, inbound Mac port, inference call or worker
dispatch is involved. The root response adds the existing live-adapter start
hook and removes the temporary-link button; existing source HTML is untouched.

The receiver stores the latest report for each period in D1. It also retains
one 24h-aggregate snapshot per minute for the preceding day, up to 32 KiB each.
This is sampled history, not a complete per-request event log. History reads
return at most 120 recent snapshots. Unknown quotas and upstream-model
attribution remain unknown. No prompts, draft outputs, private paths, provider
credentials or raw payloads are copied. Titles come from the existing public
queue-based employee reader, and only explicit telemetry fields are retained.

Every report retains its source observation time. Duplicate/older uploads
cannot overwrite new data or refresh the original receipt time. Browser meters
keep the existing 15-second freshness threshold; `/api/hud/status` returns
`fresh`, `stale`, or `never_received`. Reports do not prove human approval or
that each employee is online. Worker heartbeat and employee evidence stay
separate. When the Mac is asleep/offline, the cloud reader remains available
with old reports marked stale. Running OmniRoute while the Mac is off is a
separate hosting migration, not something this transport provides.

## Deployment boundary

Use an authenticated Cloudflare account and verify its $0 plan/allowance before
deployment. No paid plan or inference provider is selected by this source.
The supplied configuration deliberately has a placeholder database ID.

From this directory, using the account's approved installed Wrangler:

1. Provision D1 `rovor-hud-telemetry`, replace only `database_id` in
   `wrangler.jsonc`, and apply `schema.sql` to that database.
2. Configure two **different**, independently generated random secrets of at
   least 32 characters as `HUD_WRITER_TOKEN` and `HUD_READER_TOKEN` through the
   provider's secret mechanism. Never put them in source or GitHub logs.
3. Deploy this Worker with its D1 and ASSETS bindings. ASSETS points to the
   existing native-v8-9 HUD, so no HUD redesign or source-copy fork is needed.
   `run_worker_first` ensures all assets pass through private authentication.
4. Verify anonymous root redirects to `/login`, anonymous API access returns
   401, writer credentials cannot read, and reader credentials cannot upload.
   The sign-in form exchanges the reader key for a Secure/HttpOnly/SameSite
   cookie lasting seven days. It works independently on each device; there
   are no keys in URLs, browser storage, or embedded HUD JavaScript. Rotate
   the reader secret to revoke existing device cookies.

## Permanent Mac reporting

Use a persistent reviewed repository checkout, not a temporary download.
The reporter imports the existing bridge and its Python employee reader, so
the checkout must contain `tools/hud_omniroute_bridge.mjs`,
`tools/hud_employee_snapshot.py`, `tools/omniroute_ops_snapshot.py`, and the
public `coordination/tasks.json`. Existing worker services remain untouched.

Store the writer key in macOS Keychain under service `rovordigital.hud.writer`
using the account's secure credential-entry flow. The reporter reads that key
and the existing OmniRoute endpoint key locally; it never uploads either
OmniRoute key. `ROVOR_HUD_WRITER_TOKEN` is supported for controlled test/service
environments but should not be pasted into shell history or a tracked plist.
The origin is configured separately as `ROVOR_HUD_ORIGIN`.

First run `node tools/hud_telemetry_publisher.mjs --once` with that origin.
Only after all three periods are received, populate the three placeholder
paths/origin in `launchagent.plist.example`, install it as the dedicated
`com.rovor.hud-reporting` LaunchAgent, and verify a second report after closing
Terminal. This reports telemetry only; it is not a second workforce scheduler.
Stop/remove only that label to roll back reporting. The reporter repeats with
a 10-second pause, backs off on failures up to five minutes, prevents overlapping
cycles, and does not replay jobs. Slow/unavailable collection can make reports
stale, and unavailable cloud delivery does not produce fake progress. It does
not buffer a complete offline request ledger or prevent Mac sleep.

## ChatGPT without pasted links

`POST /mcp` provides one read-only tool: `rovor_workforce_status`. The reader
credential authenticates it; the writer credential does not. It returns the
latest stored report and explicit freshness. It cannot run jobs or mark work
approved. A connector must be registered against the deployed fixed `/mcp`
endpoint and authenticated **once** before new chats can call it by name.
Source code alone does not install that connector or give every chat access.
Browser device cookies do not grant access to MCP POST requests.

## Verification

`node --test tests/test_hud_cloud.mjs` (from repository root) runs 18 focused
tests on Node 24, using real in-memory SQLite behind a D1-shaped adapter.
Tests cover role separation, device sign-in, original-HUD injection, all periods,
source clocks, duplicate/out-of-order uploads, retained stale reports, retention,
allowlisted fields, malformed payloads, bounded bodies, read-only MCP and the
outbound publisher. These tests do not prove a deployed D1 binding, browser
layout, live gateway delivery, launchd startup, or a completed 24h soak.

Live read-only host evidence collected during implementation: heartbeat was
recent but dispatch reported `failure_circuit_requires_review`; no employee's
`online_verified` was true. That observation is time-specific and is not a
cloud telemetry verification.
